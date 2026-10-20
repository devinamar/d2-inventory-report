# Tests for the DIM step (extract/dim.py): the player's DIM tags and notes,
# saved for the copies in the vault, skipped without a Bungie login or a DIM
# API key, and kept when DIM refuses the login. DIMClient is a stand-in.
import types

import pytest

import models
from extract import dim
from tests import conftest as c

SESSION = types.SimpleNamespace(
    has_oauth=True,
    oauth=types.SimpleNamespace(access_token='bungie-tok', membership_id='7'),
    membership_id='4611686018467000001',
)


def dim_answers(monkeypatch, login=True, tags=None):
    # Swap DIMClient for one whose login works when login is True and whose
    # profile holds tags; returns what it was sent.
    sent = []

    class Client:
        def __init__(self, api_key):
            sent.append(('key', api_key))

        def authenticate(self, bungie_token, membership_id):
            sent.append(('login', bungie_token, membership_id))
            return login

        def fetch_tags(self, membership_id):
            sent.append(('tags', membership_id))
            return tags or {}

    monkeypatch.setattr(dim, 'DIMClient', Client)
    return sent


def stored(conn):
    # (the stored DIM rows, the step's status).
    rows = [tuple(r) for r in conn.execute('SELECT * FROM item_dim ORDER BY instance_id')]
    status = conn.execute("SELECT status FROM source_status WHERE source = 'dim'").fetchone()[0]
    return rows, status


@pytest.mark.parametrize(
    'has_oauth, api_key', [(False, 'dim-key'), (True, '')], ids=['no login', 'no key']
)
def test_without_a_login_or_dim_key_the_sync_is_skipped(conn, monkeypatch, has_oauth, api_key):
    monkeypatch.setenv('DIM_API_KEY', api_key)
    sent = dim_answers(monkeypatch)
    dim.extract(conn, types.SimpleNamespace(**{**vars(SESSION), 'has_oauth': has_oauth}))
    assert (sent, stored(conn)) == ([], ([], 'skipped'))


def test_a_refused_dim_login_keeps_the_stored_tags(conn, monkeypatch):
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'w1', 100)
    dim.save(conn, {'w1': models.DIMAnnotation('keep', 'god roll')})
    monkeypatch.setenv('DIM_API_KEY', 'dim-key')
    sent = dim_answers(monkeypatch, login=False)
    dim.extract(conn, SESSION)
    assert sent == [('key', 'dim-key'), ('login', 'bungie-tok', '7')]
    assert stored(conn) == ([('w1', 'keep', 'god roll')], 'stale')


def test_tags_are_saved_only_for_copies_in_the_vault(conn, monkeypatch):
    # DIM keeps the tags of copies dismantled since; the database refuses a
    # row for a copy it doesn't hold.
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'w1', 100)
    tags = {
        'w1': models.DIMAnnotation('keep', 'god roll'),
        'dismantled': models.DIMAnnotation('junk', None),
    }
    monkeypatch.setenv('DIM_API_KEY', 'dim-key')
    sent = dim_answers(monkeypatch, tags=tags)
    dim.extract(conn, SESSION)
    assert sent[-1] == ('tags', '4611686018467000001')
    assert stored(conn) == ([('w1', 'keep', 'god roll')], 'fresh')
