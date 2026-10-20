# Tests for storing The Aegis's rankings (extract/aegis.py) and keeping the
# last good copy when a download fails.
import pytest
import requests

import models
from analyze import aegis_rankings
from extract import aegis

BONUSES = [
    models.AegisBonus(
        'Ferropotent', 2, 'Rapid Repair', tags=('survivability',), rank=26, grade='B'
    ),
    models.AegisBonus('Ferropotent', 4, 'Built From Scratch', trigger='a\nb', rank=61, grade='C'),
    models.AegisBonus('Iron Panoply', 4, 'Panoply', source='Iron Banner', rank=19, grade='B'),
]


def test_bonuses_round_trip(conn):
    aegis.save(conn, BONUSES)

    assert aegis_rankings.load_aegis_bonuses(conn) == sorted(BONUSES, key=lambda b: b.rank)


def test_save_replaces_the_previous_copy(conn):
    aegis.save(conn, BONUSES)
    aegis.save(conn, BONUSES[2:])

    assert [b.set_name for b in aegis_rankings.load_aegis_bonuses(conn)] == ['Iron Panoply']


# The download: a failed or empty one keeps the stored rankings.

# The sheet's banner and column names with no ranked row under them.
EMPTY_SHEET = (
    'INFO,,,,,,,,,ANALYSIS,,\r\n'
    '\U0001f5bc️,#,Set,Season,Bonus,Pcs,Tags,Trigger,Effect,Description,#,Tier\r\n'
)


def stored(conn):
    # (rankings stored, the step's status).
    count = conn.execute('SELECT COUNT(*) FROM aegis_bonus').fetchone()[0]
    status = conn.execute("SELECT status FROM source_status WHERE source = 'aegis'").fetchone()[0]
    return count, status


def download_fails():
    raise requests.HTTPError('503 Server Error: Service Unavailable')


def sheet_is_empty():
    return EMPTY_SHEET


@pytest.mark.parametrize('download', [download_fails, sheet_is_empty], ids=['fails', 'empty'])
def test_a_failed_or_empty_download_keeps_the_stored_rankings(conn, monkeypatch, download):
    aegis.save(conn, BONUSES)
    monkeypatch.setattr(aegis.source, 'fetch_csv', download)
    aegis.extract(conn)
    assert stored(conn) == (3, 'stale')


def test_a_failed_download_with_nothing_stored_is_failed(conn, monkeypatch):
    monkeypatch.setattr(aegis.source, 'fetch_csv', download_fails)
    aegis.extract(conn)
    assert stored(conn) == (0, 'failed')
