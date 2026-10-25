# Tests for v_popularity_weapon (db/schema/views/v_popularity_weapon.sql):
# each scored weapon per side, with its pool label, its Endgame bar and its
# weakest column.
import pytest

from tests import conftest as c


@pytest.mark.parametrize(
    'players, hard_copies, endgame',
    [
        (100, 50, 1),  # 50 hard copies, half of all: clears both bars
        (100, 49, 0),  # a copy short of 50
        (250, 60, 0),  # 60 hard copies, but 24% of all
    ],
)
def test_the_endgame_badge_needs_enough_hard_copies_and_share(conn, players, hard_copies, endgame):
    c.add_popularity(conn, 'Gun', [100], players=players, hard_copies=hard_copies)
    row = conn.execute("SELECT hard_copies, endgame FROM v_popularity_weapon").fetchone()
    assert tuple(row) == (hard_copies, endgame)


def test_a_split_weapon_shows_its_pool_and_its_weakest_columns_confidence(conn):
    # Gun (Pantheon) is one trait pool of Gun; Fixed is a fixed roll, with no
    # columns to grade.
    c.add_popularity(
        conn,
        'Gun (Pantheon)',
        [301, 300],
        family='Gun',
        rank=4,
        columns=[
            c.popularity_column('barrel', [('Smallbore', 0.6)], n_eff=120.0),
            c.popularity_column('trait1', [('Rampage', 0.7)], n_eff=20.0),
        ],
    )
    c.add_popularity(conn, 'Fixed', [400], rank=9)
    rows = conn.execute(
        "SELECT name, family, pool, grid_id, rank, confidence, weakest, weakest_votes, top "
        "FROM v_popularity_weapon ORDER BY rank"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('Gun (Pantheon)', 'Gun', '(Pantheon)', 300, 4, 'low', 'Trait 1', 20, 'Rampage'),
        ('Fixed', 'Fixed', '', 400, 9, None, None, None, None),
    ]
