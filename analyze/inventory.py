# Reads the stored inventory back as WeaponInstance and ArmorInstance objects
# for analyze, from the views over the item tables (v_weapon, v_weapon_roll,
# v_armor, v_armor_tuning) that extract/bungie/inventory.py fills.
import models

# The lowest weapon tier the analysis compares (tierType 5, Legendary); every
# copy below it is flagged.
TIER_FLOOR = 5


def load_rolls(conn) -> dict:
    # {instance_id: [PerkSocket]}: each weapon copy's perk sockets in socket
    # order, each socket's perks in the game's order.
    sockets_by_instance = {}
    for r in conn.execute(
        "SELECT instance_id, socket_idx, kind, perk FROM v_weapon_roll "
        "ORDER BY instance_id, socket_idx, position"
    ):
        sockets = sockets_by_instance.setdefault(r['instance_id'], {})
        socket = sockets.get(r['socket_idx'])
        if socket is None:
            socket = sockets[r['socket_idx']] = models.PerkSocket(r['kind'], [])
        socket.perks.append(r['perk'])
    return {
        instance_id: list(sockets.values()) for instance_id, sockets in sockets_by_instance.items()
    }


def load_weapons(conn) -> list:
    # The weapon copies the analysis compares, lowest itemInstanceId first:
    # Legendary and Exotic copies with at least one trait socket, each with
    # its roll. Lower tiers and copies without traits stay stored but aren't
    # compared.
    rolls = load_rolls(conn)
    return [
        models.WeaponInstance(r['instance_id'], r['item_hash'], rolls.get(r['instance_id'], []))
        for r in conn.execute(
            "SELECT v.instance_id, v.item_hash FROM v_weapon v "
            "WHERE v.tier >= ? AND EXISTS ("
            "  SELECT 1 FROM v_weapon_roll r "
            "  WHERE r.instance_id = v.instance_id AND r.kind = 'trait') "
            "ORDER BY v.instance_id",
            (TIER_FLOOR,),
        )
    ]


def load_below_legendary(conn) -> list:
    # The instance ids of the weapon copies below Legendary, lowest first.
    return [
        r['instance_id']
        for r in conn.execute(
            "SELECT instance_id FROM v_weapon WHERE tier < ? ORDER BY instance_id", (TIER_FLOOR,)
        )
    ]


def load_armor(conn) -> list:
    # Current armor copies, lowest itemInstanceId first. Each row is one
    # copy, built with its definition (an Armor).
    tuning_by_instance = {}
    for r in conn.execute("SELECT instance_id, stat FROM v_armor_tuning"):
        tuning_by_instance.setdefault(r['instance_id'], set()).add(r['stat'])

    pieces = []
    for r in conn.execute("SELECT * FROM v_armor ORDER BY instance_id"):
        if r['set_hash'] is not None:
            set_bonus = models.ArmorSetBonus(r['two_pc'], r['four_pc'])
        else:
            set_bonus = None
        if r['is_exotic']:
            exotic_effect = models.ExoticEffect(r['exotic_perk_name'], r['exotic_perk_desc'])
        else:
            exotic_effect = None
        pieces.append(
            models.ArmorInstance(
                instance_id=r['instance_id'],
                armor=models.Armor(
                    name=r['name'],
                    set_name=r['set_name'],
                    set_bonus=set_bonus,
                    is_exotic=bool(r['is_exotic']),
                    exotic_effect=exotic_effect,
                ),
                stats=models.ArmorStats(*(r[c] for c in models.ARMOR_STAT_NAMES)),
                gear_tier=r['gear_tier'],
                tuning_stats=tuple(
                    s
                    for s in models.ARMOR_STAT_NAMES
                    if s in tuning_by_instance.get(r['instance_id'], ())
                ),
            )
        )
    return pieces
