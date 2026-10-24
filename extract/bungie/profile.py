# Reads the Bungie profile response: every weapon and armor copy, with the
# instance components the item tables store (300 instances, 304 stats, 305
# sockets, 309 plug objectives, 310 reusable plugs). Every weapon and armor
# copy is kept, whatever its tier; the analysis decides which ones to compare.
# A component is stored one row per copy, nested as the profile sends it and
# trimmed to the fields the app reads.
import dataclasses
import json


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
    # Rows for the component tables, in their column order: a copy's instance
    # values, and each other component as (copy, its JSON).
    items: list  # DestinyItemComponent
    instances: list  # DestinyItemInstanceComponent
    stats: list  # DestinyItemStatsComponent
    sockets: list  # DestinyItemSocketsComponent
    reusable_plugs: list  # DestinyItemReusablePlugsComponent
    plug_objectives: list  # DestinyItemPlugObjectivesComponent


# The fields of each component entry the app reads, kept in the JSON.
SOCKET_FIELDS = ('plugHash',)
PLUG_FIELDS = ('plugItemHash',)
OBJECTIVE_FIELDS = ('objectiveHash', 'progress')


def flag(value):
    # A true/false field as 1 or 0, or None when the profile leaves it out.
    if value is None:
        return None
    return int(value)


def keep(entry, fields) -> dict:
    # entry with only fields, the ones it has.
    return {k: entry[k] for k in fields if k in entry}


def profile_rows(conn, profile: dict) -> ProfileRows:
    # The rows of every weapon and armor copy. A component's hashes are kept
    # as sent, whether or not the definition tables have them; a copy the
    # profile sends a component for gets its row, the others none. An
    # instance's damage type the definitions don't have is NULL.
    all_items, components = collect_profile_items(profile)
    gear_hashes = {
        r[0]
        for r in conn.execute(
            "SELECT hash FROM DestinyInventoryItemDefinition WHERE itemType IN (2, 3)"
        )
    }
    damage_hashes = {r[0] for r in conn.execute("SELECT hash FROM DestinyDamageTypeDefinition")}

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

        stats = components['stats'].get(instance_id)
        if stats is not None:
            values = {h: s['value'] for h, s in (stats.get('stats') or {}).items() if 'value' in s}
            rows.stats.append((instance_id, json.dumps(values)))

        sockets = components['sockets'].get(instance_id)
        if sockets is not None:
            entries = [keep(s, SOCKET_FIELDS) for s in sockets.get('sockets') or []]
            rows.sockets.append((instance_id, json.dumps(entries)))

        reusable = components['reusable_plugs'].get(instance_id)
        if reusable is not None:
            plugs = {
                idx: [keep(p, PLUG_FIELDS) for p in entries]
                for idx, entries in (reusable.get('plugs') or {}).items()
            }
            rows.reusable_plugs.append((instance_id, json.dumps(plugs)))

        per_plug = components['plug_objectives'].get(instance_id)
        if per_plug is not None:
            objectives = {
                plug: [keep(o, OBJECTIVE_FIELDS) for o in entries]
                for plug, entries in (per_plug.get('objectivesPerPlug') or {}).items()
            }
            rows.plug_objectives.append((instance_id, json.dumps(objectives)))
    return rows
