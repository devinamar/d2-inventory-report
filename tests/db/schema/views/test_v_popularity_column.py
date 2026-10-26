# Tests for v_popularity_column (db/schema/views/v_popularity_column.sql):
# each scored column with its label, confidence, votes and top pick, and each
# weapon's weakest column.
from tests import conftest as c


def test_columns_are_labelled_as_the_weapon_calls_them(conn):
    # A rocket sidearm's barrel is its Tube, from its top perk's plug; the
    # pairs are Trait pairs, and a single trait socket's column is Traits.
    with conn:
        conn.execute(
            "INSERT INTO DestinyInventoryItemDefinition (hash, name, plugCategoryIdentifier) "
            "VALUES (9001, 'Quick Launch', 'tubes')"
        )
    c.add_popularity(
        conn,
        'Sidearm',
        [100],
        columns=[
            c.popularity_column('barrel', [('Quick Launch', 0.6)]),
            c.popularity_column('traits', [('Rampage + Outlaw', 0.5)]),
            c.popularity_column('trait1', [('Rampage', 0.7)]),
            c.popularity_column('trait2', [('Outlaw', 0.6)]),
            c.popularity_column('origin', [("Vanguard's Vindication", 0.9)]),
        ],
    )
    c.add_popularity(
        conn, 'Bow', [200], columns=[c.popularity_column('traits', [('Rampage', 0.7)])]
    )
    rows = conn.execute(
        "SELECT name, col, label FROM v_popularity_column ORDER BY name, col_n"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('Bow', 'traits', 'Traits'),
        ('Sidearm', 'barrel', 'Tube'),
        ('Sidearm', 'traits', 'Trait pairs'),
        ('Sidearm', 'trait1', 'Trait 1'),
        ('Sidearm', 'trait2', 'Trait 2'),
        ('Sidearm', 'origin', 'Origin'),
    ]


def test_the_weakest_column_has_the_fewest_votes_and_ties_go_to_trait1(conn):
    # Gun's magazine has the fewest votes. Every column of Rifle ties, so its
    # first trait column is the weakest, and same says they tie.
    c.add_popularity(
        conn,
        'Gun',
        [100],
        columns=[
            c.popularity_column('barrel', [('Smallbore', 0.6)], n_eff=80.4),
            c.popularity_column('magazine', [('Tactical Mag', 0.4)], n_eff=25.2),
            c.popularity_column('trait1', [('Rampage', 0.7)], n_eff=80.0),
        ],
    )
    c.add_popularity(
        conn,
        'Rifle',
        [200],
        columns=[
            c.popularity_column('barrel', [('Smallbore', 0.6)]),
            c.popularity_column('traits', [('Rampage + Outlaw', 0.5)]),
            c.popularity_column('trait1', [('Rampage', 0.7)]),
        ],
    )
    rows = conn.execute(
        "SELECT name, col, confidence, votes, top, top_share, same FROM v_popularity_column "
        "WHERE weakest ORDER BY name"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('Gun', 'magazine', 'low', 25, 'Tactical Mag', 0.4, 0),
        ('Rifle', 'trait1', 'medium', 50, 'Rampage', 0.7, 1),
    ]


def test_a_thin_origin_column_isnt_the_weakest_unless_its_the_only_one(conn):
    # Few of Shotgun's copies have its origin trait, as on Belisarius-D: its
    # columns that count tie at medium, so same holds. Relic has only an
    # origin column, which is then its weakest.
    c.add_popularity(
        conn,
        'Shotgun',
        [100],
        columns=[
            c.popularity_column('barrel', [('Smallbore', 0.6)], n_eff=33.0),
            c.popularity_column('trait1', [('Rampage', 0.7)], n_eff=33.0),
            c.popularity_column('origin', [('Hakke Breach Armaments', 1.0)], n_eff=1.0),
        ],
    )
    c.add_popularity(
        conn, 'Relic', [200], columns=[c.popularity_column('origin', [('Nadir Focus', 1.0)])]
    )
    rows = conn.execute(
        "SELECT name, col, confidence, same FROM v_popularity_column WHERE weakest ORDER BY name"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('Relic', 'origin', 'medium', None),
        ('Shotgun', 'trait1', 'medium', 1),
    ]
