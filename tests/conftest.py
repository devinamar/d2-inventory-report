# Shared fixtures for D2 Inventory Report tests.
#
# Fixtures and factory functions, so unit tests never need network calls or
# a real Bungie manifest database.
import io
import json
import zlib

import pytest
import requests

import models
from db import connection
from extract import bungie as bungie_extract
from report import report
from sources.bungie import api_mappings

# Plug hash constants
# Fake hashes used across test files. Each has a real Bungie
# plugCategoryIdentifier, since the views sort plugs by category: v_plug's perk
# kinds, v_armor's stat plugs, v_armor_tuning's mods, v_kill_tracker's trackers.

TRAIT_PERK_A = 1001  # "Rampage"     — category: frames
TRAIT_PERK_B = 1002  # "Kill Clip"   — category: frames
TRAIT_PERK_C = 1003  # "Outlaw"      — category: frames
TRAIT_PERK_D = 1004  # "Subsistence" — category: frames
TRAIT_PERK_E = 1005  # "Firefly"     — category: frames

BARREL_PERK_X = 2001  # "Hammer-Forged Rifling" — category: barrels
BARREL_PERK_Y = 2002  # "Fluted Barrel"         — category: barrels

MAG_PERK_P = 3001  # "Appended Mag"   — category: magazines
MAG_PERK_Q = 3002  # "Tactical Mag"   — category: magazines

ORIGIN_PERK = 4001  # "Vanguard's Vindication" — category: origins

INTRINSIC_ADAPTIVE = 5001  # "Adaptive Frame" — category: intrinsics
INTRINSIC_AGGRESSIVE = 5002  # "Aggressive Frame" — category: intrinsics

# Armor-related plugs
ARMOR_STAT_PLUG_A = 6001  # intrinsic stat plug — category: armor_stats
MW_PLUG_FULL = 6101  # masterwork plug — category: v400.plugs.armor.masterworks.stat.resistance
TUNING_HEALTH = (
    6201  # +5 Health tuning — category: core.gear_systems.armor_tiering.plugs.tuning.mods
)
TUNING_BALANCED = 6202  # Balanced Tuning  — same category but +1 to all
TUNING_MELEE = 6203  # +5 Melee tuning — same category

TUNING_CATEGORY = 'core.gear_systems.armor_tiering.plugs.tuning.mods'

# Kill trackers — category: v400.plugs.weapons.masterworks.trackers
KILL_TRACKER = 7001
CRUCIBLE_TRACKER = 7002

# Objectives the trackers count, with their live hashes (two of those DIM
# reads as PvE and PvP): hash → (progressDescription, inProgressValueStyle,
# completedValueStyle, icon); style 6 is Integer.
ENEMIES_DEFEATED = 73837075
OPPONENTS_DEFEATED = 74070459
OBJECTIVES = {
    ENEMIES_DEFEATED: (
        'Enemies Defeated',
        6,
        6,
        '/common/destiny2_content/icons/31c848643d47d317a9b971214a988d22.png',
    ),
    OPPONENTS_DEFEATED: (
        'Crucible Opponents Defeated',
        6,
        6,
        '/common/destiny2_content/icons/66317c523dd68205dcc753c7563d5068.png',
    ),
}


# Plug database
# Each entry: hash → {name, category, icon, description, investmentStats}

