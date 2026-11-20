# Tests for v_weapon_definition (db/schema/views/v_weapon_definition.sql): each
# weapon definition as the report shows it before any copy.
from tests import conftest as c


def test_a_definition_has_the_breaker_its_starting_frame_gives(conn):
    # Adaptive Frame gives Shield Piercing; a weapon starting with a frame
    # that names none has no breaker.
    c.add_breaker(conn, c.INTRINSIC_ADAPTIVE, 'Shield Piercing', 'Barrier')
    c.add_weapon_def(conn, 100)
    c.add_weapon_def(conn, 200, sockets=[c.INTRINSIC_AGGRESSIVE])
    rows = conn.execute(
        "SELECT item_hash, breaker, breaker_icon FROM v_weapon_definition ORDER BY item_hash"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (100, 'Shield Piercing', 'https://www.bungie.net/img/shield_piercing.png'),
        (200, '', ''),
    ]


def test_a_definition_without_copies_has_its_family_slot_ammo_and_frame(conn):
    # The Popular page shows weapons the vault doesn't hold: their slot, ammo
    # badge, default element and starting frame come from the definition.
    c.add_weapon_def(conn, 100, name='Gun (Adept)', ammoType=2)
    row = conn.execute(
        "SELECT item_hash, name, family_name, slot, ammo, ammo_icon, element, archetype "
        "FROM v_weapon_definition"
    ).fetchone()
    assert tuple(row) == (
        100,
        'Gun (Adept)',
        'Gun',
        'Kinetic Weapons',
        'special',
        'https://www.bungie.net/img/destiny_content/ammo_types/special.png',
        'Kinetic',
        'Adaptive Frame',
    )
