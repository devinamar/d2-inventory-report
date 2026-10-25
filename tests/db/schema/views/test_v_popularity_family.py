# Tests for v_popularity_family (db/schema/views/v_popularity_family.sql):
# each family's effective votes per column, pooled over its scored weapons.
from tests import conftest as c


def test_votes_pool_over_both_sides_and_every_weapon_of_the_family(conn):
    c.add_popularity(
        conn,
        'Gun (Raid)',
        [100],
        family='Gun',
        columns=[c.popularity_column('barrel', [('Smallbore', 1.0)], n_eff=60.0)],
    )
    c.add_popularity(
        conn,
        'Gun (Raid)',
        [100],
        side='pvp',
        family='Gun',
        columns=[c.popularity_column('barrel', [('Smallbore', 1.0)], n_eff=15.0)],
    )
    c.add_popularity(
        conn,
        'Gun (Pantheon)',
        [200],
        family='Gun',
        columns=[
            c.popularity_column('barrel', [('Full Bore', 1.0)], n_eff=30.0),
            c.popularity_column('magazine', [('Tactical Mag', 1.0)], n_eff=30.0),
        ],
    )
    rows = conn.execute(
        "SELECT family, col, votes FROM v_popularity_family ORDER BY col"
    ).fetchall()
    assert [tuple(r) for r in rows] == [('Gun', 'barrel', 105.0), ('Gun', 'magazine', 30.0)]
