# Tests for copying the manifest into the definition tables
# (extract/bungie/manifest.py). The manifest is a small SQLite file laid out as
# Bungie ships it, holding real definitions from the live manifest trimmed to
# the fields the copy reads.
import json
import sqlite3

import pytest

from db import connection
from extract.bungie import manifest

VERSION = 'world_sql_content_a695ee698e87bcb0333c1026ba10cd63'

FATEBRINGER = {
    'hash': 4219826183,
    'displayProperties': {'name': 'Fatebringer (Timelost)'},
    'itemType': 3,
    'itemTypeDisplayName': 'Hand Cannon',
    'classType': 3,
    'defaultDamageTypeHash': 3373582085,
    'equippingBlock': {'ammoType': 1},
    'inventory': {'tierType': 5, 'bucketTypeHash': 1498876634},
    'sockets': {'socketEntries': [{'singleInitialItemHash': 1294026524, 'reusablePlugSetHash': 1}]},
}
ADAPTIVE_FRAME = {
    'hash': 1294026524,
    'displayProperties': {'name': 'Adaptive Frame'},
    'itemType': 19,
    'itemTypeDisplayName': 'Intrinsic',
    'classType': 3,
    'inventory': {'tierType': 5, 'bucketTypeHash': 1469714392},
    'plug': {'plugCategoryIdentifier': 'intrinsics'},
}
# A Hunter cloak, which is an ornament plug too. Its cosmetics socket names
# COSMETICS, the list of 712 it can switch to (trimmed to two here).
SPACEWALK_CLOAK = {
    'hash': 2147583688,
    'displayProperties': {'name': 'Spacewalk Cloak'},
    'itemType': 2,
    'itemTypeDisplayName': 'Hunter Cloak',
    'classType': 1,
    'inventory': {'tierType': 5, 'bucketTypeHash': 1585787867},
    'itemCategoryHashes': [23, 49, 20],
    'plug': {'plugCategoryIdentifier': 'armor_skins_hunter_class'},
    'sockets': {
        'socketEntries': [{'singleInitialItemHash': 4248210736, 'reusablePlugSetHash': 236342179}]
    },
}
DEFAULT_SHADER = {
    'hash': 4248210736,
    'displayProperties': {'name': 'Default Shader'},
    'itemType': 19,
    'itemTypeDisplayName': 'Restore Defaults',
    'classType': 3,
    'inventory': {'tierType': 2, 'bucketTypeHash': 2422292810},
    'plug': {'plugCategoryIdentifier': 'shader'},
}
ASTROGRAPH = {
    'hash': 2412474869,
    'displayProperties': {'name': 'Astrograph'},
    'itemType': 19,
    'itemTypeDisplayName': 'Shader',
    'classType': 3,
    'inventory': {'tierType': 5, 'bucketTypeHash': 2422292810},
    'plug': {'plugCategoryIdentifier': 'shader'},
}
# An item Bungie keeps hidden: no plug data, so the copy doesn't keep it.
CLASSIFIED = {
    'hash': 3921006357,
    'displayProperties': {'name': 'Classified'},
    'itemType': 0,
    'classType': 0,
    'inventory': {'tierType': 0, 'bucketTypeHash': 2422292810},
}
# Banshee's order for hand cannons; its icon is the weapon type's picture.
HAND_CANNONS = {
    'hash': 3177548761,
    'displayProperties': {'name': 'Hand Cannons'},
    'itemType': 26,
    'itemTypeDisplayName': 'Gunsmith Order',
    'classType': 3,
    'inventory': {'tierType': 2, 'bucketTypeHash': 635141261},
}
TERRORS_END = {
    'hash': 2176571298,
    'displayProperties': {'name': "Terror's End"},
    'itemType': 14,
    'itemTypeDisplayName': 'Emblem',
    'classType': 3,
    'inventory': {'tierType': 5, 'bucketTypeHash': 4274335291},
}
# A weapon's Kill Tracker and the objective it counts, whose icon is the badge
# of what it counts.
KILL_TRACKER = {
    'hash': 905869860,
    'displayProperties': {'name': 'Kill Tracker'},
    'itemType': 19,
    'classType': 3,
    'inventory': {'tierType': 2, 'bucketTypeHash': 3313201758},
    'plug': {'plugCategoryIdentifier': 'v400.plugs.weapons.masterworks.trackers'},
    'objectives': {'objectiveHashes': [73837075]},
}
ENEMIES_DEFEATED = {
    'hash': 73837075,
    'displayProperties': {
        'icon': '/common/destiny2_content/icons/31c848643d47d317a9b971214a988d22.png'
    },
    'progressDescription': 'Enemies Defeated',
    'inProgressValueStyle': 6,
    'completedValueStyle': 6,
}
# Spacewalk Cloak's cosmetics: entry 0 and entry 682 of the live list.
COSMETICS = {
    'hash': 236342179,
    'reusablePlugItems': [
        {'plugItemHash': 2412474869, 'currentlyCanRoll': True},
        {'plugItemHash': 3921006357, 'currentlyCanRoll': True},
    ],
}

