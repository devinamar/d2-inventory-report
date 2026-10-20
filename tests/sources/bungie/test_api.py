# Tests for the Bungie API client (sources/bungie/api.py): the headers it
# sends, the Response it unwraps from Bungie's reply, and the errors it raises.
# Its session's get and post are stand-ins that answer in Bungie's envelope.
import pytest
import requests

from sources.bungie import api
from tests import conftest as c

KEY = 'api-key'


def envelope(response, code=1, status='Success', message='Ok'):
    # Bungie's reply: the Response and the status fields every endpoint adds
    # (ErrorCode 1 is Success).
    return {
        'Response': response,
        'ErrorCode': code,
        'ThrottleSeconds': 0,
        'ErrorStatus': status,
        'Message': message,
        'MessageData': {},
    }


def card(membership_id):
    # A UserInfoCard: one account the player search found.
    return {
        'membershipType': 3,
        'membershipId': membership_id,
        'displayName': 'Guardian',
        'bungieGlobalDisplayName': 'Guardian',
        'bungieGlobalDisplayNameCode': 42,
    }


def answer(monkeypatch, client, method, reply):
    # Swap the client's session.<method> for one that answers reply; returns
    # the requests it was sent.
    sent = []

    def send(url, **kwargs):
        sent.append({'url': url, **kwargs})
        return reply

    monkeypatch.setattr(client.session, method, send)
    return sent


def test_the_token_header_is_sent_only_with_a_token():
    without = api.BungieAPI(KEY).session.headers
    with_token = api.BungieAPI(KEY, access_token='tok').session.headers
    assert (without['X-API-Key'], 'Authorization' in without) == (KEY, False)
    assert (with_token['X-API-Key'], with_token['Authorization']) == (KEY, 'Bearer tok')


def test_get_profile_asks_for_every_component_in_one_request(monkeypatch):
    client = api.BungieAPI(KEY)
    profile = {'profileInventory': {'data': {'items': []}}}
    sent = answer(monkeypatch, client, 'get', c.make_response(payload=envelope(profile)))
    assert client.get_profile(3, '4611686018467000001', [102, 305, 310]) == profile
    assert sent == [
        {
            'url': 'https://www.bungie.net/Platform/Destiny2/3/Profile/4611686018467000001/',
            'params': {'components': '102,305,310'},
            'timeout': 30,
        }
    ]


def test_a_bungie_error_raises_even_with_http_200(monkeypatch):
    # Bungie answers maintenance with HTTP 200 and ErrorCode 5, SystemDisabled.
    client = api.BungieAPI(KEY)
    message = 'This system is temporarily disabled for maintenance.'
    reply = envelope({}, 5, 'SystemDisabled', message)
    answer(monkeypatch, client, 'get', c.make_response(payload=reply))
    with pytest.raises(Exception, match='disabled for maintenance'):
        client.get_manifest()


def test_an_http_error_raises_before_the_body_is_read(monkeypatch):
    # A 503's body is an HTML page, not Bungie's JSON.
    client = api.BungieAPI(KEY)
    page = c.make_response(503, b'<html>Unavailable</html>', headers={'Content-Type': 'text/html'})
    answer(monkeypatch, client, 'get', page)
    with pytest.raises(requests.HTTPError):
        client.get_manifest()


def test_search_player_sends_the_name_and_numeric_code(monkeypatch):
    # #0042 is sent as the number 42. The first account found is the player.
    client = api.BungieAPI(KEY)
    cards = [card('4611686018467000001'), card('4611686018467000002')]
    sent = answer(monkeypatch, client, 'post', c.make_response(payload=envelope(cards)))
    assert client.search_player('Guardian#0042') == cards[0]
    assert sent == [
        {
            'url': 'https://www.bungie.net/Platform/Destiny2/SearchDestinyPlayerByBungieName/-1/',
            'json': {'displayName': 'Guardian', 'displayNameCode': 42},
            'timeout': 30,
        }
    ]


@pytest.mark.parametrize('name', ['Guardian', 'Guardian#abc'])
def test_a_malformed_name_is_refused_before_any_request(monkeypatch, name):
    client = api.BungieAPI(KEY)
    sent = answer(monkeypatch, client, 'post', None)
    with pytest.raises(ValueError, match='Invalid Bungie name'):
        client.search_player(name)
    assert sent == []


def test_no_matching_player_raises(monkeypatch):
    client = api.BungieAPI(KEY)
    answer(monkeypatch, client, 'post', c.make_response(payload=envelope([])))
    with pytest.raises(Exception, match='Player not found: Guardian#0042'):
        client.search_player('Guardian#0042')
