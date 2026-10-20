# Tests for loading the stored copies (analyze/inventory.py): which weapons
# the analysis compares, and what each weapon and armor copy carries. The
# round trips save their copies the way a run does: a profile response through
# the extract.
import models
from analyze import inventory
from extract.bungie import inventory as snapshot
from extract.bungie import profile
from tests import conftest as c

# Intrinsic, barrel, magazine and two traits.
SOCKETS = [c.INTRINSIC_ADAPTIVE, c.BARREL_PERK_X, c.MAG_PERK_P, c.TRAIT_PERK_A, c.TRAIT_PERK_C]


def save_profile(conn, **parts):
    # Save a profile response (make_profile's parts) the way a run saves it.
    snapshot.save_snapshot(conn, profile.profile_rows(conn, c.make_profile(**parts)))


def test_analysis_compares_legendary_and_up_and_flags_lower_tiers(conn):
    # Every copy is stored; the analysis loads the Legendary and Exotic ones
    # that have a trait socket, and flags every copy below Legendary.
    c.add_weapon_def(conn, 100, tier=5)
    c.add_weapon_def(conn, 101, name='Exotic Rifle', tier=6)
    c.add_weapon_def(conn, 102, name='Rare Rifle', tier=4)
    c.add_copy(conn, 'legendary', 100, SOCKETS)
    c.add_copy(conn, 'no traits', 100, SOCKETS[:3])
    c.add_copy(conn, 'exotic', 101, SOCKETS)
    c.add_copy(conn, 'rare', 102, SOCKETS)
    weapons = inventory.load_weapons(conn)
    assert [w.instance_id for w in weapons] == ['exotic', 'legendary']
    assert inventory.load_below_legendary(conn) == ['rare']


def test_a_weapon_copy_loads_with_its_roll(conn):
    # Each perk socket with its kind and the perks the copy can switch to, in
    # the game's order; a socket it can't switch holds its plugged perk, and
    # an intrinsic it can't switch isn't a perk socket.
    with conn:
        conn.executemany(
            'INSERT INTO DestinyInventoryItemDefinition (hash, name, plugCategoryIdentifier) '
            'VALUES (?, ?, ?)',
            [
                (1, 'Arrowhead Brake', 'barrels'),
                (2, 'Smallbore', 'barrels'),
                (3, 'Outlaw', 'frames'),
                (4, 'Rampage', 'frames'),
                (5, 'Kill Clip', 'frames'),
            ],
        )
    c.add_weapon_def(conn, 100, 'Fatebringer', sockets=[c.INTRINSIC_ADAPTIVE, 2, 3, 4])
    save_profile(
        conn,
        vault=[{'itemHash': 100, 'itemInstanceId': 'w1'}],
        sockets={'w1': [c.INTRINSIC_ADAPTIVE, 2, 3, 5]},
        reusable={'w1': {1: [1, 2], 3: [4, 5]}},
    )
    (w1,) = inventory.load_weapons(conn)
    assert (w1.instance_id, w1.item_hash) == ('w1', 100)
    assert [(s.kind, s.perks) for s in w1.roll] == [
        ('barrel', ['Arrowhead Brake', 'Smallbore']),
        ('trait', ['Outlaw']),
        ('trait', ['Rampage', 'Kill Clip']),
    ]


def test_an_armor_copy_loads_with_its_set_bonus_and_stats(conn):
    with conn:
        conn.execute("INSERT INTO DestinyEquipableItemSetDefinition VALUES (77, 'Bushido')")
        conn.executemany(
            "INSERT INTO DestinySandboxPerkDefinition (hash, name, description) VALUES (?, ?, ?)",
            [(701, 'Two', 'two pieces.'), (702, 'Four', 'four pieces.')],
        )
        conn.executemany(
            "INSERT INTO DestinyItemSetPerkDefinition VALUES (77, ?, ?, ?)",
            [(0, 2, 701), (1, 4, 702)],
        )
    c.add_armor_def(conn, 400, set_hash=77, sockets=[c.ARMOR_STAT_PLUG_A])
    save_profile(
        conn,
        vault=[{'itemHash': 400, 'itemInstanceId': i} for i in ('a1', 'a2')],
        sockets={'a1': [c.ARMOR_STAT_PLUG_A]},
    )

    a1, a2 = inventory.load_armor(conn)
    assert a1.armor == a2.armor
    assert a1.armor.set_bonus == models.ArmorSetBonus('Two: two pieces.', 'Four: four pieces.')
    assert a1.stats == models.ArmorStats(10, 7, 15, 8, 5, 12)
    assert a2.stats == models.ArmorStats()