# The manifest's tables the copy reads, each holding its definitions.
DEFINITIONS = {
    'DestinyDamageTypeDefinition': [
        {'hash': 3373582085, 'enumValue': 1, 'displayProperties': {'name': 'Kinetic'}}
    ],
    'DestinyBreakerTypeDefinition': [],
    'DestinyStatDefinition': [],
    'DestinyClassDefinition': [],
    'DestinyEquipableItemSetDefinition': [],
    'DestinyInventoryItemDefinition': [
        FATEBRINGER,
        ADAPTIVE_FRAME,
        SPACEWALK_CLOAK,
        DEFAULT_SHADER,
        ASTROGRAPH,
        CLASSIFIED,
        HAND_CANNONS,
        TERRORS_END,
        KILL_TRACKER,
    ],
    'DestinyInventoryBucketDefinition': [
        {'hash': 1498876634, 'displayProperties': {'name': 'Kinetic Weapons'}, 'bucketOrder': 20},
        {'hash': 1585787867, 'displayProperties': {'name': 'Class Armor'}, 'bucketOrder': 90},
    ],
    'DestinyCollectibleDefinition': [],
    'DestinyObjectiveDefinition': [ENEMIES_DEFEATED],
    'DestinySandboxPerkDefinition': [],
    'DestinyPlugSetDefinition': [COSMETICS],
    'DestinyInventoryItemConstantsDefinition': [],
}


@pytest.fixture
def manifest_path(tmp_path):
    # The manifest file: one table per definition type, each definition a
    # JSON row.
    path = tmp_path / f'{VERSION}.sqlite'
    mconn = sqlite3.connect(path)
    with mconn:
        for table, definitions in DEFINITIONS.items():
            mconn.execute(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, json TEXT)')
            mconn.executemany(
                f'INSERT INTO {table} (json) VALUES (?)', [(json.dumps(d),) for d in definitions]
            )
    mconn.close()
    return path


@pytest.fixture
def db():
    # A new database with nothing copied into it yet.
    conn = connection.open_db(':memory:')
    yield conn
    conn.close()


def test_weapons_armor_plugs_and_gunsmith_orders_are_copied_and_the_rest_skipped(db, manifest_path):
    # The live manifest's 19,268 such definitions are copied and its other
    # 19,626 skipped: here an emblem, and the hidden item the cosmetics name.
    assert manifest.ingest_manifest(db, manifest_path, VERSION)
    names = {r['name'] for r in db.execute('SELECT name FROM DestinyInventoryItemDefinition')}
    assert names == {
        'Fatebringer (Timelost)',
        'Adaptive Frame',
        'Spacewalk Cloak',
        'Default Shader',
        'Astrograph',
        'Hand Cannons',
        'Kill Tracker',
    }
    ammo = db.execute('SELECT ammoType FROM DestinyInventoryItemDefinition WHERE hash = 4219826183')
    assert ammo.fetchone()[0] == 1  # primary


def test_the_objectives_plugs_count_are_copied_with_their_badges(db, manifest_path):
    # The Kill Tracker's "Enemies Defeated", which the report draws as its
    # badge, as DIM does.
    assert manifest.ingest_manifest(db, manifest_path, VERSION)
    rows = db.execute('SELECT * FROM DestinyObjectiveDefinition').fetchall()
    assert [tuple(r) for r in rows] == [
        (
            73837075,
            'Enemies Defeated',
            6,
            6,
            '/common/destiny2_content/icons/31c848643d47d317a9b971214a988d22.png',
        )
    ]


def test_a_plug_list_entry_that_isnt_a_plug_is_skipped(db, manifest_path):
    # The cosmetics list names the Classified item, which the copy doesn't
    # keep; the copy goes ahead without that entry.
    assert manifest.ingest_manifest(db, manifest_path, VERSION)
    rows = db.execute(
        'SELECT plugSetHash, position, plugItemHash, currentlyCanRoll '
        'FROM DestinyItemSocketEntryPlugItemRandomizedDefinition'
    )
    assert [tuple(r) for r in rows] == [(236342179, 0, 2412474869, 1)]


def test_a_version_already_copied_is_not_copied_again(db, manifest_path):
    assert manifest.ingest_manifest(db, manifest_path, VERSION)
    assert not manifest.ingest_manifest(db, manifest_path, VERSION)
    assert [r['version'] for r in db.execute('SELECT version FROM manifest_version')] == [VERSION]
