# Tests for armor pruning's Python side (analyze/armor_pruning.py): each
# piece's score (tuning variants, masterwork, the preferred score) and the
# rescue search over the saved scores and v_armor_reach. The views that flag
# pieces are tested in tests/db/schema/views/.
import models
from analyze import armor_pruning
from tests import conftest as c

BASE = (30, 25, 20, 0, 0, 0)
GRENADE_FIRST = ['grenade', 'health', 'melee', 'super_stat', 'class_stat', 'weapons']


# Scoring: masterwork, tuning variants and the preferred score


def test_masterwork_adds_5_to_each_zero_stat():
    assert armor_pruning.apply_mw_to_zeros((30, 0, 20, 0, 5, 0)) == (30, 5, 20, 5, 5, 5)


def test_the_untuned_variant_comes_first():
    variants = armor_pruning.tuning_variants(BASE, ('grenade',))
    assert variants[0] == ((30, 25, 20, 5, 5, 5), '')


def test_a_legendary_raises_only_its_tuning_stat():
    # +5 Wep from each of the three stats of at least 5, after the untuned one.
    variants = armor_pruning.tuning_variants(BASE, ('weapons',))
    assert [label for _, label in variants] == [
        '',
        '+5 Wep / -5 Hlt',
        '+5 Wep / -5 Mel',
        '+5 Wep / -5 Gre',
    ]


def test_an_exotic_raises_any_stat():
    # 3 donors of at least 5, 5 targets each, plus the untuned variant.
    variants = armor_pruning.tuning_variants(BASE, models.ARMOR_STAT_NAMES)
    assert len(variants) == 16


def test_a_stat_below_5_cant_give_up_points():
    # Health and melee can donate; grenade=3 can't: 2 donors x 5 targets + 1.
    variants = armor_pruning.tuning_variants((30, 25, 3, 0, 0, 0), models.ARMOR_STAT_NAMES)
    assert len(variants) == 11


def test_without_a_tuning_socket_only_the_untuned_variant():
    assert armor_pruning.tuning_variants(BASE, ()) == [((30, 25, 20, 5, 5, 5), '')]


def test_a_tuning_swap_moves_5_points_and_masterwork_fills_the_zeros():
    # +5 Gre / -5 Hlt: health 30 -> 25, grenade 20 -> 25.
    variants = dict(
        (label, stats) for stats, label in armor_pruning.tuning_variants(BASE, ('grenade',))
    )
    assert variants['+5 Gre / -5 Hlt'] == (25, 25, 25, 5, 5, 5)


def test_a_grenade_first_piece_picks_the_grenade_tune():
    best, label = armor_pruning.best_variant_for_prefs(BASE, GRENADE_FIRST, 1, ('grenade',))
    assert best[2] == 25
    assert '+5 Gre' in label


def test_another_tuning_stat_cant_raise_the_pick():
    # A Weapons-tuned piece can't raise grenade, and every swap lowers the
    # total, so it stays untuned.
    best, label = armor_pruning.best_variant_for_prefs(BASE, GRENADE_FIRST, 1, ('weapons',))
    assert (best, label) == ((30, 25, 20, 5, 5, 5), '')


def test_without_picks_the_first_stat_is_still_raised():
    # With no picks the first stat of the priority counts: +5 Hlt from melee.
    priority = ['health', 'melee', 'grenade', 'super_stat', 'class_stat', 'weapons']
    best, _ = armor_pruning.best_variant_for_prefs(BASE, priority, 0, ('health',))
    assert best[0] == 35


def test_a_piece_without_tuning_keeps_its_spread():
    # No tuning socket: only the masterwork applies.
    best, label = armor_pruning.best_variant_for_prefs(BASE, GRENADE_FIRST, 1, ())
    assert (best, label) == ((30, 25, 20, 5, 5, 5), '')


def test_scores_weigh_the_picks_3_2_1_on_the_best_variant():
    # Health first: +5 Hlt / -5 Gre gives 35 / 25 / 15.
    armor = c.make_armor(set_name='Test Set')
    piece = c.make_armor_inst(
        armor, 'p', stats=models.ArmorStats(*BASE), tuning_stats=('health',), gear_tier=5
    )
    prefs = {'Test Set': models.ArmorPreference('health', 'melee', 'grenade')}
    score = armor_pruning.compute_armor_scores([piece], prefs)['p']
    assert (score.preferred_score, score.best_tuning) == (3 * 35 + 2 * 25 + 15, '+5 Hlt / -5 Gre')
    # Untuned it scores 3 * 30 + 2 * 25 + 20: the swap adds 10.
    assert score.tuning_gain == 10


