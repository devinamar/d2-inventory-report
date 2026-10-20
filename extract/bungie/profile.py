# Reads the Bungie profile response: every weapon and armor copy, with the
# instance components the item tables store as they come (300 instances, 304
# stats, 305 sockets, 309 plug objectives, 310 reusable plugs). Every weapon
# and armor copy is kept, whatever its tier; the analysis decides which ones
# to compare.
import dataclasses


def collect_profile_items(profile: dict) -> tuple:
    # (all_items, components): every item in the vault, the character
    # inventories and equipped gear, and the per-instance data under 'sockets',
    # 'reusable_plugs', 'plug_objectives', 'instances' and 'stats'.
    all_items = []
    all_items.extend(profile.get('profileInventory', {}).get('data', {}).get('items', []))
    for inv in profile.get('characterInventories', {}).get('data', {}).values():
        all_items.extend(inv.get('items', []))
    for equip in profile.get('characterEquipment', {}).get('data', {}).values():
        all_items.extend(equip.get('items', []))

    item_components = profile.get('itemComponents', {})
    components = {
        'sockets': item_components.get('sockets', {}).get('data', {}),
        'reusable_plugs': item_components.get('reusablePlugs', {}).get('data', {}),
        'plug_objectives': item_components.get('plugObjectives', {}).get('data', {}),
        'instances': item_components.get('instances', {}).get('data', {}),
        'stats': item_components.get('stats', {}).get('data', {}),
    }
    return all_items, components


@dataclasses.dataclass
class ProfileRows:
    # Rows for the component tables, in their column order.
    items: list  # DestinyItemComponent
    instances: list  # DestinyItemInstanceComponent
    stats: list  # DestinyItemStatsComponent
    sockets: list  # DestinyItemSocketsComponent
    reusable_plugs: list  # DestinyItemReusablePlugsComponent
    plug_objectives: list  # DestinyItemPlugObjectivesComponent
    unknown_plugs: int = 0  # socket plugs that aren't stored plugs, stored as NULL


def flag(value):
    # A true/false field as 1 or 0, or None when the profile leaves it out.
    if value is None:
        return None
    return int(value)


def profile_rows(conn, profile: dict) -> ProfileRows:
    # The rows of every weapon and armor copy. Plugs, stats and objectives the
    # definition tables don't have are left out: a plugged plug is stored as
    # NULL, the rest are skipped.
    all_items, components = collect_profile_items(profile)
    gear_hashes = {
        r[0]
        for r in conn.execute(
            "SELECT hash FROM DestinyInventoryItemDefinition WHERE itemType IN (2, 3)"
        )
    }
    plug_hashes = {
        r[0]
        for r in conn.execute(
            "SELECT hash FROM DestinyInventoryItemDefinition "
            "WHERE plugCategoryIdentifier IS NOT NULL"
        )
    }
    stat_hashes = {r[0] for r in conn.execute("SELECT hash FROM DestinyStatDefinition")}
    damage_hashes = {r[0] for r in conn.execute("SELECT hash FROM DestinyDamageTypeDefinition")}
    objective_hashes = {r[0] for r in conn.execute("SELECT hash FROM DestinyObjectiveDefinition")}

    rows = ProfileRows([], [], [], [], [], [])
    for item in all_items:
        instance_id = item.get('itemInstanceId')
        if not instance_id or item.get('itemHash') not in gear_hashes:
            continue
        rows.items.append((instance_id, item['itemHash'], item.get('state', 0)))

        instance = components['instances'].get(instance_id)
        if instance is not None:
            damage_hash = instance.get('damageTypeHash')
            if damage_hash not in damage_hashes:
                damage_hash = None
            rows.instances.append(
                (
                    instance_id,
                    flag(instance.get('isEquipped')),
                    (instance.get('primaryStat') or {}).get('value'),
                    instance.get('gearTier'),
                    damage_hash,
                )
            )

        stats = components['stats'].get(instance_id, {}).get('stats', {})
        for stat in stats.values():
            if stat['statHash'] in stat_hashes:
                rows.stats.append((instance_id, stat['statHash'], stat.get('value')))

        sockets = components['sockets'].get(instance_id, {}).get('sockets', [])
        for idx, socket in enumerate(sockets):
            plug_hash = socket.get('plugHash')
            if plug_hash and plug_hash not in plug_hashes:
                rows.unknown_plugs += 1
                plug_hash = None
            rows.sockets.append(
                (
                    instance_id,
                    idx,
                    plug_hash or None,
                    flag(socket.get('isEnabled')),
                    flag(socket.get('isVisible')),
                )
            )

        reusable = components['reusable_plugs'].get(instance_id, {}).get('plugs', {})
        for idx, plugs in reusable.items():
            if int(idx) >= len(sockets):
                continue
            for position, plug in enumerate(plugs):
                if plug['plugItemHash'] in plug_hashes:
                    rows.reusable_plugs.append(
                        (
                            instance_id,
                            int(idx),
                            position,
                            plug['plugItemHash'],
                            flag(plug.get('canInsert')),
                            flag(plug.get('enabled')),
                        )
                    )

        per_plug = components['plug_objectives'].get(instance_id, {}).get('objectivesPerPlug', {})
        for plug_hash, objectives in per_plug.items():
            if int(plug_hash) not in plug_hashes:
                continue
            for o in objectives:
                if o['objectiveHash'] in objective_hashes:
                    rows.plug_objectives.append(
                        (
                            instance_id,
                            int(plug_hash),
                            o['objectiveHash'],
                            o.get('progress'),
                            o.get('completionValue'),
                            flag(o.get('complete')),
                            flag(o.get('visible')),
                        )
                    )
    return rows
