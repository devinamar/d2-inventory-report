# Tests for v_weapon_pool (db/schema/views/v_weapon_pool.sql): the perks each
# weapon definition can roll in each perk socket, from its socket's plug set or
# the inline list of a socket naming none, with the column each is scored in.
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


def test_a_socket_naming_no_plug_set_rolls_its_inline_list(conn):
    # Like Mint Retrograde's origin socket, whose options are listed only
    # inline; the masterwork in the list isn't a perk.
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.ORIGIN_PERK])
    c.add_inline_plugs(conn, 100, 1, [c.ORIGIN_PERK, c.MW_PLUG_FULL])
    rows = conn.execute(
        "SELECT socket_idx, kind, col, perk, can_roll, position FROM v_weapon_pool"
    ).fetchall()
    assert [tuple(r) for r in rows] == [(1, 'origin', 'origin', "Vanguard's Vindication", 1, 0)]


def test_trait_columns_are_numbered_in_socket_order(conn):
    # Two versions place their traits at different sockets (3 and 4, then 2
    # and 3), as Drang's do; each one's first trait socket is trait1.
    for item_hash, first in ((100, 3), (101, 2)):
        c.add_weapon_def(conn, item_hash, sockets=[c.INTRINSIC_ADAPTIVE] + [None] * 4)
        c.add_plug_set(conn, item_hash, first, item_hash * 10, [(c.TRAIT_PERK_A, 1)])
        c.add_plug_set(conn, item_hash, first + 1, item_hash * 10 + 1, [(c.TRAIT_PERK_C, 1)])
    c.add_plug_set(conn, 100, 1, 2000, [(c.BARREL_PERK_X, 1)])
    rows = conn.execute(
        "SELECT item_hash, socket_idx, col, perk FROM v_weapon_pool ORDER BY item_hash, socket_idx"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (100, 1, 'barrel', 'Hammer-Forged Rifling'),
        (100, 3, 'trait1', 'Rampage'),
        (100, 4, 'trait2', 'Outlaw'),
        (101, 2, 'trait1', 'Rampage'),
        (101, 3, 'trait2', 'Outlaw'),
    ]
