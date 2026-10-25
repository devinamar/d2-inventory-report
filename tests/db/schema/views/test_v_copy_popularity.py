# Tests for v_copy_popularity (db/schema/views/v_copy_popularity.sql): each
# copy's score per side, how close its roll is to what players run, and its
# rank on its card.
from tests import conftest as c

GUN_COLUMNS = [
    c.popularity_column('barrel', [('Fluted Barrel', 0.5), ('Hammer-Forged Rifling', 0.25)]),
    c.popularity_column('magazine', [('Tactical Mag', 1.0)]),
    c.popularity_column('traits', [('Kill Clip + Outlaw', 0.8), ('Rampage + Outlaw', 0.4)]),
    c.popularity_column('trait1', [('Kill Clip', 0.8), ('Rampage', 0.2)]),
    c.popularity_column('trait2', [('Outlaw', 1.0)]),
]


def scores(conn):
    rows = conn.execute(
        "SELECT instance_id, side, round(score, 4), slots, rank FROM v_copy_popularity "
        "ORDER BY side, rank"
    ).fetchall()
    return [tuple(r) for r in rows]


def add_result(conn, instance_id, match_count):
    with conn:
        conn.execute(
            "INSERT INTO weapon_result VALUES (?, ?, 1)",
            (instance_id, match_count),
        )


def test_a_copy_scores_its_best_perk_per_slot_with_its_traits_as_one_pair(conn):
    # a: Hammer-Forged Rifling, half the top barrel's share; Appended Mag,
    # unvoted in a scored column; Rampage + Outlaw, half the top pair's. b can
    # switch to Kill Clip, making the top pair. The origin has no scores, so it
    # isn't a slot; on PvP nothing is scored.
    c.add_weapon_def(conn, 100, name='Gun')
    c.add_popularity(conn, 'Gun', [100], columns=GUN_COLUMNS)
    c.add_copy(conn, 'a', 100, c.WEAPON_SOCKETS)
    c.add_copy(conn, 'b', 100, c.WEAPON_SOCKETS, {3: [c.TRAIT_PERK_A, c.TRAIT_PERK_B]})
    assert scores(conn) == [
        ('b', 'pve', 0.5, 3, 1),
        ('a', 'pve', 0.3333, 3, 2),
        ('a', 'pvp', None, 0, 1),
        ('b', 'pvp', None, 0, 2),
    ]


def test_without_pair_scores_each_trait_column_is_a_slot(conn):
    # Rampage is a quarter of the top first trait, Outlaw the top second.
    c.add_weapon_def(conn, 100, name='Gun')
    c.add_popularity(conn, 'Gun', [100], columns=GUN_COLUMNS[3:])
    c.add_copy(conn, 'a', 100, c.WEAPON_SOCKETS)
    assert scores(conn)[0] == ('a', 'pve', 0.625, 2, 1)


def test_copies_tied_on_score_rank_by_wishlist_matches_gear_tier_then_id(conn):
    # No scores at all: every copy ties, so z's wishlist match puts it first,
    # then the higher gear tier, then the lower id.
    c.add_weapon_def(conn, 100, name='Gun')
    for instance_id, gear_tier, match_count in (('x', 3, 0), ('y', 5, 0), ('z', 1, 1), ('w', 3, 0)):
        c.add_copy(conn, instance_id, 100, c.WEAPON_SOCKETS, gear_tier=gear_tier)
        add_result(conn, instance_id, match_count)
    ranked = [r[0] for r in scores(conn) if r[1] == 'pve']
    assert ranked == ['z', 'y', 'w', 'x']
