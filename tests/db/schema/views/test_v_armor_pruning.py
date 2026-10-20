# Tests for v_armor_pruning (db/schema/views/v_armor_pruning.sql): the armor
# pieces to dismantle, why, and the copy kept in their place, worked out from
# copies written with add_armor and their saved scores.
from tests import conftest as c

ROLL = {'health': 30, 'melee': 25, 'grenade': 20}


def pruned(conn):
    # {instance_id: (reason, keeper_id)} from v_armor_pruning.
    return {
        r['instance_id']: (r['reason'], r['keeper_id'])
        for r in conn.execute("SELECT * FROM v_armor_pruning")
    }


def test_legacy_pieces_go_on_their_own_and_lower_tiers_compete(conn):
    # Grade F keeps one copy per slot: the Tier 4 piece outscores the Tier 5
    # one, which is past the cap. The legacy piece is flagged on its own.
    c.add_preference(conn, 'Test Set', 'F')
    c.add_armor(conn, 'old', ROLL, tuning=(), gear_tier=None)
    c.add_armor(conn, 'low', ROLL, set_name='Test Set', tuning=(), gear_tier=4, score=110)
    c.add_armor(conn, 'tuned', ROLL, set_name='Test Set', score=100)
    c.add_armor(conn, 'exotic', ROLL, tuning=(), exotic=True, name='Test Exotic', score=100)
    assert pruned(conn) == {'old': ('legacy', None), 'tuned': ('cap_tier', 'low')}


def test_an_exact_duplicate_loses_to_the_older_copy(conn):
    # Same stats and tuning; a copy that tunes another stat is a roll of its own.
    c.add_preference(conn, 'Test Set', 'S')
    c.add_armor(conn, 'a1', ROLL, set_name='Test Set', score=100)
    c.add_armor(conn, 'a2', ROLL, set_name='Test Set', score=100)
    c.add_armor(conn, 'a3', ROLL, set_name='Test Set', tuning=('melee',), score=100)
    assert pruned(conn) == {'a2': ('equal_same_set', 'a1')}


def test_each_grade_keeps_its_cap(conn):
    # One copy more than the cap, scores falling: only the last goes, losing
    # to the first. A set without a grade is Unclassified.
    expected = {}
    for code, cap in conn.execute("SELECT grade, slot_cap FROM armor_grade").fetchall():
        set_name = f'Grade {code or "none"}'
        if code:
            c.add_preference(conn, set_name, code)
        for i in range(cap + 1):
            c.add_armor(
                conn, f'{set_name} {i}', {'health': 30 - i}, set_name=set_name, score=100 - i
            )
        expected[f'{set_name} {cap}'] = ('cap_tier', f'{set_name} 0')
    assert pruned(conn) == expected


def test_caps_count_per_class_and_slot(conn):
    c.add_preference(conn, 'Test Set', 'F')
    for instance_id, slot, armor_class, score in (
        ('w1', 'Helmet', 'Warlock', 90),
        ('w2', 'Helmet', 'Warlock', 80),
        ('t1', 'Helmet', 'Titan', 70),
        ('g1', 'Gauntlets', 'Warlock', 60),
    ):
        c.add_armor(
            conn,
            instance_id,
            {'health': score},
            set_name='Test Set',
            slot=slot,
            armor_class=armor_class,
            score=score,
        )
    assert pruned(conn) == {'w2': ('cap_tier', 'w1')}


def test_equal_scores_keep_the_lower_id(conn):
    c.add_preference(conn, 'Test Set', 'F')
    c.add_armor(conn, 'b', {'health': 30}, set_name='Test Set', score=100)
    c.add_armor(conn, 'a', {'melee': 30}, set_name='Test Set', score=100)
    assert pruned(conn) == {'b': ('cap_tier', 'a')}


def test_exotic_versions_compete_by_name(conn):
    # A reissue may spell the name differently; another class's copy is an
    # exotic of its own.
    c.add_armor(conn, 'old', ROLL, exotic=True, name='Test Exotic', score=100)
    c.add_armor(conn, 'new', ROLL, exotic=True, name='Test EXOTIC', score=120)
    c.add_armor(conn, 'titan', ROLL, exotic=True, name='Test Exotic', armor_class='Titan', score=90)
    assert pruned(conn) == {'old': ('exotic_dupe', 'new')}


def test_an_untiered_exotic_is_not_legacy(conn):
    # An exotic from before Armor 3.0 competes with its other copies instead,
    # and stays when it scores best.
    c.add_armor(
        conn, 'old', ROLL, exotic=True, name='Test Exotic', tuning=(), gear_tier=None, score=110
    )
    c.add_armor(conn, 'new', ROLL, exotic=True, name='Test Exotic', score=100)
    assert pruned(conn) == {'new': ('exotic_dupe', 'old')}


def test_exotic_class_items_keep_one_copy_per_perk_pair(conn):
    for instance_id, perks, score in (
        ('c1', ('Spirit A', 'Spirit B'), 100),
        ('c2', ('Spirit B', 'Spirit A'), 90),
        ('c3', ('Spirit A', 'Spirit C'), 80),
    ):
        c.add_armor(
            conn,
            instance_id,
            ROLL,
            exotic=True,
            name='Test Bond',
            slot='Class Armor',
            perks=perks,
            score=score,
        )
    assert pruned(conn) == {'c2': ('exotic_dupe', 'c1')}


def test_a_rescued_piece_is_marked(conn):
    c.add_preference(conn, 'Test Set', 'F')
    c.add_armor(conn, 'kept', {'health': 30}, set_name='Test Set', score=100)
    c.add_armor(conn, 'capped', {'melee': 30}, set_name='Test Set', score=90)
    with conn:
        conn.execute("INSERT INTO armor_rescue VALUES ('capped', 'health', 'melee', 'grenade', 99)")
    rows = conn.execute("SELECT instance_id, rescued FROM v_armor_pruning").fetchall()
    assert [tuple(r) for r in rows] == [('capped', 1)]
