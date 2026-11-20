# Tests for v_plug_breaker (db/schema/views/v_plug_breaker.sql): the champion
# breaker a plug's own perk names.
from tests import conftest as c


def test_a_frame_gives_the_breaker_its_perk_names(conn):
    # Adaptive Frame's perks: its frame perk, which names no breaker, and
    # "[Shield-Piercing] Barrier"; Aggressive Frame's "[Stagger] Unstoppable".
    # Each gives the breaker type its perk's token names, with its icon; a
    # plug with no such perk gives none.
    with conn:
        conn.execute("INSERT INTO DestinySandboxPerkDefinition (hash, name) VALUES (1, 'Frame')")
        conn.execute(
            "UPDATE DestinyInventoryItemDefinition SET perks = '[{\"perkHash\": 1}]' "
            "WHERE hash = ?",
            (c.INTRINSIC_ADAPTIVE,),
        )
    c.add_breaker(conn, c.INTRINSIC_ADAPTIVE, 'Shield Piercing', 'Barrier')
    c.add_breaker(conn, c.INTRINSIC_AGGRESSIVE, 'Stagger', 'Unstoppable')
    rows = conn.execute("SELECT * FROM v_plug_breaker ORDER BY plug_hash").fetchall()
    assert [tuple(r) for r in rows] == [
        (c.INTRINSIC_ADAPTIVE, 'Shield Piercing', 'https://www.bungie.net/img/shield_piercing.png'),
        (c.INTRINSIC_AGGRESSIVE, 'Stagger', 'https://www.bungie.net/img/stagger.png'),
    ]