def test_without_picks_the_score_is_the_best_variants_total():
    armor = c.make_armor(set_name='Test Set')
    piece = c.make_armor_inst(
        armor, 'p', stats=models.ArmorStats(*BASE), tuning_stats=('health',), gear_tier=5
    )
    score = armor_pruning.compute_armor_scores([piece], {})['p']
    assert (score.preferred_score, score.tuning_gain) == (90, 0)


def test_every_gear_tier_and_exotic_is_scored_but_not_legacy():
    # A Tier 3 piece has no tuning socket: it scores its masterworked stats.
    stats = models.ArmorStats(*BASE)
    pieces = [
        c.make_armor_inst(c.make_armor(), 'legacy', stats=stats),
        c.make_armor_inst(c.make_armor(name='Exo', is_exotic=True), 'exotic', stats=stats),
        c.make_armor_inst(c.make_armor(), 'tier3', stats=stats, gear_tier=3),
        c.make_armor_inst(
            c.make_armor(), 'tier5', stats=stats, tuning_stats=('health',), gear_tier=5
        ),
    ]
    scores = armor_pruning.compute_armor_scores(pieces, {})
    assert set(scores) == {'exotic', 'tier3', 'tier5'}
    assert (scores['tier3'].best_stats, scores['tier3'].best_tuning) == ((30, 25, 20, 5, 5, 5), '')


def test_an_exotic_scores_untuned():
    # Its socket can raise any stat, but tuning is left out of an exotic's score.
    exotic = c.make_armor(name='Exo', is_exotic=True)
    piece = c.make_armor_inst(
        exotic,
        'exotic',
        stats=models.ArmorStats(*BASE),
        tuning_stats=models.ARMOR_STAT_NAMES,
        gear_tier=5,
    )
    prefs = {'Exo': models.ArmorPreference('health', 'melee', 'grenade')}
    score = armor_pruning.compute_armor_scores([piece], prefs)['exotic']
    assert (score.preferred_score, score.best_tuning, score.tuning_gain) == (160, '', 0)


# Rescue: base pieces take health / melee / grenade to 95 each; capped pieces
# can lift it to 100.

SLOTS = ('Helmet', 'Gauntlets', 'Chest Armor', 'Leg Armor', 'Class Armor')
BUILD = ('health', 'melee', 'grenade')


def base_pieces(conn):
    # One kept piece per slot with 19 in each of the build's stats.
    for slot in SLOTS:
        stats = {'health': 19, 'melee': 19, 'grenade': 19}
        c.add_armor(conn, f'base {slot}', stats, set_name='Base', slot=slot, score=100)


def add_capped(conn, instance_id, set_name, slot, stats):
    # A piece its set caps: the set keeps a better-scored copy in the slot that
    # rolls none of the build's stats.
    keeper = {'super_stat': 30, 'class_stat': 30}
    c.add_armor(conn, f'{instance_id} keeper', keeper, set_name=set_name, slot=slot, score=200)
    c.add_armor(conn, instance_id, stats, set_name=set_name, slot=slot, score=10)


def test_the_better_set_wins_over_a_higher_minimum(conn):
    c.add_preference(conn, 'Better Set', 'C', rank=3)
    c.add_preference(conn, 'Worse Set', 'D', rank=1)
    base_pieces(conn)
    add_capped(conn, 'higher', 'Worse Set', 'Helmet', dict.fromkeys(BUILD, 25))  # lowest 101
    add_capped(conn, 'better', 'Better Set', 'Helmet', dict.fromkeys(BUILD, 24))  # lowest 100
    assert armor_pruning.triple_rescue(conn) == {'better': [(BUILD, 100)]}


def test_two_pieces_from_different_slots_when_one_is_not_enough(conn):
    c.add_preference(conn, 'Test Set', 'F')
    base_pieces(conn)
    add_capped(conn, 'helm', 'Test Set', 'Helmet', dict.fromkeys(BUILD, 22))
    add_capped(conn, 'arms', 'Test Set', 'Gauntlets', dict.fromkeys(BUILD, 22))
    assert armor_pruning.triple_rescue(conn) == {'helm': [(BUILD, 101)], 'arms': [(BUILD, 101)]}
