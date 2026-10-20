# Tests for finding exact weapon duplicates (analyze/weapon_pruning.py): copies
# of one family whose element, archetype and every perk socket match. The copy
# kept has the highest gear tier, then the best wishlist score, then the lowest
# itemInstanceId.
from analyze import weapon_pruning
from tests import conftest as c

# Intrinsic, barrel, magazine and two traits.
ROLL = [c.INTRINSIC_ADAPTIVE, c.BARREL_PERK_X, c.MAG_PERK_P, c.TRAIT_PERK_A, c.TRAIT_PERK_C]


def scored_copy(conn, instance_id, item_hash=100, roll=ROLL, score=0, gear_tier=None, element=2):
    # A copy with its weapon_result row, as scoring saves it.
    c.add_copy(conn, instance_id, item_hash, roll, damage_type=element, gear_tier=gear_tier)
    with conn:
        conn.execute("INSERT INTO weapon_result VALUES (?, ?, 1)", (instance_id, score))


def test_matching_copies_keep_the_oldest(conn):
    c.add_weapon_def(conn, 100)
    for instance_id in ('w1', 'w2', 'w3'):
        scored_copy(conn, instance_id)
    assert weapon_pruning.find_exact_duplicates(conn) == [('w2', 'w1'), ('w3', 'w1')]


def test_gear_tier_then_score_pick_the_keeper(conn):
    # Tier beats score and age; at equal tier the better score wins.
    c.add_weapon_def(conn, 100)
    scored_copy(conn, 'old', score=5)
    scored_copy(conn, 'tiered', gear_tier=3)
    scored_copy(conn, 'tiered_scored', gear_tier=3, score=2)
    assert weapon_pruning.find_exact_duplicates(conn) == [
        ('old', 'tiered_scored'),
        ('tiered', 'tiered_scored'),
    ]


def test_copies_differing_in_one_perk_are_kept(conn):
    c.add_weapon_def(conn, 100)
    scored_copy(conn, 'w1')
    scored_copy(conn, 'w2', roll=[c.INTRINSIC_ADAPTIVE, c.BARREL_PERK_Y, *ROLL[2:]])
    assert weapon_pruning.find_exact_duplicates(conn) == []


def test_element_and_archetype_must_match(conn):
    c.add_weapon_def(conn, 100)
    scored_copy(conn, 'arc')
    scored_copy(conn, 'void', element=4)
    scored_copy(conn, 'aggressive', roll=[c.INTRINSIC_AGGRESSIVE, *ROLL[1:]])
    assert weapon_pruning.find_exact_duplicates(conn) == []


def test_editions_of_one_family_are_compared(conn):
    c.add_weapon_def(conn, 100, name='Fatebringer')
    c.add_weapon_def(conn, 200, name='Fatebringer (Timelost)')
    scored_copy(conn, 'base', item_hash=100)
    scored_copy(conn, 'timelost', item_hash=200)
    assert weapon_pruning.find_exact_duplicates(conn) == [('timelost', 'base')]


def test_unscored_copies_are_left_out(conn):
    # Only copies the analysis scored (weapon_result) are compared.
    c.add_weapon_def(conn, 100)
    scored_copy(conn, 'w1')
    c.add_copy(conn, 'w2', 100, ROLL, damage_type=2)
    assert weapon_pruning.find_exact_duplicates(conn) == []
