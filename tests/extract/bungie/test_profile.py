# Tests for reading the profile response (extract/bungie/profile.py) into rows
# for the component tables.
import json

from extract.bungie import profile
from sources.bungie import api_mappings
from tests import conftest as c

RPM = next(h for h, key in api_mappings.STAT_KEYS.items() if key == 'rpm')


def item(item_hash, instance_id, state=0):
    return {'itemHash': item_hash, 'itemInstanceId': instance_id, 'state': state}


def test_keeps_every_weapon_and_armor_copy(conn):
    # Whatever their tier; only items that aren't weapons or armor, and stacks
    # without an instance id, are left out.
    c.add_weapon_def(conn, 100, tier=5)
    c.add_weapon_def(conn, 101, tier=4)  # a rare weapon
    c.add_armor_def(conn, 200, tier=4)
    response = c.make_profile(
        vault=[
            item(100, 'legendary'),
            item(101, 'rare'),
            item(200, 'armor'),
            item(999, 'not gear'),
            {'itemHash': 100},  # no instance
        ]
    )
    rows = profile.profile_rows(conn, response)
    assert [r[0] for r in rows.items] == ['legendary', 'rare', 'armor']


def test_copies_your_characters_carry_are_kept_too(conn):
    # The vault, each character's inventory and each character's equipped gear
    # are three lists; a copy left out would be deleted from the database as
    # gone.
    c.add_weapon_def(conn, 100)
    response = c.make_profile(
        vault=[item(100, 'vault')], carried=[item(100, 'carried')], equipped=[item(100, 'equipped')]
    )
    rows = profile.profile_rows(conn, response)
    assert [r[0] for r in rows.items] == ['vault', 'carried', 'equipped']


def test_copies_and_their_instance_data(conn):
    # A copy the profile sends no instance data for has no instance row; a
    # damage type the definitions don't have is NULL.
    c.add_weapon_def(conn, 100)
    void = c.DAMAGE_TYPES[4][0]
    response = c.make_profile(
        vault=[item(100, 'w1', state=5)],
        equipped=[item(100, 'w2'), item(100, 'w3')],
        instances={
            'w1': {'primaryStat': {'value': 2010}, 'gearTier': 4, 'damageTypeHash': void},
            'w2': {'damageTypeHash': 0, 'isEquipped': True},
        },
    )
    rows = profile.profile_rows(conn, response)
    # (itemInstanceId, itemHash, state)
    assert rows.items == [('w1', 100, 5), ('w2', 100, 0), ('w3', 100, 0)]
    # (itemInstanceId, isEquipped, primaryStat.value, gearTier, damageTypeHash)
    assert rows.instances == [('w1', None, 2010, 4, void), ('w2', 1, None, None, None)]


def test_components_are_kept_as_sent_trimmed_to_the_fields_read(conn):
    # One row per copy the profile sends a component for. Hashes stay whether
    # or not the definition tables have them, an empty socket is {}, and only
    # the fields the app reads are kept.
    c.add_weapon_def(conn, 100)
    response = c.make_profile(
        vault=[item(100, 'w1'), item(100, 'w2')],
        sockets={'w1': [c.INTRINSIC_ADAPTIVE, 7777, None]},
        reusable={'w1': {1: [c.TRAIT_PERK_A, 8888], 5: [c.TRAIT_PERK_B]}},
        stats={'w1': {RPM: 140, 9999: 1}},
    )
    data = response['itemComponents']
    for socket in data['sockets']['data']['w1']['sockets']:
        socket.update(isEnabled=True, isVisible=True)
    for plug in data['reusablePlugs']['data']['w1']['plugs']['1']:
        plug.update(canInsert=True, enabled=True)
    rows = profile.profile_rows(conn, response)
    assert [r[0] for r in rows.sockets] == ['w1']
    assert json.loads(rows.sockets[0][1]) == [
        {'plugHash': c.INTRINSIC_ADAPTIVE},
        {'plugHash': 7777},
        {},
    ]
    assert json.loads(rows.reusable_plugs[0][1]) == {
        '1': [{'plugItemHash': c.TRAIT_PERK_A}, {'plugItemHash': 8888}],
        '5': [{'plugItemHash': c.TRAIT_PERK_B}],
    }
    assert json.loads(rows.stats[0][1]) == {str(RPM): 140, '9999': 1}


def test_plug_objectives_keep_each_plugs_objectives_as_sent(conn):
    # Keyed by plug, each objective's hash and progress; completionValue,
    # complete and visible are left out.
    c.add_weapon_def(conn, 100)
    response = c.make_profile(
        vault=[item(100, 'w1')],
        objectives={
            'w1': {
                c.KILL_TRACKER: [(c.ENEMIES_DEFEATED, 46), (9999, 1)],
                8888: [(c.ENEMIES_DEFEATED, 3)],
            }
        },
    )
    rows = profile.profile_rows(conn, response)
    assert [r[0] for r in rows.plug_objectives] == ['w1']
    assert json.loads(rows.plug_objectives[0][1]) == {
        str(c.KILL_TRACKER): [
            {'objectiveHash': c.ENEMIES_DEFEATED, 'progress': 46},
            {'objectiveHash': 9999, 'progress': 1},
        ],
        '8888': [{'objectiveHash': c.ENEMIES_DEFEATED, 'progress': 3}],
    }
