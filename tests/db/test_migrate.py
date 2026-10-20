# Tests for db/migrate.py: rebuilding a database from db/schema/, keeping only
# the preferences, and filling in the default preferences and wishlist sources
# a database lacks.
import sqlite3
import tomllib

import pytest

import models
from analyze import armor_grades
from db import connection, migrate


def older_layout(tmp_path):
    # A database in an older layout, returning its path: armor_preference names
    # the grade and rank tier and tier_rank, lacks is_exotic and has a column
    # since removed; a table since removed is still there; the player added a
    # wishlist and a weapon definition is stored.
    path = tmp_path / 'd2.db'
    conn = connection.open_db(path)
    conn.executescript("""
        DROP TABLE armor_preference;
        CREATE TABLE armor_preference (
            name TEXT PRIMARY KEY, stat_1 TEXT, tier TEXT, tier_rank INTEGER, old_note TEXT);
        INSERT INTO armor_preference VALUES ('Bushido', 'melee', 'A', 2, 'x');
        INSERT INTO DestinyInventoryItemDefinition (hash, name, itemType) VALUES (7, 'Gun', 3);
        CREATE TABLE weapon_score (instance_id TEXT PRIMARY KEY);
        INSERT INTO wishlist_preference VALUES ('mine', 'Mine', 'https://example.com/mine.txt');
    """)
    conn.close()
    return path


# Rebuilding


def test_a_rebuild_keeps_the_preferences_under_their_new_column_names(tmp_path):
    # Renamed columns (migrate.RENAMED) keep their values; new columns take
    # their defaults. The player's own wishlist is kept too.
    path = older_layout(tmp_path)
    migrate.rebuild(path)
    conn = sqlite3.connect(path)
    assert conn.execute(
        'SELECT name, is_exotic, stat_1, stat_2, grade, rank FROM armor_preference'
    ).fetchall() == [('Bushido', 0, 'melee', None, 'A', 2)]
    assert conn.execute("SELECT label FROM wishlist_preference WHERE key = 'mine'").fetchone() == (
        'Mine',
    )
    conn.close()


def test_a_rebuild_empties_every_other_table(tmp_path):
    # The database is the schema's again, and the next run refills it.
    path = older_layout(tmp_path)
    migrate.rebuild(path)
    conn = sqlite3.connect(path)
    assert migrate.matches_schema(conn)
    assert conn.execute('SELECT COUNT(*) FROM DestinyInventoryItemDefinition').fetchone() == (0,)
    conn.close()


def test_a_rebuild_keeps_the_old_database_as_the_only_backup(tmp_path):
    path = older_layout(tmp_path)
    (tmp_path / 'd2.20260101-000000.bak').write_bytes(b'')  # an earlier backup
    migrate.rebuild(path)
    (backup,) = tmp_path.glob('d2.*.bak')
    assert backup.name != 'd2.20260101-000000.bak'
    old = sqlite3.connect(backup)  # the old database, with the column since removed
    assert old.execute('SELECT old_note FROM armor_preference').fetchone() == ('x',)
    old.close()


def test_a_rebuild_that_would_lose_preferences_is_refused(tmp_path):
    # grade is NOT NULL, so a stored NULL can't be copied. The old database
    # stays in place, unchanged, with no backup made.
    path = tmp_path / 'd2.db'
    conn = connection.open_db(path)
    conn.executescript("""
        DROP TABLE armor_preference;
        CREATE TABLE armor_preference (name TEXT PRIMARY KEY, tier TEXT);
        INSERT INTO armor_preference VALUES ('Bushido', NULL);
    """)
    conn.close()

    with pytest.raises(sqlite3.IntegrityError):
        migrate.rebuild(path)
    raw = sqlite3.connect(path)
    assert raw.execute('SELECT * FROM armor_preference').fetchall() == [('Bushido', None)]
    raw.close()
    assert [p.name for p in tmp_path.iterdir()] == ['d2.db']


# Default preferences and wishlists


def test_default_preferences_fill_only_missing_names(conn):
    # A deleted default comes back; a saved row stays as it is, whatever the
    # case of its name.
    total = conn.execute('SELECT COUNT(*) FROM armor_preference').fetchone()[0]
    with conn:
        conn.execute("DELETE FROM armor_preference WHERE name = 'Aeon Swift'")
        conn.execute(
            "UPDATE armor_preference SET name = 'bushido', stat_1 = 'melee' WHERE name = 'Bushido'"
        )
    migrate.add_default_preferences(conn)
    assert conn.execute('SELECT COUNT(*) FROM armor_preference').fetchone()[0] == total
    exotic = conn.execute("SELECT is_exotic FROM armor_preference WHERE name = 'Aeon Swift'")
    assert exotic.fetchone()[0] == 1
    bushido = conn.execute("SELECT stat_1 FROM armor_preference WHERE name LIKE 'bushido'")
    assert [r[0] for r in bushido] == ['melee']


def test_default_wishlists_fill_only_missing_keys(conn):
    # A new database has every default source, in file order. A deleted one
    # comes back; a saved row stays as it is.
    with open(migrate.DEFAULT_WISHLISTS, 'rb') as f:
        keys = list(tomllib.load(f))
    order = conn.execute('SELECT key FROM wishlist_preference ORDER BY rowid')
    assert [r[0] for r in order] == keys
    with conn:
        conn.execute('DELETE FROM wishlist_preference WHERE key = ?', (keys[0],))
        conn.execute("UPDATE wishlist_preference SET label = 'Mine' WHERE key = ?", (keys[1],))
    migrate.add_default_wishlists(conn)
    assert sorted(r[0] for r in conn.execute('SELECT key FROM wishlist_preference')) == sorted(keys)
    label = conn.execute('SELECT label FROM wishlist_preference WHERE key = ?', (keys[1],))
    assert label.fetchone()[0] == 'Mine'


def test_default_preference_files_are_valid(conn):
    # No name is in two files. Each default's stats are known and distinct; a
    # set has a grade and rank, an exotic neither.
    names = []
    for subset, _ in migrate.DEFAULT_PREFERENCES:
        with open(migrate.KEPT_DIR / f'{subset}.toml', 'rb') as f:
            names += [name.lower() for name in tomllib.load(f)]
    assert len(names) == len(set(names))

    rows = conn.execute(
        'SELECT name, is_exotic, stat_1, stat_2, stat_3, grade, rank FROM armor_preference'
    )
    for name, is_exotic, *stats, grade, rank in rows:
        picks = [s for s in stats if s]
        assert set(picks) <= set(models.ARMOR_STAT_NAMES) and len(set(picks)) == len(picks), name
        if is_exotic:
            assert (grade, rank) == ('', 0), name
        else:
            assert grade in armor_grades.GRADE_ORDER and rank >= 1, name
