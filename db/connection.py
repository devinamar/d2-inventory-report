# The local SQLite database. open_db opens it, creating its tables from the
# files in db/schema/ (or rebuilding it with db/migrate.py when they changed)
# and adding any default preference it lacks. journal_mode=DELETE (rather than
# WAL) dates from when the database lived on a network share.
import sqlite3

import paths
from db import migrate


def connect(path) -> sqlite3.Connection:
    # A connection to the database file at path, with rows readable by column
    # name and foreign keys enforced.
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode = DELETE')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def open_db(path=None) -> sqlite3.Connection:
    # Open the database at path (default paths.DB_FILE). A new one gets its
    # tables from db/schema/; one whose tables no longer match is rebuilt,
    # keeping its preferences. Either way, the default preferences it lacks are
    # added.
    if path is None:
        path = paths.DB_FILE
    conn = connect(path)
    if migrate.is_empty(conn):
        migrate.create_tables(conn)
    elif not migrate.matches_schema(conn):
        conn.close()
        migrate.rebuild(path)
        conn = connect(path)
    migrate.add_default_preferences(conn)
    migrate.add_default_wishlists(conn)
    return conn