PLUG_DB = {
    TRAIT_PERK_A: {
        'name': 'Rampage',
        'category': 'frames',
        'icon': '/img/rampage.png',
        'description': 'Kills grant bonus damage.',
        'investmentStats': [],
    },
    TRAIT_PERK_B: {
        'name': 'Kill Clip',
        'category': 'frames',
        'icon': '/img/killclip.png',
        'description': 'Reloading after a kill grants bonus damage.',
        'investmentStats': [],
    },
    TRAIT_PERK_C: {
        'name': 'Outlaw',
        'category': 'frames',
        'icon': '/img/outlaw.png',
        'description': 'Precision kills greatly decrease reload time.',
        'investmentStats': [],
    },
    TRAIT_PERK_D: {
        'name': 'Subsistence',
        'category': 'frames',
        'icon': '/img/subsistence.png',
        'description': 'Defeating targets partially reloads the magazine.',
        'investmentStats': [],
    },
    TRAIT_PERK_E: {
        'name': 'Firefly',
        'category': 'frames',
        'icon': '/img/firefly.png',
        'description': 'Precision kills cause the target to explode.',
        'investmentStats': [],
    },
    BARREL_PERK_X: {
        'name': 'Hammer-Forged Rifling',
        'category': 'barrels',
        'icon': '/img/hammerforged.png',
        'description': 'Increased range.',
        'investmentStats': [],
    },
    BARREL_PERK_Y: {
        'name': 'Fluted Barrel',
        'category': 'barrels',
        'icon': '/img/fluted.png',
        'description': 'Increased handling and stability.',
        'investmentStats': [],
    },
    MAG_PERK_P: {
        'name': 'Appended Mag',
        'category': 'magazines',
        'icon': '/img/appendedmag.png',
        'description': 'Increased magazine size.',
        'investmentStats': [],
    },
    MAG_PERK_Q: {
        'name': 'Tactical Mag',
        'category': 'magazines',
        'icon': '/img/tacticalmag.png',
        'description': 'Increased magazine size, reload speed, and stability.',
        'investmentStats': [],
    },
    ORIGIN_PERK: {
        'name': "Vanguard's Vindication",
        'category': 'origins',
        'icon': '/img/vanguard.png',
        'description': 'Final blows grant health regeneration.',
        'investmentStats': [],
    },
    INTRINSIC_ADAPTIVE: {
        'name': 'Adaptive Frame',
        'category': 'intrinsics',
        'icon': '/img/adaptive.png',
        'description': 'A well-rounded grip.',
        'investmentStats': [],
    },
    INTRINSIC_AGGRESSIVE: {
        'name': 'Aggressive Frame',
        'category': 'intrinsics',
        'icon': '/img/aggressive.png',
        'description': 'High damage, slow fire rate.',
        'investmentStats': [],
    },
    ARMOR_STAT_PLUG_A: {
        'name': 'Stat Plug A',
        'category': 'armor_stats',
        'icon': '',
        'description': '',
        'investmentStats': [
            {'statTypeHash': 392767087, 'value': 10},  # health
            {'statTypeHash': 4244567218, 'value': 7},  # melee
            {'statTypeHash': 1735777505, 'value': 15},  # grenade
            {'statTypeHash': 144602215, 'value': 8},  # super_stat
            {'statTypeHash': 1943323491, 'value': 5},  # class_stat
            {'statTypeHash': 2996146975, 'value': 12},  # weapons
        ],
    },
    MW_PLUG_FULL: {
        'name': 'Upgrade Armor',
        'category': 'v400.plugs.armor.masterworks.stat.resistance',
        'icon': '',
        'description': '',
        'investmentStats': [
            {'statTypeHash': 392767087, 'value': 2},
        ],
    },
    TUNING_HEALTH: {
        'name': '+5 Health / -5 Melee',
        'category': 'core.gear_systems.armor_tiering.plugs.tuning.mods',
        'icon': '',
        'description': '',
        'investmentStats': [
            {'statTypeHash': 392767087, 'value': 5},  # +5 health
            {'statTypeHash': 4244567218, 'value': -5},  # -5 melee
        ],
    },
    TUNING_MELEE: {
        'name': '+5 Melee / -5 Health',
        'category': 'core.gear_systems.armor_tiering.plugs.tuning.mods',
        'icon': '',
        'description': '',
        'investmentStats': [
            {'statTypeHash': 4244567218, 'value': 5},  # +5 melee
            {'statTypeHash': 392767087, 'value': -5},  # -5 health
        ],
    },
    TUNING_BALANCED: {
        'name': 'Balanced Tuning',
        'category': 'core.gear_systems.armor_tiering.plugs.tuning.mods',
        'icon': '',
        'description': '',
        'investmentStats': [
            {'statTypeHash': 392767087, 'value': 1},
            {'statTypeHash': 4244567218, 'value': 1},
            {'statTypeHash': 1735777505, 'value': 1},
            {'statTypeHash': 144602215, 'value': 1},
            {'statTypeHash': 1943323491, 'value': 1},
            {'statTypeHash': 2996146975, 'value': 1},
        ],
    },
    KILL_TRACKER: {
        'name': 'Kill Tracker',
        'category': 'v400.plugs.weapons.masterworks.trackers',
        'icon': '',
        'description': '',
        'investmentStats': [],
    },
    CRUCIBLE_TRACKER: {
        'name': 'Crucible Tracker',
        'category': 'v400.plugs.weapons.masterworks.trackers',
        'icon': '',
        'description': '',
        'investmentStats': [],
    },
}

