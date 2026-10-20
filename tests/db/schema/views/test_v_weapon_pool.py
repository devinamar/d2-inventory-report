# Tests for v_weapon_pool (db/schema/views/v_weapon_pool.sql): the perks each
# weapon definition can roll in each perk socket, from its socket's plug set.
from tests import conftest as c


def test_pool_lists_what_each_socket_can_roll(conn):
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    # Rampage is listed twice; either entry rolling makes it rollable. The
    # masterwork isn't a perk.
    with conn:
        conn.execute("INSERT INTO DestinyPlugSetDefinition VALUES (900)")
        conn.executemany(
            "INSERT INTO DestinyItemSocketEntryPlugItemRandomizedDefinition VALUES (900, ?, ?, ?)",
            [
                (0, c.TRAIT_PERK_A, 0),
                (1, c.TRAIT_PERK_B, 0),
                (2, c.MW_PLUG_FULL, 1),
                (3, c.TRAIT_PERK_A, 1),
            ],
        )
        conn.execute(
            "UPDATE DestinyItemSocketEntryDefinition SET randomizedPlugSetHash = 900 "
            "WHERE socketIndex = 1"
        )
    rows = conn.execute(
        "SELECT socket_idx, kind, perk, can_roll FROM v_weapon_pool ORDER BY perk"
    ).fetchall()
    assert [tuple(r) for r in rows] == [(1, 'trait', 'Kill Clip', 0), (1, 'trait', 'Rampage', 1)]
