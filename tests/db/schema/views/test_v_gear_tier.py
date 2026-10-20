# Tests for v_gear_tier (db/schema/views/v_gear_tier.sql): the pip image for
# each gear tier, from the manifest's item constants.
import json


def test_each_gear_tier_gets_its_pip_image(conn):
    # The first path is tier 1's; an empty path gives no row.
    with conn:
        conn.execute(
            "INSERT INTO DestinyInventoryItemConstantsDefinition (hash, gearTierOverlayImagePaths) "
            "VALUES (1, ?)",
            (json.dumps(['/t1.png', '', '/t3.png']),),
        )
    rows = conn.execute("SELECT tier, url FROM v_gear_tier ORDER BY tier").fetchall()
    assert [tuple(r) for r in rows] == [
        (1, 'https://www.bungie.net/t1.png'),
        (3, 'https://www.bungie.net/t3.png'),
    ]