# A weapon copy's sockets: intrinsic, barrel, magazine, two traits, origin, and
# an armor masterwork plug standing in for a socket that isn't a perk.
WEAPON_SOCKETS = [
    INTRINSIC_ADAPTIVE,
    BARREL_PERK_X,
    MAG_PERK_P,
    TRAIT_PERK_A,
    TRAIT_PERK_C,
    ORIGIN_PERK,
    MW_PLUG_FULL,
]


# Factory functions


def make_armor(name='Test Helm', set_name='Bushido', **kwargs):
    return models.Armor(name=name, set_name=set_name, **kwargs)


def make_armor_inst(armor, instance_id='armor_1', stats=None, **kwargs):
    return models.ArmorInstance(
        instance_id=instance_id, armor=armor, stats=stats or models.ArmorStats(), **kwargs
    )


# Pytest fixtures

# The damage types the manifest defines (DestinyDamageTypeDefinition): enum
# value -> (hash, name).
DAMAGE_TYPES = {
    1: (3373582085, 'Kinetic'),
    2: (2303181850, 'Arc'),
    3: (1847026933, 'Solar'),
    4: (3454344768, 'Void'),
    6: (151347233, 'Stasis'),
    7: (3949783978, 'Strand'),
}

# The weapon and armor buckets (DestinyInventoryBucketDefinition): hash, name,
# bucketOrder.
KINETIC_BUCKET, HELMET_BUCKET = 1498876634, 3448274439
BUCKETS = [
    (KINETIC_BUCKET, 'Kinetic Weapons', 20),
    (2465295065, 'Energy Weapons', 30),
    (953998645, 'Power Weapons', 40),
    (HELMET_BUCKET, 'Helmet', 50),
    (3551918588, 'Gauntlets', 60),
    (14239492, 'Chest Armor', 70),
    (20886954, 'Leg Armor', 80),
    (1585787867, 'Class Armor', 90),
]

# The classes (DestinyClassDefinition): hash, classType, name.
CLASSES = [(3655393761, 0, 'Titan'), (671679327, 1, 'Hunter'), (2271682572, 2, 'Warlock')]
BUCKET_HASHES = {name: h for h, name, _ in BUCKETS}
CLASS_TYPES = {name: class_type for _, class_type, name in CLASSES}


@pytest.fixture
def conn():
    # In-memory db with the current schema, holding what the manifest ingest
    # and the extract would: the test plugs with their investment stats and
    # objectives, the damage types, the stats the app names, the weapon and
    # armor buckets, the classes, and the app's stat vocabulary.
    c = connection.open_db(':memory:')
    with c:
        c.executemany(
            "INSERT INTO DestinyInventoryItemDefinition "
            "(hash, name, description, icon, plugCategoryIdentifier, investmentStats) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    h,
                    e['name'],
                    e['description'],
                    e['icon'],
                    e['category'],
                    json.dumps(e['investmentStats']),
                )
                for h, e in PLUG_DB.items()
            ],
        )
        c.executemany(
            "INSERT INTO DestinyObjectiveDefinition VALUES (?, ?, ?, ?, ?)",
            [(h, *entry) for h, entry in OBJECTIVES.items()],
        )
        c.executemany(
            "INSERT INTO DestinyDamageTypeDefinition (hash, enumValue, name) VALUES (?, ?, ?)",
            [(h, enum, name) for enum, (h, name) in DAMAGE_TYPES.items()],
        )
        c.executemany(
            "INSERT INTO DestinyStatDefinition VALUES (?, ?, ?)",
            [(h, key, f'/img/{key}.png') for h, key in api_mappings.STAT_KEYS.items()],
        )
        c.executemany("INSERT INTO DestinyInventoryBucketDefinition VALUES (?, ?, ?)", BUCKETS)
        c.executemany("INSERT INTO DestinyClassDefinition VALUES (?, ?, ?)", CLASSES)
    bungie_extract.save_vocabulary(c, api_mappings.STAT_KEYS)
    yield c
    c.close()


