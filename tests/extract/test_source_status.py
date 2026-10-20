# Tests for recording how each outside source fared (extract/source_status.py).
import datetime

from extract import source_status

VERSION = '{"descriptions": 2.0625}'


def test_a_sources_status_is_replaced_each_run(conn):
    # One row per source: its latest status, when it was checked, and its
    # detail; a source without a row has no detail.
    source_status.save(conn, 'clarity', 'fresh', VERSION)
    source_status.save(conn, 'clarity', 'cached', VERSION)
    (row,) = conn.execute('SELECT * FROM source_status').fetchall()
    assert (row['source'], row['status'], row['detail']) == ('clarity', 'cached', VERSION)
    assert datetime.datetime.fromisoformat(row['checked_at']) <= datetime.datetime.now()
    assert (source_status.detail(conn, 'clarity'), source_status.detail(conn, 'aegis')) == (
        VERSION,
        '',
    )
