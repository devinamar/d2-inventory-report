# Tests for v_popularity_version (db/schema/views/v_popularity_version.sql):
# each scored version with the weapon it counts toward and its grid.
from tests import conftest as c


def test_each_version_belongs_to_its_scored_weapon_once(conn):
    # Both sides list the Pantheon pool's versions, yet each is one row; a
    # grid is named after its weapon's lowest version hash.
    c.add_popularity(conn, 'Gun (Pantheon)', [301, 300], family='Gun')
    c.add_popularity(conn, 'Gun (Pantheon)', [301, 300], side='pvp', family='Gun')
    c.add_popularity(conn, 'Gun (Raid)', [200], family='Gun')
    rows = conn.execute(
        "SELECT item_hash, name, family, grid_id FROM v_popularity_version ORDER BY item_hash"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (200, 'Gun (Raid)', 'Gun', 200),
        (300, 'Gun (Pantheon)', 'Gun', 300),
        (301, 'Gun (Pantheon)', 'Gun', 300),
    ]