# Definitions and copies in the db, written the way the manifest ingest and
# the profile extract write them.


def socket_entries(plugs) -> str:
    # A definition's socketEntries: one entry per starting plug, 0 for a
    # socket that starts empty (None).
    return json.dumps([{'singleInitialItemHash': plug or 0} for plug in plugs])


def add_weapon_def(
    conn, item_hash, name='Test Rifle', tier=5, damage_type=1, sockets=None, **fields
):
    # A kinetic Auto Rifle definition with one socket entry per entry in
    # sockets, the socket's starting plug (default: the Adaptive Frame
    # intrinsic). fields sets other DestinyInventoryItemDefinition columns.
    if sockets is None:
        sockets = [INTRINSIC_ADAPTIVE]
    damage_hash = None
    if damage_type:
        damage_hash = DAMAGE_TYPES[damage_type][0]
    columns = {
        'hash': item_hash,
        'name': name,
        'itemType': 3,
        'itemTypeDisplayName': 'Auto Rifle',
        'tierType': tier,
        'bucketTypeHash': KINETIC_BUCKET,
        'defaultDamageTypeHash': damage_hash,
        'socketEntries': socket_entries(sockets),
        **fields,
    }
    with conn:
        conn.execute(
            f"INSERT INTO DestinyInventoryItemDefinition ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' * len(columns))})",
            tuple(columns.values()),
        )


def add_plug_set(conn, item_hash, socket_idx, set_hash, plugs, key='randomizedPlugSetHash'):
    # A plug set listing plugs ([(plug hash, currentlyCanRoll)]) in that
    # order, named by the definition's socket socket_idx as its key
    # (randomizedPlugSetHash, or reusablePlugSetHash for a set to switch to).
    with conn:
        conn.execute(
            "INSERT INTO DestinyPlugSetDefinition VALUES (?, ?)",
            (
                set_hash,
                json.dumps([{'plugItemHash': h, 'currentlyCanRoll': bool(r)} for h, r in plugs]),
            ),
        )
        conn.execute(
            "UPDATE DestinyInventoryItemDefinition "
            f"SET socketEntries = json_set(socketEntries, '$[{socket_idx}].{key}', ?) "
            "WHERE hash = ?",
            (set_hash, item_hash),
        )


def add_armor_def(
    conn,
    item_hash,
    name='Test Helm',
    set_name='Bushido',
    set_hash=None,
    tier=5,
    sockets=(),
    slot='Helmet',
    armor_class='Titan',
):
    # An armor definition (a Titan helmet unless slot and armor_class say
    # otherwise), the armor set it belongs to and its socket entries. A
    # set_name makes an armor set of that name (set_hash, else a hash of the
    # name); with set_name '' the piece is outside a set. sockets is each
    # socket's starting plug (None for none).
    if set_name and set_hash is None:
        set_hash = zlib.crc32(set_name.encode())
    with conn:
        if set_name:
            conn.execute(
                "INSERT OR IGNORE INTO DestinyEquipableItemSetDefinition (hash, name) "
                "VALUES (?, ?)",
                (set_hash, set_name),
            )
        conn.execute(
            "INSERT INTO DestinyInventoryItemDefinition "
            "(hash, name, itemType, classType, tierType, bucketTypeHash, equipableItemSetHash, "
            "socketEntries) VALUES (?, ?, 2, ?, ?, ?, ?, ?)",
            (
                item_hash,
                name,
                CLASS_TYPES[armor_class],
                tier,
                BUCKET_HASHES[slot],
                set_hash,
                socket_entries(sockets),
            ),
        )


def add_set_perks(conn, set_hash, perks):
    # The armor set's bonuses, perks: [(requiredSetCount, sandboxPerkHash)].
    with conn:
        conn.execute(
            "UPDATE DestinyEquipableItemSetDefinition SET setPerks = ? WHERE hash = ?",
            (
                json.dumps([{'requiredSetCount': n, 'sandboxPerkHash': h} for n, h in perks]),
                set_hash,
            ),
        )


