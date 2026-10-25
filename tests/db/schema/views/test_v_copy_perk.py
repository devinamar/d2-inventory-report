# Tests for v_copy_perk (db/schema/views/v_copy_perk.sql): each copy's perks
# per socket, with the column each is scored in.
from tests import conftest as c


def test_a_copys_trait_sockets_are_numbered_in_socket_order(conn):
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'a', 100, c.WEAPON_SOCKETS, {3: [c.TRAIT_PERK_A, c.TRAIT_PERK_B]})
    rows = conn.execute(
        "SELECT socket_idx, col, perk FROM v_copy_perk ORDER BY socket_idx, position"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (1, 'barrel', 'Hammer-Forged Rifling'),
        (2, 'magazine', 'Appended Mag'),
        (3, 'trait1', 'Rampage'),
        (3, 'trait1', 'Kill Clip'),
        (4, 'trait2', 'Outlaw'),
        (5, 'origin', "Vanguard's Vindication"),
    ]
