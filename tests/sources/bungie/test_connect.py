# Tests for connect() (sources/bungie/connect.py): the Session it hands the
# extract, after logging in, downloading the manifest and finding the player,
# each swapped for a stand-in.
import pytest

from sources.bungie import connect, oauth

# The player search's answer: the account found.
CARD = {
    'membershipType': 3,
    'membershipId': '4611686018467000001',
    'bungieGlobalDisplayName': 'Guardian',
}


@pytest.fixture(autouse=True)
def downloads(monkeypatch, tmp_path):
    # The Bungie app's credentials in the environment, and the manifest
    # download swapped for a stand-in; returns the API clients it was given.
    monkeypatch.setenv('BUNGIE_CLIENT_ID', 'client-id')
    monkeypatch.setenv('BUNGIE_CLIENT_SECRET', 'secret')
    monkeypatch.setenv('BUNGIE_API_KEY', 'api-key')
    monkeypatch.delenv('BUNGIE_REDIRECT_URI', raising=False)
    clients = []

    def download_manifest(api):
        clients.append(api)
        return tmp_path / 'world_sql_content_new.sqlite', 'world_sql_content_new'

    monkeypatch.setattr(connect, 'download_manifest', download_manifest)
    return clients


def log_in(handler):
    # authenticate() for a login that works.
    handler.access_token, handler.membership_id = 'tok', '7'
    return True


def players(monkeypatch, answer):
    # Swap the player search for one answering answer: an account's card, or
    # an exception to raise. Returns the names searched for.
    searched = []

    def search_player(name):
        searched.append(name)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(connect.BungieAPI, 'search_player', staticmethod(search_player))
    return searched


def test_the_session_holds_the_player_and_the_login_token(monkeypatch, downloads, tmp_path):
    monkeypatch.setattr(oauth.OAuthHandler, 'authenticate', log_in)
    searched = players(monkeypatch, CARD)
    session = connect.connect('Guardian#0042')
    assert (session.has_oauth, session.api.session.headers['Authorization']) == (True, 'Bearer tok')
    assert (searched, downloads) == (['Guardian#0042'], [session.api])
    assert (session.manifest_path, session.manifest_version) == (
        tmp_path / 'world_sql_content_new.sqlite',
        'world_sql_content_new',
    )
    assert (session.membership_type, session.membership_id, session.display_name) == (
        3,
        '4611686018467000001',
        'Guardian',
    )


def test_the_display_name_falls_back_to_the_name_given(monkeypatch):
    card = {key: value for key, value in CARD.items() if key != 'bungieGlobalDisplayName'}
    monkeypatch.setattr(oauth.OAuthHandler, 'authenticate', log_in)
    players(monkeypatch, card)
    assert connect.connect('Guardian#0042').display_name == 'Guardian#0042'


def test_a_failed_login_carries_on_without_its_token(monkeypatch):
    # The login set a token before it failed; the run doesn't use it.
    def fail(handler):
        handler.access_token = 'half-done'
        raise RuntimeError('Bungie refused the token request')

    monkeypatch.setattr(oauth.OAuthHandler, 'authenticate', fail)
    players(monkeypatch, CARD)
    session = connect.connect('Guardian#0042')
    assert (session.has_oauth, 'Authorization' in session.api.session.headers) == (False, False)


def test_an_unknown_player_ends_the_run(monkeypatch):
    monkeypatch.setattr(oauth.OAuthHandler, 'authenticate', log_in)
    players(monkeypatch, Exception('Player not found: Nobody#0001'))
    with pytest.raises(SystemExit) as end:
        connect.connect('Nobody#0001')
    assert end.value.code == 1