def add_copy(
    conn,
    instance_id,
    item_hash,
    sockets=(),
    reusable=None,
    stats=None,
    state=0,
    damage_type=None,
    objectives=None,
    gear_tier=None,
):
    # A copy: its DestinyItemComponent row, its instance data when it has a
    # damage_type (an enum value) or a gear_tier, the plug in each socket (sockets, None for
    # an empty one), the plugs a socket can switch to (reusable, {socket
    # index: [plug hashes]}), its stats ({stat hash: value}) and its plugs'
    # objective progress (objectives, {plug hash: [(objective hash,
    # progress)]}).
    with conn:
        conn.execute(
            "INSERT INTO DestinyItemComponent (itemInstanceId, itemHash, state) VALUES (?, ?, ?)",
            (instance_id, item_hash, state),
        )
        if damage_type or gear_tier:
            damage_hash = None
            if damage_type:
                damage_hash = DAMAGE_TYPES[damage_type][0]
            conn.execute(
                "INSERT INTO DestinyItemInstanceComponent "
                "(itemInstanceId, damageTypeHash, gearTier) VALUES (?, ?, ?)",
                (instance_id, damage_hash, gear_tier),
            )
        conn.executemany(
            "INSERT INTO DestinyItemSocketsComponent (itemInstanceId, socketIndex, plugHash) "
            "VALUES (?, ?, ?)",
            [(instance_id, idx, plug) for idx, plug in enumerate(sockets)],
        )
        conn.executemany(
            "INSERT INTO DestinyItemReusablePlugsComponent "
            "(itemInstanceId, socketIndex, position, plugItemHash) VALUES (?, ?, ?, ?)",
            [
                (instance_id, idx, position, plug)
                for idx, plugs in (reusable or {}).items()
                for position, plug in enumerate(plugs)
            ],
        )
        conn.executemany(
            "INSERT INTO DestinyItemStatsComponent VALUES (?, ?, ?)",
            [(instance_id, h, v) for h, v in (stats or {}).items()],
        )
        conn.executemany(
            "INSERT INTO DestinyItemPlugObjectivesComponent "
            "(itemInstanceId, plugHash, objectiveHash, progress) VALUES (?, ?, ?, ?)",
            [
                (instance_id, plug, objective, progress)
                for plug, entries in (objectives or {}).items()
                for objective, progress in entries
            ],
        )


def add_armor(
    conn,
    instance_id,
    stats,
    *,
    set_name='Bushido',
    slot='Helmet',
    armor_class='Warlock',
    name=None,
    exotic=False,
    tuning=('health',),
    gear_tier=5,
    perks=(),
    score=None,
):
    # One armor copy with a definition of its own (named after its set and
    # slot unless name is given; Exotic or Legendary): a stat plug carrying
    # its base stats ({stat name: value}), a tuning plug raising each stat in
    # tuning, its gear tier, an intrinsic plug named after each of perks, and
    # its armor_score row when score is given.
    item_hash = zlib.crc32(instance_id.encode())
    tier = 5
    if exotic:
        tier = 6
    add_armor_def(
        conn,
        item_hash,
        name or f'{set_name} {slot}',
        set_name,
        tier=tier,
        slot=slot,
        armor_class=armor_class,
    )
    stat_hash = {key: h for h, key in api_mappings.STAT_KEYS.items()}
    stat_plug = (zlib.crc32(f'stats {instance_id}'.encode()), '', 'armor_stats', stats)
    tuning_plugs = [
        (zlib.crc32(f'tuning {stat}'.encode()), '', TUNING_CATEGORY, {stat: 5}) for stat in tuning
    ]
    perk_plugs = [(zlib.crc32(f'perk {p}'.encode()), p, 'intrinsics', {}) for p in perks]
    plugs = [stat_plug, *tuning_plugs, *perk_plugs]
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO DestinyInventoryItemDefinition "
            "(hash, name, plugCategoryIdentifier, investmentStats) VALUES (?, ?, ?, ?)",
            [
                (
                    h,
                    plug_name,
                    category,
                    json.dumps(
                        [{'statTypeHash': stat_hash[k], 'value': v} for k, v in values.items()]
                    ),
                )
                for h, plug_name, category, values in plugs
            ],
        )
    sockets = [stat_plug[0], *(h for h, _, _, _ in perk_plugs)]
    reusable = {}
    if tuning_plugs:
        reusable = {len(sockets): [h for h, _, _, _ in tuning_plugs]}
        sockets.append(tuning_plugs[0][0])
    add_copy(conn, instance_id, item_hash, sockets, reusable, gear_tier=gear_tier)
    if score is not None:
        with conn:
            conn.execute(
                "INSERT INTO armor_score (instance_id, preferred_score) VALUES (?, ?)",
                (instance_id, score),
            )


