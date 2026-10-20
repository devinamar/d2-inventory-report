# Tests for the Clarity step (extract/clarity.py): dim.json is downloaded only
# when Clarity's version changes, and a failed download keeps the stored
# descriptions. The source's fetch functions are stand-ins.
import pytest
import requests

from extract import clarity, source_status

VERSION = '{"descriptions": 2.0625}'  # the version stored in the live database
NEW_VERSION = '{"descriptions": 2.0626}'
# A dim.json holding one description.
DIM_JSON = {'1001': {'descriptions': {'en': [{'linesContent': [{'text': 'Kills grant damage.'}]}]}}}


def stored(conn):
    # (the stored descriptions, the step's status and version).
    notes = dict(conn.execute('SELECT plug_hash, text FROM clarity_note').fetchall())
    row = conn.execute("SELECT status, detail FROM source_status WHERE source = 'clarity'")
    return notes, tuple(row.fetchone())


def clarity_answers(monkeypatch, version):
    # Swap Clarity's fetch functions for ones answering version and DIM_JSON;
    # returns how often dim.json was downloaded.
    downloads = []

    def fetch_descriptions():
        downloads.append(DIM_JSON)
        return DIM_JSON

    monkeypatch.setattr(clarity.source, 'fetch_version', lambda: version)
    monkeypatch.setattr(clarity.source, 'fetch_descriptions', fetch_descriptions)
    return downloads


def test_an_unchanged_version_keeps_the_notes_without_downloading(conn, monkeypatch):
    clarity.save(conn, {1001: 'Kills grant bonus damage.'})
    source_status.save(conn, 'clarity', 'fresh', VERSION)
    downloads = clarity_answers(monkeypatch, VERSION)
    clarity.extract(conn)
    assert downloads == []
    assert stored(conn) == ({1001: 'Kills grant bonus damage.'}, ('cached', VERSION))


def test_a_new_version_replaces_the_notes(conn, monkeypatch):
    clarity.save(conn, {1001: 'Kills grant bonus damage.'})
    source_status.save(conn, 'clarity', 'fresh', VERSION)
    downloads = clarity_answers(monkeypatch, NEW_VERSION)
    clarity.extract(conn)
    assert len(downloads) == 1
    assert stored(conn) == ({1001: 'Kills grant damage.'}, ('fresh', NEW_VERSION))


@pytest.mark.parametrize(
    'notes, status', [({1001: 'Kills grant bonus damage.'}, 'stale'), ({}, 'failed')]
)
def test_a_failed_download_is_stale_with_notes_stored_else_failed(conn, monkeypatch, notes, status):
    def fetch_version():
        raise requests.ConnectionError('raw.githubusercontent.com unreachable')

    clarity.save(conn, notes)
    source_status.save(conn, 'clarity', 'fresh', VERSION)
    monkeypatch.setattr(clarity.source, 'fetch_version', fetch_version)
    clarity.extract(conn)
    assert stored(conn) == (notes, (status, VERSION))
