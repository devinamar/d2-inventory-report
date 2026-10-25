# Tests for v_popularity_pair (db/schema/views/v_popularity_pair.sql): each
# scored trait pair split into its traits, with its rank, its share against
# the top pair, and each trait's partners.
from tests import conftest as c


def test_pairs_split_into_their_traits_with_each_traits_partners(conn):
    # Rampage runs with Outlaw on 0.5 of 0.8 of its pairs, its first partner;
    # Outlaw runs with Rampage on 0.5 of 0.7 of its own. A weapon with one
    # trait socket scores single traits there, which aren't pairs.
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
        "SELECT name, trait1, trait2, rank, round(rel, 4), round(trait1_cond, 4), "
        "round(trait2_cond, 4), trait1_n, trait2_n FROM v_popularity_pair ORDER BY rank"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('Gun', 'Rampage', 'Outlaw', 1, 1.0, 0.625, 0.7143, 1, 1),
        ('Gun', 'Rampage', 'Firefly', 2, 0.6, 0.375, 1.0, 2, 1),
        ('Gun', 'Kill Clip', 'Outlaw', 3, 0.4, 1.0, 0.2857, 1, 2),
    ]


def test_a_pair_the_file_rounds_to_nothing_has_ratios_of_0(conn):
    # Its first trait runs only with it, so that trait's shares add up to 0.
    c.add_popularity(
        conn,
        'Gun',
        [100],
        columns=[
            c.popularity_column('traits', [('Rampage + Outlaw', 1.0), ('Kill Clip + Outlaw', 0.0)])
        ],
    )
    row = conn.execute(
        "SELECT rel, trait1_cond, trait2_cond FROM v_popularity_pair WHERE trait1 = 'Kill Clip'"
    ).fetchone()
    assert tuple(row) == (0.0, 0, 0.0)
