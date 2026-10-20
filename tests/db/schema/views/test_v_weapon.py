# Tests for v_weapon (db/schema/views/v_weapon.sql): every weapon copy with its
# definition, family, slot, element, archetype, season and icons, read from
# rows written the way the ingest and the profile extract write them.
import pytest

from sources.bungie import api_mappings
from tests import conftest as c

SOCKETS = c.WEAPON_SOCKETS
RPM = next(h for h, key in api_mappings.STAT_KEYS.items() if key == 'rpm')


def weapon(conn, instance_id):
    return conn.execute("SELECT * FROM v_weapon WHERE instance_id = ?", (instance_id,)).fetchone()


def season(conn, instance_id):
    w = weapon(conn, instance_id)
    return (w['season_num'], w['season_name'], w['season_date'])


def test_weapon_lists_every_copy_with_its_tier(conn):
    # Copies without a trait socket and lower tiers are listed too; the
    # analysis decides which to compare.
    c.add_weapon_def(conn, 100)
    c.add_weapon_def(conn, 101, tier=4)
    c.add_copy(conn, 'traits', 100, SOCKETS)
    c.add_copy(conn, 'none', 100, SOCKETS[:3])
    c.add_copy(conn, 'rare', 101, SOCKETS)
    rows = conn.execute("SELECT instance_id, tier FROM v_weapon ORDER BY instance_id").fetchall()
    assert [tuple(r) for r in rows] == [('none', 5), ('rare', 4), ('traits', 5)]


@pytest.mark.parametrize(
    'name, family',
    [
        ('Abyssal Edge (Adept)', 'Abyssal Edge'),
        ('Fatebringer (Timelost)', 'Fatebringer'),
        ("Zaouli's Bane (Harrowed)", "Zaouli's Bane"),
        ('Fatebringer', 'Fatebringer'),
    ],
)
def test_family_drops_an_edition_suffix(conn, name, family):
    # So the special editions group with the base weapon.
    c.add_weapon_def(conn, 100, name=name)
    c.add_copy(conn, 'w1', 100, SOCKETS)
    assert weapon(conn, 'w1')['family_name'] == family


def test_slot_is_its_buckets_name_and_tier_6_is_exotic(conn):
    c.add_weapon_def(conn, 100, name='The Messenger', tier=6)
    c.add_copy(conn, 'w1', 100, SOCKETS)
    w1 = weapon(conn, 'w1')
    assert (w1['slot'], w1['slot_order'], w1['is_exotic']) == ('Kinetic Weapons', 20, 1)


def test_element_is_the_copys_else_the_weapons_default(conn):
    c.add_weapon_def(conn, 100, damage_type=1)
    c.add_copy(conn, 'void', 100, SOCKETS, damage_type=4)
    c.add_copy(conn, 'default', 100, SOCKETS)
    assert weapon(conn, 'void')['element'] == 'Void'
    assert weapon(conn, 'default')['element'] == 'Kinetic'


def test_weapon_type_icon_is_its_gunsmith_orders(conn):
    # The order is named after the type, plural; a Combat Bow's is Bows. A
    # type without an order has no icon.
    with conn:
        conn.executemany(
            "INSERT INTO DestinyInventoryItemDefinition (hash, name, itemTypeDisplayName, icon) "
            "VALUES (?, ?, 'Gunsmith Order', ?)",
            [(1, 'Auto Rifles', '/ar.png'), (2, 'Bows', '/bow.png')],
        )
    c.add_weapon_def(conn, 100)
    c.add_weapon_def(conn, 101, itemTypeDisplayName='Combat Bow')
    c.add_weapon_def(conn, 102, itemTypeDisplayName='Glaive')
    for instance_id, item_hash in (('ar', 100), ('bow', 101), ('glaive', 102)):
        c.add_copy(conn, instance_id, item_hash, SOCKETS)
    icons = {i: weapon(conn, i)['wtype_icon'] for i in ('ar', 'bow', 'glaive')}
    assert icons == {
        'ar': 'https://www.bungie.net/ar.png',
        'bow': 'https://www.bungie.net/bow.png',
        'glaive': '',
    }


