# Tests for v_weapon_definition (db/schema/views/v_weapon_definition.sql): each
# weapon definition as the report shows it before any copy.
from tests import conftest as c


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