def add_preference(conn, name, grade, rank=0, stats=()):
    # Save a set's armor preference: its grade, rank and stat picks.
    picks = [*stats, None, None, None][:3]
    with conn:
        conn.execute(
            "INSERT INTO armor_preference (name, stat_1, stat_2, stat_3, grade, rank) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, *picks, grade, rank),
        )


def make_profile(
    vault=(),
    equipped=(),
    sockets=None,
    reusable=None,
    instances=None,
    stats=None,
    objectives=None,
    carried=(),
):
    # The parts of a profile response the extract reads. vault, carried (a
    # character's inventory) and equipped are item dicts ({'itemHash',
    # 'itemInstanceId', 'state'}); the rest are keyed by instance id: sockets
    # ([plug hash, or None for empty]), reusable ({socket index: [plug
    # hashes]}), instances (component 300 dicts), stats ({stat hash: value})
    # and objectives ({plug hash: [(objective hash, progress)]}, each one
    # complete and visible).
    return {
        'profileInventory': {'data': {'items': list(vault)}},
        'characterInventories': {'data': {'char1': {'items': list(carried)}}},
        'characterEquipment': {'data': {'char1': {'items': list(equipped)}}},
        'itemComponents': {
            'sockets': {
                'data': {
                    iid: {'sockets': [{'plugHash': p} if p else {} for p in plugs]}
                    for iid, plugs in (sockets or {}).items()
                }
            },
            'reusablePlugs': {
                'data': {
                    iid: {
                        'plugs': {
                            str(idx): [{'plugItemHash': h} for h in hashes]
                            for idx, hashes in by_socket.items()
                        }
                    }
                    for iid, by_socket in (reusable or {}).items()
                }
            },
            'instances': {'data': dict(instances or {})},
            'stats': {
                'data': {
                    iid: {'stats': {str(h): {'statHash': h, 'value': v} for h, v in s.items()}}
                    for iid, s in (stats or {}).items()
                }
            },
            'plugObjectives': {
                'data': {
                    iid: {
                        'objectivesPerPlug': {
                            str(plug): [
                                {
                                    'objectiveHash': h,
                                    'progress': p,
                                    'completionValue': 1,
                                    'complete': True,
                                    'visible': True,
                                }
                                for h, p in entries
                            ]
                            for plug, entries in by_plug.items()
                        }
                    }
                    for iid, by_plug in (objectives or {}).items()
                }
            },
        },
    }


# Replies from Bungie, DIM, Google and GitHub, for the stand-ins that replace
# the network in the sources' tests.


def make_response(status=200, body=b'', payload=None, headers=None):
    # A requests.Response as the network hands it back: its status, headers and
    # body (payload, a JSON value, when given), with the encoding requests reads
    # from the headers.
    response = requests.Response()
    response.status_code = status
    response.headers.update(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode()
        response.headers.setdefault('Content-Type', 'application/json')
    response.raw = io.BytesIO(body)
    response.encoding = requests.utils.get_encoding_from_headers(response.headers)
    return response


# The report as a run writes it, for the tests of its templates.


def write_report(conn, folder):
    # (html, markdown): the report report.write writes for conn into folder,
    # for the player Name#1234.
    report.write(conn, folder, 'Name#1234')
    html = (folder / 'd2_report_Name.html').read_text(encoding='utf-8')
    markdown = (folder / 'd2_report_Name.md').read_text(encoding='utf-8')
    return html, markdown


def report_page(html, name):
    # One page's part of the report's HTML: from its section to the next
    # page's.
    return html.split(f'id="page-{name}"')[1].split('<section class="page"')[0]
