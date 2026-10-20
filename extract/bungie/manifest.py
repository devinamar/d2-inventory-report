# Manifest ingest: copies what the app uses from the downloaded manifest into
# the tables named after its definitions (db/schema/bungie/manifest/): every
# weapon, armor piece and plug (and the Gunsmith Orders, Banshee's bounties
# whose icons picture the weapon types), their sockets and plug sets, and the
# stats, damage types, champion types, classes, buckets, objectives, armor sets
# and collectibles they name. Runs first in extract, and only for a new version.
import contextlib
import json
import sqlite3

WEAPON_ITEM_TYPE = 3  # DestinyItemType.Weapon
ARMOR_ITEM_TYPE = 2  # DestinyItemType.Armor
# Banshee's bounties, one per weapon type and named after it ("Hand Cannons"):
# their icons are the only weapon type pictures in the manifest.
GUNSMITH_ORDER = 'Gunsmith Order'


def definitions(mconn, table: str):
    # Every definition in a manifest table, parsed from its JSON, one at a
    # time so the whole table is never in memory.
    for (raw,) in mconn.execute(f'SELECT json FROM {table}'):
        yield json.loads(raw)


# DestinyInventoryItemDefinition's columns, in the order item_row gives them.
ITEM_COLUMNS = (
    'hash',
    'name',
    'description',
    'icon',
    'itemType',
    'itemTypeDisplayName',
    'classType',
    'tierType',
    'bucketTypeHash',
    'equipableItemSetHash',
    'ammoType',
    'defaultDamageTypeHash',
    'iconWatermark',
    'collectibleHash',
    'traitIds',
    'plugCategoryIdentifier',
)


def item_row(obj) -> tuple:
    # A DestinyInventoryItemDefinition row (ITEM_COLUMNS): the fields the app
    # reads, as the manifest has them. plugCategoryIdentifier is '' for a plug
    # without one and NULL for an item that isn't a plug.
    props = obj.get('displayProperties') or {}
    inventory = obj.get('inventory') or {}
    plug = obj.get('plug')
    if isinstance(plug, dict):
        category = plug.get('plugCategoryIdentifier') or ''
    else:
        category = None
    trait_ids = obj.get('traitIds')
    if trait_ids is not None:
        trait_ids = json.dumps(trait_ids)
    equipping = obj.get('equippingBlock') or {}
    return (
        obj['hash'],
        props.get('name'),
        props.get('description'),
        props.get('icon'),
        obj.get('itemType'),
        obj.get('itemTypeDisplayName'),
        obj.get('classType'),
        inventory.get('tierType'),
        inventory.get('bucketTypeHash'),
        equipping.get('equipableItemSetHash'),
        equipping.get('ammoType'),
        obj.get('defaultDamageTypeHash'),
        obj.get('iconWatermark'),
        obj.get('collectibleHash'),
        trait_ids,
        category,
    )


def upsert(conn, table: str, columns: tuple, rows: list) -> None:
    # Insert rows, updating those whose key (the first column) is already
    # there. Unlike INSERT OR REPLACE this keeps the row, so the rows that
    # reference it stay valid.
    sets = ', '.join(f'{c} = excluded.{c}' for c in columns[1:])
    if sets:
        conflict = f'ON CONFLICT({columns[0]}) DO UPDATE SET {sets}'
    else:
        conflict = 'ON CONFLICT DO NOTHING'
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join('?' * len(columns))}) {conflict}",
        rows,
    )


def replace_rows(conn, table: str, rows: list) -> None:
    # Replace every row of a table nothing else points at.
    conn.execute(f"DELETE FROM {table}")
    if rows:
        conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(rows[0]))})", rows)


