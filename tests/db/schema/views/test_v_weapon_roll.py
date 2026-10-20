# Tests for v_weapon_roll (db/schema/views/v_weapon_roll.sql): the perks each
# weapon copy can equip in each perk socket, read from rows written the way
# the profile extract writes them.
from tests import conftest as c

SOCKETS = c.WEAPON_SOCKETS


def roll(conn, instance_id):
    # [(socket index, kind, [perk names in order])] from v_weapon_roll.
    sockets = {}
    for r in conn.execute(
        "SELECT socket_idx, kind, perk FROM v_weapon_roll WHERE instance_id = ? "
        "ORDER BY socket_idx, position",
        (instance_id,),
    ):
        sockets.setdefault((r['socket_idx'], r['kind']), []).append(r['perk'])
    return [(idx, kind, perks) for (idx, kind), perks in sockets.items()]


def test_roll_lists_each_perk_socket_and_its_options(conn):
    c.add_weapon_def(conn, 100)
    reusable = {
        1: [c.BARREL_PERK_X, c.BARREL_PERK_Y],
        2: [c.MAG_PERK_P, c.MAG_PERK_Q],
        3: [c.TRAIT_PERK_A, c.TRAIT_PERK_B],
        4: [c.TRAIT_PERK_C, c.TRAIT_PERK_D],
    }
    c.add_copy(conn, 'w1', 100, SOCKETS, reusable)
    # The intrinsic offers no choice and the masterwork isn't a perk.
    assert roll(conn, 'w1') == [
        (1, 'barrel', ['Hammer-Forged Rifling', 'Fluted Barrel']),
        (2, 'magazine', ['Appended Mag', 'Tactical Mag']),
        (3, 'trait', ['Rampage', 'Kill Clip']),
        (4, 'trait', ['Outlaw', 'Subsistence']),
        (5, 'origin', ["Vanguard's Vindication"]),
    ]


def test_switchable_intrinsic_is_a_perk_socket(conn):
    # Ergo Sum: each copy can switch its intrinsic.
    c.add_weapon_def(conn, 100)
    reusable = {0: [c.INTRINSIC_ADAPTIVE, c.INTRINSIC_AGGRESSIVE]}
    c.add_copy(conn, 'w1', 100, SOCKETS[:1], reusable)
    assert roll(conn, 'w1') == [(0, 'intrinsic', ['Adaptive Frame', 'Aggressive Frame'])]


def test_perks_follow_the_games_order(conn):
    # The plugged perk keeps its place in the game's list; one the list
    # leaves out comes first.
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'listed', 100, SOCKETS[:4], {3: [c.TRAIT_PERK_B, c.TRAIT_PERK_A]})
    c.add_copy(conn, 'unlisted', 100, SOCKETS[:4], {3: [c.TRAIT_PERK_B, c.TRAIT_PERK_C]})
    assert roll(conn, 'listed')[-1] == (3, 'trait', ['Kill Clip', 'Rampage'])
    assert roll(conn, 'unlisted')[-1] == (3, 'trait', ['Rampage', 'Kill Clip', 'Outlaw'])


def test_options_of_another_category_are_left_out(conn):
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'w1', 100, SOCKETS[:4], {3: [c.TRAIT_PERK_A, c.BARREL_PERK_X]})
    assert roll(conn, 'w1')[-1] == (3, 'trait', ['Rampage'])


def test_empty_socket_has_no_perks(conn):
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'w1', 100, [None, None, None, c.TRAIT_PERK_A])
    assert roll(conn, 'w1') == [(3, 'trait', ['Rampage'])]
