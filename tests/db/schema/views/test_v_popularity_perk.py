# Tests for v_popularity_perk (db/schema/views/v_popularity_perk.sql): each
# scored perk outside the trait pairs, with its rank and its share against its
# column's top.
from tests import conftest as c


def test_perks_rank_by_share_against_their_columns_top(conn):
    # The pairs (traits) aren't perks of a column; col_n keeps the published
    # order, which is socket order.
    c.add_popularity(
        conn,
        'Gun',
        [100],
        columns=[
            c.popularity_column('barrel', [('Smallbore', 0.5), ('Full Bore', 0.25)]),
            c.popularity_column('traits', [('Rampage + Outlaw', 0.6)]),
            c.popularity_column('trait1', [('Rampage', 0.8), ('Kill Clip', 0.2)]),
        ],
    )
    rows = conn.execute(
        "SELECT col, col_n, perk, share, rank, round(rel, 4) FROM v_popularity_perk "
        "ORDER BY col_n, rank"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('barrel', 0, 'Smallbore', 0.5, 1, 1.0),
        ('barrel', 0, 'Full Bore', 0.25, 2, 0.5),
        ('trait1', 2, 'Rampage', 0.8, 1, 1.0),
        ('trait1', 2, 'Kill Clip', 0.2, 2, 0.25),
    ]
