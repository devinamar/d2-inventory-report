# Tests for opening the database (db/connection.py): open_db rebuilds a
# database whose tables no longer match db/schema/, and opens a matching one as
# it is.
from db import connection, migrate


def test_a_database_whose_tables_changed_is_rebuilt_on_opening(tmp_path):
    path = tmp_path / 'd2.db'
    conn = connection.open_db(path)
    conn.execute('CREATE TABLE weapon_score (instance_id TEXT PRIMARY KEY)')  # since removed
    conn.close()
    conn = connection.open_db(path)
    assert migrate.matches_schema(conn)
    conn.close()
    assert len(list(tmp_path.glob('d2.*.bak'))) == 1


def test_a_database_that_matches_the_schema_opens_as_it_is(tmp_path):
    path = tmp_path / 'd2.db'
    conn = connection.open_db(path)
    with conn:
        conn.execute(
            "INSERT INTO DestinyInventoryItemDefinition (hash, name, itemType) VALUES (7, 'Gun', 3)"
        )
    conn.close()
    conn = connection.open_db(path)
    assert [r['name'] for r in conn.execute('SELECT name FROM DestinyInventoryItemDefinition')] == [
        'Gun'
    ]
    conn.close()
    assert list(tmp_path.glob('d2.*.bak')) == []
