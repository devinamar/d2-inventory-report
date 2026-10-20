# Tests for the Bungie login's token logic (sources/bungie/oauth.py): the token
# file, the token request, the browser login, and the choice between a saved,
# refreshed or new login. Bungie's token endpoint and the callback server are
# stand-ins, so no test reaches Bungie or opens a browser.
import time
import urllib.parse

import pytest

import paths
from sources.bungie import oauth
from tests import conftest as c

REDIRECT = 'https://localhost:7777/callback'
STATE = 'state-1'


@pytest.fixture(autouse=True)
def token_file(tmp_path, monkeypatch):
    # The token file in this test's own folder, a fixed login state, and a
    # callback server that fails the test unless the test swaps in its own.
    def token_urlsafe(nbytes):
        # The real state is random, with at least 16 bytes to guess.
        assert nbytes >= 16
        return STATE

    def no_browser(login_url, redirect_uri):
        pytest.fail(f'the browser login was reached: {login_url}, back to {redirect_uri}')

    monkeypatch.setattr(paths, 'BUNGIE_TOKEN_FILE', tmp_path / 'tokens.json')
    monkeypatch.setattr(oauth.secrets, 'token_urlsafe', token_urlsafe)
    monkeypatch.setattr(oauth.callback_server, 'open_and_wait', no_browser)
    return tmp_path / 'tokens.json'


def handler():
    return oauth.OAuthHandler('client-id', 'secret', REDIRECT)


def token_endpoint(monkeypatch, *replies):
    # Swap requests.post for Bungie's token endpoint, answering replies in
    # turn; returns what it was sent.
    sent = []
    answers = iter(replies)

    def post(url, data, timeout):
        sent.append({'url': url, 'timeout': timeout, **data})
        return next(answers)

    monkeypatch.setattr(oauth.requests, 'post', post)
    return sent


def granted(access_token, refresh_token, membership_id=None):
    # Bungie's token response; a refresh's needn't name the membership id.
    tokens = {
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'refresh_token': refresh_token,
        'refresh_expires_in': 7776000,
    }
    if membership_id:
        tokens['membership_id'] = membership_id
    return c.make_response(payload=tokens)


def browser(monkeypatch, outcome):
    # Swap the callback server for one whose browser Bungie sends back with
    # outcome, the redirect's query, or that fails with outcome, an exception.
    # Returns the (login page, redirect URI) it was given each time.
    opened = []

    def open_and_wait(login_url, redirect_uri):
        opened.append((login_url, redirect_uri))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(oauth.callback_server, 'open_and_wait', open_and_wait)
    return opened


def code_grant(code):
    # What the token endpoint is sent to exchange a login code.
    return {
        'url': oauth.TOKEN_URL,
        'timeout': 30,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT,
        'client_id': 'client-id',
        'client_secret': 'secret',
    }


# Token file


def test_saved_tokens_round_trip_in_an_owner_only_file(token_file):
    oauth.save_tokens({'access_token': 'a1', 'membership_id': '7'})
    assert oauth.load_tokens() == {'access_token': 'a1', 'membership_id': '7'}
    assert token_file.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('text', [None, 'not json'], ids=['missing', 'not JSON'])
def test_an_unreadable_token_file_counts_as_no_login(token_file, text):
    if text is not None:
        token_file.write_text(text)
    assert oauth.load_tokens() == {}


# Token request


def test_a_refused_token_request_raises_with_bungies_reply(monkeypatch):
    refusal = b'{"error":"invalid_grant","error_description":"AuthorizationCodeInvalid"}'
    token_endpoint(monkeypatch, c.make_response(400, refusal))
    with pytest.raises(RuntimeError, match='AuthorizationCodeInvalid'):
        handler().request_tokens(grant_type='authorization_code', code='c1')


# Browser login


def test_the_login_page_asks_bungie_for_a_code_for_this_app(monkeypatch):
    opened = browser(monkeypatch, {'code': 'c1', 'state': STATE})
    token_endpoint(monkeypatch, granted('a1', 'r1', '7'))
    handler().browser_login()
    ((login_url, redirect_uri),) = opened
    assert redirect_uri == REDIRECT  # the server waits where Bungie sends the browser
    page = urllib.parse.urlsplit(login_url)
    assert f'{page.scheme}://{page.netloc}{page.path}' == oauth.AUTH_URL
    assert dict(urllib.parse.parse_qsl(page.query)) == {
        'client_id': 'client-id',
        'response_type': 'code',
        'state': STATE,
        'redirect_uri': REDIRECT,
    }


