# Tests for v_armor (db/schema/views/v_armor.sql): every armor copy with its
# base stats, set and bonuses, class, slot and exotic perk, read from rows
# written the way the ingest and the profile extract write them.
import json

import pytest

from sources.bungie import api_mappings
from tests import conftest as c

STATS = ('health', 'melee', 'grenade', 'super_stat', 'class_stat', 'weapons')
STAT_HASHES = {key: h for h, key in api_mappings.STAT_KEYS.items()}


def armor(conn, instance_id):
    return conn.execute("SELECT * FROM v_armor WHERE instance_id = ?", (instance_id,)).fetchone()


def test_base_stats_add_up_the_stat_plugs(conn):
    # The two stat plugs count; the masterwork and tuning plugs don't.
    c.add_armor_def(conn, 200, sockets=[None, c.ARMOR_STAT_PLUG_A, c.ARMOR_STAT_PLUG_A, None])
    c.add_copy(
        conn,
        'a1',
        200,
        [c.MW_PLUG_FULL, c.ARMOR_STAT_PLUG_A, c.ARMOR_STAT_PLUG_A, c.TUNING_HEALTH],
    )
    c.add_copy(conn, 'bare', 200)
    a1, bare = armor(conn, 'a1'), armor(conn, 'bare')
    assert tuple(a1[s] for s in STATS) == (20, 14, 30, 16, 10, 24)
    assert tuple(bare[s] for s in STATS) == (0, 0, 0, 0, 0, 0)


def test_an_intrinsic_plugs_stats_count_too(conn):
    # An exotic class item's "Spirit of" perk carries stats, and so does an
    # older exotic's perk: here Solipsism's Spirit of Inmost Light, +30 super
    # and +25 melee.
    with conn:
        conn.execute(
            "INSERT INTO DestinyInventoryItemDefinition "
            "(hash, name, plugCategoryIdentifier, investmentStats) "
            "VALUES (9201, 'Spirit of Inmost Light', 'intrinsics', ?)",
            (
                json.dumps(
                    [
                        {'statTypeHash': STAT_HASHES['super_stat'], 'value': 30},
                        {'statTypeHash': STAT_HASHES['melee'], 'value': 25},
                    ]
                ),
            ),
        )
    c.add_armor_def(
        conn, 300, name='Solipsism', set_name='', tier=6, slot='Class Armor', armor_class='Warlock'
    )
    c.add_copy(conn, 'x1', 300, [c.ARMOR_STAT_PLUG_A, 9201])
    assert tuple(armor(conn, 'x1')[s] for s in STATS) == (10, 32, 15, 38, 5, 12)


# Armor outside a set is named after its item, without the slot word: one name
# per slot (the gauntlets and chest are legacy pieces from the live vault),
# then a slot word in another case, a last word that isn't a slot, one word,
# and a blank or whitespace-only name.
SET_NAMES = [
    ('Bushido Helm', 'Bushido'),
    ('Red Moon Phantom Grips', 'Red Moon Phantom'),
    ('Frumious Vest', 'Frumious'),
    ('Iron Will Strides', 'Iron Will'),
    ('Reverie Dawn Cloak', 'Reverie Dawn'),
    ('Iron Forerunner HELM', 'Iron Forerunner'),
    ('Exotic Engram', 'Exotic Engram'),
    ('Helm', 'Helm'),
    ('', 'Unknown Armor'),
    ('   ', '   '),
]


@pytest.mark.parametrize('name, set_name', SET_NAMES)
def test_set_name_outside_a_set_drops_the_slot_word(conn, name, set_name):
    c.add_armor_def(conn, 200, name=name, set_name='')
    c.add_copy(conn, 'a1', 200)
    assert armor(conn, 'a1')['set_name'] == set_name


def test_set_bonuses_class_and_slot(conn):
    # A set's bonuses are each perk's name and text as Bungie wrote it; armor
    # outside a set has none.
    c.add_armor_def(conn, 200, name='Luminopotent Boots', set_name='Luminopotent', set_hash=77)
    c.add_armor_def(conn, 201, name='Old Helm', set_name='')
    with conn:
        conn.executemany(
            "INSERT INTO DestinySandboxPerkDefinition (hash, name, description) VALUES (?, ?, ?)",
            [
                (701, 'Ionic Overclock', 'Gain [Arc] energy.'),
                (702, 'Shock and Clear', 'Kills\n\njolt.'),
            ],
        )
    c.add_set_perks(conn, 77, [(2, 701), (4, 702)])
    c.add_copy(conn, 'set', 200)
    c.add_copy(conn, 'none', 201)
    in_set, none = armor(conn, 'set'), armor(conn, 'none')
    assert (in_set['set_name'], in_set['two_pc'], in_set['four_pc']) == (
        'Luminopotent',
        'Ionic Overclock: Gain [Arc] energy.',
        'Shock and Clear: Kills\n\njolt.',
    )
    assert (in_set['armor_class'], in_set['slot']) == ('Titan', 'Helmet')
    assert (none['set_name'], none['two_pc'], none['four_pc']) == ('Old', None, None)


def test_an_exotics_perk_is_its_starting_intrinsic(conn):
    # The definition's starting plug, whichever perk the copy holds.
    c.add_armor_def(conn, 300, name='Heart', set_name='', tier=6, sockets=[c.INTRINSIC_ADAPTIVE])
    c.add_copy(conn, 'x1', 300, [c.INTRINSIC_AGGRESSIVE])
    x1 = armor(conn, 'x1')
    assert (x1['is_exotic'], x1['exotic_perk_name'], x1['exotic_perk_desc']) == (
        1,
        'Adaptive Frame',
        'A well-rounded grip.',
    )
