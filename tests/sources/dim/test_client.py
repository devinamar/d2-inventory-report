# Tests for the DIM API client (sources/dim/client.py): trading the Bungie
# login for a DIM token, and reading the player's DIM tags and notes. Its
# session's get and post are stand-ins.
import models
from sources.dim import client
from tests import conftest as c


def answer(monkeypatch, dim, method, reply):
    # Swap dim's session.<method> for one that answers reply; returns the
    # requests it was sent.
    sent = []

    def send(url, **kwargs):
        sent.append({'url': url, **kwargs})
        return reply

    monkeypatch.setattr(dim.session, method, send)
    return sent


def test_login_trades_the_bungie_token_for_a_dim_token(monkeypatch):
    dim = client.DIMClient('dim-key')
    reply = c.make_response(payload={'accessToken': 'dim-tok', 'expiresInSeconds': 2592000})
    sent = answer(monkeypatch, dim, 'post', reply)
    assert dim.authenticate('bungie-tok', '7') is True
    assert sent == [
        {
            'url': 'https://api.destinyitemmanager.com/auth/token',
            'json': {'bungieAccessToken': 'bungie-tok', 'membershipId': '7'},
            'timeout': 30,
        }
    ]
    headers = dim.session.headers
    assert (headers['X-API-Key'], headers['Authorization']) == ('dim-key', 'Bearer dim-tok')


def test_a_refused_login_returns_false_and_sends_no_token(monkeypatch):
    dim = client.DIMClient('dim-key')
    answer(monkeypatch, dim, 'post', c.make_response(401, b'{"error":"Unauthorized"}'))
    assert dim.authenticate('bungie-tok', '7') is False
    assert 'Authorization' not in dim.session.headers


def test_tags_are_keyed_by_instance_id_as_text(monkeypatch):
    # A numeric id becomes text, an entry without an id is skipped, and a
    # missing tag or note is None.
    dim = client.DIMClient('dim-key')
    tags = [
        {'id': '6917529000000000001', 'tag': 'keep', 'notes': 'god roll'},
        {'id': 6917529000000000002, 'tag': 'junk'},
        {'tag': 'favorite'},
    ]
    sent = answer(monkeypatch, dim, 'get', c.make_response(payload={'tags': tags}))
    assert dim.fetch_tags('4611686018467000001') == {
        '6917529000000000001': models.DIMAnnotation('keep', 'god roll'),
        '6917529000000000002': models.DIMAnnotation('junk', None),
    }
    assert sent == [
        {
            'url': 'https://api.destinyitemmanager.com/profile',
            'params': {'platformMembershipId': '4611686018467000001', 'components': 'tags'},
            'timeout': 30,
        }
    ]