def test_a_redirect_with_a_foreign_state_is_refused(monkeypatch):
    # A page forging the redirect can't know this login's state; its code is
    # never exchanged.
    browser(monkeypatch, {'code': 'c1', 'state': 'forged'})
    sent = token_endpoint(monkeypatch)
    with pytest.raises(RuntimeError, match='state mismatch'):
        handler().browser_login()
    assert sent == []


def test_a_redirect_without_a_code_is_refused_with_bungies_reason(monkeypatch):
    # OAuth's error when the player declines the login.
    browser(monkeypatch, {'error': 'access_denied', 'state': STATE})
    token_endpoint(monkeypatch)
    with pytest.raises(RuntimeError, match='access_denied'):
        handler().browser_login()


@pytest.mark.parametrize(
    'server', [OSError('Address already in use'), {}], ids=['fails to start', 'times out']
)
def test_without_the_callback_server_the_address_is_pasted(monkeypatch, server):
    asked = []

    def paste(prompt):
        asked.append(prompt)
        return f'{REDIRECT}?code=c2&state={STATE}'

    browser(monkeypatch, server)
    monkeypatch.setattr('builtins.input', paste)
    sent = token_endpoint(monkeypatch, granted('a2', 'r2', '7'))
    assert handler().browser_login()['access_token'] == 'a2'
    assert (asked, sent) == (['Paste it here: '], [code_grant('c2')])


# Choosing a login


def test_a_saved_token_is_used_without_asking_bungie(monkeypatch):
    expires_at = time.time() + 3600
    oauth.save_tokens({'access_token': 'a1', 'membership_id': '7', 'expires_at': expires_at})
    monkeypatch.delattr(oauth.requests, 'post')  # any token request would fail the test
    h = handler()
    assert h.authenticate()
    assert (h.access_token, h.membership_id) == ('a1', '7')


@pytest.mark.parametrize('seconds_left', [None, 60], ids=['no expiry saved', 'expiring soon'])
def test_an_expired_or_expiring_token_is_refreshed(monkeypatch, seconds_left):
    # A token with less than EXPIRY_MARGIN seconds left counts as expired, and
    # so does a saved file without expires_at.
    saved = {'access_token': 'old', 'refresh_token': 'r1', 'membership_id': '7'}
    if seconds_left is not None:
        saved['expires_at'] = time.time() + seconds_left
    oauth.save_tokens(saved)
    sent = token_endpoint(monkeypatch, granted('new', 'r2'))
    h = handler()
    assert h.authenticate()
    assert sent == [
        {
            'url': oauth.TOKEN_URL,
            'timeout': 30,
            'grant_type': 'refresh_token',
            'refresh_token': 'r1',
            'client_id': 'client-id',
            'client_secret': 'secret',
        }
    ]
    assert (h.access_token, h.membership_id) == ('new', '7')  # the id kept from the saved login
    stored = oauth.load_tokens()
    assert stored['refresh_token'] == 'r2' and stored['expires_at'] > time.time() + 3000


def test_without_a_saved_login_the_browser_login_runs_and_is_saved(monkeypatch):
    browser(monkeypatch, {'code': 'c1', 'state': STATE})
    sent = token_endpoint(monkeypatch, granted('a1', 'r1', '7'))
    h = handler()
    assert h.authenticate()
    assert sent == [code_grant('c1')]
    assert (h.access_token, h.membership_id) == ('a1', '7')
    assert oauth.load_tokens()['refresh_token'] == 'r1'


def test_a_refused_refresh_falls_back_to_a_browser_login(monkeypatch):
    # A refresh token expires after 90 days, or can be revoked.
    oauth.save_tokens({'access_token': 'old', 'refresh_token': 'r0', 'membership_id': '7'})
    browser(monkeypatch, {'code': 'c1', 'state': STATE})
    refused = c.make_response(400, b'{"error":"invalid_grant"}')
    sent = token_endpoint(monkeypatch, refused, granted('a1', 'r1', '7'))
    h = handler()
    assert h.authenticate()
    assert [grant['grant_type'] for grant in sent] == ['refresh_token', 'authorization_code']
    assert (h.access_token, oauth.load_tokens()['refresh_token']) == ('a1', 'r1')