def test_archetype_is_the_copys_intrinsic_else_the_starting_one(conn):
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'own', 100, [c.INTRINSIC_AGGRESSIVE, *SOCKETS[1:]])
    c.add_copy(conn, 'empty', 100, [None, *SOCKETS[1:]])
    own, empty = weapon(conn, 'own'), weapon(conn, 'empty')
    assert (own['archetype'], own['archetype_icon']) == (
        'Aggressive Frame',
        'https://www.bungie.net/img/aggressive.png',
    )
    assert empty['archetype'] == 'Adaptive Frame'


def test_rpm_and_lock_state(conn):
    # State 1 is Bungie's Locked flag (4 is Masterwork).
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'w1', 100, SOCKETS, stats={RPM: 140}, state=1 | 4)
    c.add_copy(conn, 'w2', 100, SOCKETS, state=4)
    w1, w2 = weapon(conn, 'w1'), weapon(conn, 'w2')
    assert (w1['rpm'], w1['is_locked']) == (140, 1)
    assert (w2['rpm'], w2['is_locked']) == (0, 0)


def test_source_is_where_its_collection_entry_says_it_drops(conn):
    # Bungie's "Random Perks" line, the source of 91 of the live vault's
    # copies, names no place, so it's left out.
    with conn:
        conn.executemany(
            "INSERT INTO DestinyCollectibleDefinition VALUES (?, ?)",
            [
                (1, 'Commander Zavala'),
                (2, 'Random Perks: This item cannot be reacquired from Collections.'),
            ],
        )
    c.add_weapon_def(conn, 100, collectibleHash=1)
    c.add_weapon_def(conn, 101, collectibleHash=2)
    c.add_copy(conn, 'w1', 100, SOCKETS)
    c.add_copy(conn, 'w2', 101, SOCKETS)
    assert (weapon(conn, 'w1')['source'], weapon(conn, 'w2')['source']) == ('Commander Zavala', '')


def test_ammo_is_the_weapons_ammo_type_with_its_badge(conn):
    # Luna's Howl is primary, Ergo Sum special (not heavy, though a sword).
    c.add_weapon_def(conn, 100, ammoType=1)
    c.add_weapon_def(conn, 101, ammoType=2)
    c.add_weapon_def(conn, 102)
    for instance_id, item_hash in (('primary', 100), ('special', 101), ('unknown', 102)):
        c.add_copy(conn, instance_id, item_hash, SOCKETS)
    badges = 'https://www.bungie.net/img/destiny_content/ammo_types/'
    assert [
        (weapon(conn, i)['ammo'], weapon(conn, i)['ammo_icon'])
        for i in ('primary', 'special', 'unknown')
    ] == [
        ('primary', badges + 'primary.png'),
        ('special', badges + 'special.png'),
        ('', ''),
    ]


def test_season_takes_a_season_trait_then_annual_then_any(conn):
    c.add_weapon_def(conn, 100, traitIds='["releases.v400.annual", "releases.v710.season"]')
    c.add_weapon_def(conn, 101, traitIds='["releases.v100", "releases.v400.annual"]')
    c.add_weapon_def(conn, 102, traitIds='["item.weapon.exotic", "releases.v100"]')
    for iid, item_hash in (('season', 100), ('annual', 101), ('any', 102)):
        c.add_copy(conn, iid, item_hash, SOCKETS)
    assert season(conn, 'season') == (21, 'Season of the Deep', '2023-05-23')
    assert season(conn, 'annual') == (4, 'Forsaken', '2018-09-04')
    assert season(conn, 'any') == (1, 'Red War', '2017-09-06')


def test_a_weapon_whose_traits_name_no_known_release_has_no_season(conn):
    # In today's manifest, only BrayTech RWP Mk. II; its icon still carries
    # its watermark, the Warmind badge.
    icon = '/common/destiny2_content/icons/da5f961ef97b78293cc498978c10e178.png'
    c.add_weapon_def(conn, 100, traitIds='["item.weapon.scout_rifle"]', iconWatermark=icon)
    c.add_copy(conn, 'w1', 100, SOCKETS)
    assert season(conn, 'w1') == (0, '', '')
    assert weapon(conn, 'w1')['watermark'] == f'https://www.bungie.net{icon}'
