# Tests for v_armor_reach (db/schema/views/v_armor_reach.sql): how far each
# class's kept Legendary armor takes each three-stat build, over copies
# written with add_armor and their saved scores.
from tests import conftest as c

ROLL = {'health': 30, 'melee': 25, 'grenade': 20}


def reach(conn):
    # The health, melee and grenade build's pieces: (slot, instance_id, its
    # three values, the build's three totals).
    return [
        tuple(r)
        for r in conn.execute(
            "SELECT slot, instance_id, value_1, value_2, value_3, total_1, total_2, total_3 "
            "FROM v_armor_reach WHERE stat_1 = 'health' AND stat_2 = 'melee' "
            "AND stat_3 = 'grenade' ORDER BY slot"
        )
    ]


def test_reach_takes_the_best_kept_piece_in_each_slot(conn):
    # A capped piece counts only once it's rescued.
    c.add_preference(conn, 'Test Set', 'F')
    c.add_armor(conn, 'helm', ROLL, set_name='Test Set', score=100)
    c.add_armor(conn, 'capped', dict.fromkeys(ROLL, 30), set_name='Test Set', score=90)
    arms = {'health': 20, 'melee': 20, 'grenade': 20}
    c.add_armor(conn, 'arms', arms, set_name='Test Set', slot='Gauntlets', score=100)
    assert reach(conn) == [
        ('Gauntlets', 'arms', 20, 20, 20, 50, 45, 40),
        ('Helmet', 'helm', 30, 25, 20, 50, 45, 40),
    ]
    with conn:
        conn.execute("INSERT INTO armor_rescue VALUES ('capped', 'health', 'melee', 'grenade', 50)")
    assert reach(conn)[1] == ('Helmet', 'capped', 30, 30, 30, 50, 50, 50)


def test_exotics_never_count_toward_a_builds_reach(conn):
    # The exotic helmet rolls better, but only Legendary pieces count.
    c.add_preference(conn, 'Test Set', 'F')
    c.add_armor(conn, 'helm', ROLL, set_name='Test Set', score=100)
    c.add_armor(conn, 'exotic', dict.fromkeys(ROLL, 30), exotic=True, name='Test Exotic', score=100)
    assert reach(conn) == [('Helmet', 'helm', 30, 25, 20, 30, 25, 20)]