def ingest_manifest(conn, manifest_path, version: str) -> bool:
    # Copy what the app uses from the manifest at manifest_path, unless this
    # version was already ingested. Reads the manifest read-only, one
    # definition at a time. Returns True when the tables were rewritten.
    if conn.execute(
        "SELECT 1 FROM manifest_version WHERE version = ?",
        (version,),
    ).fetchone():
        return False

    uri = f"file:{manifest_path}?mode=ro"
    with contextlib.closing(sqlite3.connect(uri, uri=True)) as mconn:
        # The whole small tables.
        damage_rows = []
        for o in definitions(mconn, 'DestinyDamageTypeDefinition'):
            props = o.get('displayProperties') or {}
            damage_rows.append(
                (o['hash'], o.get('enumValue'), props.get('name'), props.get('icon'))
            )
        breaker_rows = []
        for o in definitions(mconn, 'DestinyBreakerTypeDefinition'):
            props = o.get('displayProperties') or {}
            breaker_rows.append((o['hash'], props.get('name'), props.get('icon')))
        stat_rows = []
        for o in definitions(mconn, 'DestinyStatDefinition'):
            props = o.get('displayProperties') or {}
            stat_rows.append((o['hash'], props.get('name'), props.get('icon')))
        class_rows = [
            (o['hash'], o.get('classType'), (o.get('displayProperties') or {}).get('name'))
            for o in definitions(mconn, 'DestinyClassDefinition')
        ]
        set_rows, set_perk_rows = [], []
        for o in definitions(mconn, 'DestinyEquipableItemSetDefinition'):
            set_rows.append((o['hash'], (o.get('displayProperties') or {}).get('name')))
            for position, perk in enumerate(o.get('setPerks') or []):
                set_perk_rows.append(
                    (o['hash'], position, perk.get('requiredSetCount'), perk.get('sandboxPerkHash'))
                )

        # Weapons, armor and plugs: one row each, a weapon's or armor piece's
        # sockets, a plug's investment stats, and the hashes they name.
        item_rows, socket_rows, stat_value_rows = [], [], []
        plug_hashes, objective_hashes, collectible_hashes, bucket_hashes = (
            set(),
            set(),
            set(),
            set(),
        )
        weapons = armor = 0
        for obj in definitions(mconn, 'DestinyInventoryItemDefinition'):
            is_weapon = obj.get('itemType') == WEAPON_ITEM_TYPE
            is_plug = isinstance(obj.get('plug'), dict)
            gear = is_weapon or obj.get('itemType') == ARMOR_ITEM_TYPE
            is_order = obj.get('itemTypeDisplayName') == GUNSMITH_ORDER
            if not (gear or is_plug or is_order):
                continue
            item_rows.append(item_row(obj))
            if gear:
                if is_weapon:
                    weapons += 1
                    if obj.get('collectibleHash'):
                        collectible_hashes.add(obj['collectibleHash'])
                else:
                    armor += 1
                bucket_hashes.add((obj.get('inventory') or {}).get('bucketTypeHash'))
                for idx, se in enumerate((obj.get('sockets') or {}).get('socketEntries') or []):
                    socket_rows.append(
                        (
                            obj['hash'],
                            idx,
                            se.get('singleInitialItemHash') or None,
                            se.get('randomizedPlugSetHash') or None,
                            se.get('reusablePlugSetHash') or None,
                        )
                    )
            if is_plug:
                plug_hashes.add(obj['hash'])
                objective_hashes.update((obj.get('objectives') or {}).get('objectiveHashes') or [])
                for position, stat in enumerate(obj.get('investmentStats') or []):
                    stat_value_rows.append(
                        (obj['hash'], position, stat.get('statTypeHash'), stat.get('value'))
                    )

        # What the items name: their buckets, the weapons' collectibles, the
        # plugs' objectives and the set bonuses' perks.
        bucket_rows = [
            (o['hash'], (o.get('displayProperties') or {}).get('name'), o.get('bucketOrder'))
            for o in definitions(mconn, 'DestinyInventoryBucketDefinition')
            if o['hash'] in bucket_hashes
        ]
        collectible_rows = [
            (o['hash'], o.get('sourceString'))
            for o in definitions(mconn, 'DestinyCollectibleDefinition')
            if o['hash'] in collectible_hashes
        ]
        objective_rows = [
            (
                o['hash'],
                o.get('progressDescription'),
                o.get('inProgressValueStyle'),
                o.get('completedValueStyle'),
                (o.get('displayProperties') or {}).get('icon'),
            )
            for o in definitions(mconn, 'DestinyObjectiveDefinition')
            if o['hash'] in objective_hashes
        ]
        perk_hashes = {r[3] for r in set_perk_rows}
        sandbox_perk_rows = [
            (
                o['hash'],
                (o.get('displayProperties') or {}).get('name'),
                (o.get('displayProperties') or {}).get('description'),
                (o.get('displayProperties') or {}).get('icon'),
            )
            for o in definitions(mconn, 'DestinySandboxPerkDefinition')
            if o['hash'] in perk_hashes
        ]

        # The plug sets the sockets name, and their plugs. An entry whose plug
        # isn't a stored plug is skipped.
        named_sets = {h for r in socket_rows for h in r[3:5] if h}
        plug_set_rows, plug_set_item_rows, skipped = [], [], 0
        for o in definitions(mconn, 'DestinyPlugSetDefinition'):
            if o['hash'] not in named_sets:
                continue
            plug_set_rows.append((o['hash'],))
            for position, p in enumerate(o.get('reusablePlugItems') or []):
                if p.get('plugItemHash') not in plug_hashes:
                    skipped += 1
                    continue
                can_roll = p.get('currentlyCanRoll')
                if can_roll is not None:
                    can_roll = int(can_roll)
                plug_set_item_rows.append((o['hash'], position, p['plugItemHash'], can_roll))

        # Gear tier pip images and masterwork borders.
        constants_rows = [
            (
                o['hash'],
                json.dumps(o.get('gearTierOverlayImagePaths') or []),
                o.get('masterworkBorderedOverlayPath'),
                o.get('masterworkExoticBorderedOverlayPath'),
            )
            for o in definitions(mconn, 'DestinyInventoryItemConstantsDefinition')
        ]

    # Parents before children, so every foreign key holds as rows go in.
    # Tables other rows point at are upserted, never emptied: stored copies
    # and wishlist rolls point at items, and copies at stats, damage types and
    # objectives, so a row missing from a newer manifest must not orphan them.
    # The rows hanging off an item, a plug set or an armor set are replaced.
    with conn:
        upsert(
            conn, 'DestinyDamageTypeDefinition', ('hash', 'enumValue', 'name', 'icon'), damage_rows
        )
        upsert(conn, 'DestinyBreakerTypeDefinition', ('hash', 'name', 'icon'), breaker_rows)
        upsert(conn, 'DestinyStatDefinition', ('hash', 'name', 'icon'), stat_rows)
        upsert(conn, 'DestinyClassDefinition', ('hash', 'classType', 'name'), class_rows)
        upsert(conn, 'DestinyEquipableItemSetDefinition', ('hash', 'name'), set_rows)
        upsert(
            conn,
            'DestinySandboxPerkDefinition',
            ('hash', 'name', 'description', 'icon'),
            sandbox_perk_rows,
        )
        replace_rows(conn, 'DestinyItemSetPerkDefinition', set_perk_rows)
        upsert(
            conn, 'DestinyInventoryBucketDefinition', ('hash', 'name', 'bucketOrder'), bucket_rows
        )
        upsert(conn, 'DestinyCollectibleDefinition', ('hash', 'sourceString'), collectible_rows)
        upsert(
            conn,
            'DestinyObjectiveDefinition',
            ('hash', 'progressDescription', 'inProgressValueStyle', 'completedValueStyle', 'icon'),
            objective_rows,
        )
        upsert(conn, 'DestinyInventoryItemDefinition', ITEM_COLUMNS, item_rows)
        replace_rows(conn, 'DestinyItemSocketEntryDefinition', socket_rows)
        replace_rows(conn, 'DestinyItemInvestmentStatDefinition', stat_value_rows)
        upsert(conn, 'DestinyPlugSetDefinition', ('hash',), plug_set_rows)
        replace_rows(conn, 'DestinyItemSocketEntryPlugItemRandomizedDefinition', plug_set_item_rows)
        upsert(
            conn,
            'DestinyInventoryItemConstantsDefinition',
            (
                'hash',
                'gearTierOverlayImagePaths',
                'masterworkBorderedOverlayPath',
                'masterworkExoticBorderedOverlayPath',
            ),
            constants_rows,
        )
        conn.execute("INSERT INTO manifest_version VALUES (?)", (version,))
    print(
        f"  Database: ingested manifest {version} ({len(plug_hashes):,} plugs, "
        f"{weapons:,} weapons, {armor:,} armor, {len(plug_set_rows):,} plug sets)"
    )
    if skipped:
        print(f"  Database: skipped {skipped} plug-set entries naming an unknown plug")
    return True
