# Tests for v_popularity_pair (db/schema/views/v_popularity_pair.sql): each
# scored trait pair split into its traits, with its rank and its share against
# the top pair.
from tests import conftest as c


def test_pairs_split_into_their_traits_with_their_share_against_the_top(conn):
    # A weapon with one trait socket scores single traits there, which aren't
    # pairs.
    c.add_popularity(
        conn,
        'Gun',
        [100],
        columns=[
            c.popularity_column(
                'traits',
                [
                    ('Rampage + Outlaw', 0.5),
                    ('Rampage + Firefly', 0.3),
                    ('Kill Clip + Outlaw', 0.2),
                ],
            )
        ],
    )
    c.add_popularity(
        conn, 'Sidearm', [200], columns=[c.popularity_column('traits', [('Rampage', 1.0)])]
    )
    rows = conn.execute(
        "SELECT name, trait1, trait2, rank, share, round(rel, 4) FROM v_popularity_pair "
        "ORDER BY rank"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('Gun', 'Rampage', 'Outlaw', 1, 0.5, 1.0),
        ('Gun', 'Rampage', 'Firefly', 2, 0.3, 0.6),
        ('Gun', 'Kill Clip', 'Outlaw', 3, 0.2, 0.4),
    ]


def test_pairs_the_file_rounds_to_nothing_have_a_rel_of_0(conn):
    # Every pair rounds to 0, so there is no top share to compare against.
    c.add_popularity(
        conn,
        'Gun',
        [100],
        columns=[
            c.popularity_column('traits', [('Rampage + Outlaw', 0.0), ('Kill Clip + Outlaw', 0.0)])
        ],
    )
    rows = conn.execute("SELECT rel FROM v_popularity_pair").fetchall()
    assert [tuple(r) for r in rows] == [(0,), (0,)]
