# Tests for v_weapon_pool (db/schema/views/v_weapon_pool.sql): the perks each
# weapon definition can roll in each perk socket, from its socket's plug set.
from tests import conftest as c


def test_pool_lists_what_each_socket_can_roll(conn):
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    # Rampage is listed twice; either entry rolling makes it rollable. The
    # masterwork isn't a perk.
    c.add_plug_set(
        conn,
        100,
        1,
        900,
        [(c.TRAIT_PERK_A, 0), (c.TRAIT_PERK_B, 0), (c.MW_PLUG_FULL, 1), (c.TRAIT_PERK_A, 1)],
    )
    rows = conn.execute(
        "SELECT socket_idx, kind, perk, can_roll FROM v_weapon_pool ORDER BY perk"
    ).fetchall()
    assert [tuple(r) for r in rows] == [(1, 'trait', 'Kill Clip', 0), (1, 'trait', 'Rampage', 1)]


def test_a_socket_without_a_random_roll_lists_the_plugs_it_can_switch_to(conn):
    # Like A Sudden Death (Adept)'s origin socket, whose 4 origin traits come
    # from the set it can switch to; 5,828 of the live pool's 102,565 rows
    # come from such a set.
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.ORIGIN_PERK])
    c.add_plug_set(conn, 100, 1, 901, [(c.ORIGIN_PERK, 1)], key='reusablePlugSetHash')
    rows = conn.execute("SELECT socket_idx, kind, perk FROM v_weapon_pool").fetchall()
    assert [tuple(r) for r in rows] == [(1, 'origin', "Vanguard's Vindication")]
