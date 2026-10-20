# OAuth authentication handler for the Bungie API.
#
# Bungie's API requires OAuth for accessing reusablePlugs (component 310),
# which reveals ALL possible perks a weapon can roll — not just what's
# currently equipped. Without OAuth, we can only see equipped perks.
#
# Flow: Open browser -> User logs in -> Bungie redirects to a local HTTPS
#       callback server (callback_server.py) -> Server captures the code ->
#       Exchange the code for tokens. Falls back to pasting the redirect
#       address if the local server can't start.
#
# DEV NOTE: Ive opted for verbose comments in this section to
# assist future me in understanding oauth processes.

import json
import secrets
import time
import urllib.parse

import requests

import paths
from sources.bungie import callback_server

AUTH_URL = "https://www.bungie.net/en/OAuth/Authorize"
TOKEN_URL = "https://www.bungie.net/platform/app/oauth/token/"

# Where Bungie sends the browser after login, unless .env sets
# BUNGIE_REDIRECT_URI. It must match the redirect URL registered with the
# Bungie app; the setup wizard tells the user to register this one.
DEFAULT_REDIRECT_URI = "https://localhost:7777/callback"

# An access token lasts an hour. One with less than this many seconds left is
# refreshed up front, so it can't expire halfway through a run.
EXPIRY_MARGIN = 300


def load_tokens() -> dict:
    # The tokens saved by the last login or refresh: Bungie's token response
    # plus expires_at, the access token's expiry in epoch seconds. {} when
    # there are none or the file can't be read.
    try:
        return json.loads(paths.BUNGIE_TOKEN_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_tokens(tokens: dict) -> None:
    # Save the tokens for the next run, in a file only you can read.
    # touch(mode=0o600) creates the file with owner-only read/write before
    # any secret is in it; write_text then fills it and leaves the
    # permissions alone. Writing directly would create the file with the
    # default permissions (often world-readable 0o644) first, exposing the
    # tokens for a moment.
    paths.BUNGIE_TOKEN_FILE.touch(mode=0o600)
    paths.BUNGIE_TOKEN_FILE.write_text(json.dumps(tokens))


def paste_redirect(login_url: str) -> dict:
    # Manual fallback: the user opens the login page themselves and pastes
    # the address the browser lands on afterwards. Returns that address's
    # query parameters ({name: value}).
    print("\nOpen this page, log in, then copy the whole address from the browser's address bar:")
    print(f"\n   {login_url}\n")
    address = input("Paste it here: ").strip()
    return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(address).query))


class OAuthHandler:
    # One Bungie login: gets an access token (saved, refreshed or from a new
    # browser login) and holds it with the player's Bungie.net membership id.

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.membership_id = None

    def request_tokens(self, **grant) -> dict:
        # POST a grant to Bungie's token endpoint (a login code to exchange,
        # or a refresh token) along with this app's id and secret, and return
        # Bungie's response with expires_at added. Bungie answers with an
        # access token (about an hour), a refresh token (90 days) and the
        # membership id. Raises RuntimeError when Bungie refuses the grant.
        response = requests.post(
            TOKEN_URL,
            data={**grant, 'client_id': self.client_id, 'client_secret': self.client_secret},
            timeout=30,
        )
        if not response.ok:
            raise RuntimeError(f"Bungie refused the token request: {response.text}")
        tokens = response.json()
        tokens['expires_at'] = time.time() + tokens['expires_in']
        return tokens

    def refresh(self, saved: dict) -> dict:
        # New tokens for the saved refresh token, so no browser is needed.
        # {} when there's no refresh token or Bungie refuses it (expired after
        # 90 days, or revoked).
        if not saved.get('refresh_token'):
            return {}
        print("Token expired, refreshing...")
        try:
            tokens = self.request_tokens(
                grant_type='refresh_token', refresh_token=saved['refresh_token']
            )
        except RuntimeError as e:
            print(f"  Refresh refused ({e}); logging in again.")
            return {}
        print("Token refreshed.")
        return tokens

    def browser_login(self) -> dict:
        # A new login: send the user to Bungie's login page, catch the code
        # Bungie sends back, and exchange it for tokens. state is a random
        # value Bungie hands back unchanged; a redirect without it didn't
        # come from this login (e.g. a page forging one), so it's refused.
        state = secrets.token_urlsafe(16)
        query = {
            'client_id': self.client_id,
            'response_type': 'code',
            'state': state,
            'redirect_uri': self.redirect_uri,
        }
        login_url = f"{AUTH_URL}?{urllib.parse.urlencode(query)}"

        print("\nBungie login required. Opening the login page in your browser...")
        print("(First time: the browser warns about a self-signed certificate for localhost.")
        print(" Choose Advanced -> Proceed; the login is then picked up automatically.)\n")
        try:
            params = callback_server.open_and_wait(login_url, self.redirect_uri)
        except OSError as e:
            print(f"Couldn't start the local callback server ({e}).")
            params = {}
        if not params:
            params = paste_redirect(login_url)

        if params.get('state') != state:
            raise RuntimeError("the redirect doesn't belong to this login (state mismatch)")
        if 'code' not in params:
            raise RuntimeError(f"Bungie sent no login code ({params.get('error', 'no reason')})")

        print("\nExchanging code for tokens...")
        tokens = self.request_tokens(
            grant_type='authorization_code', code=params['code'], redirect_uri=self.redirect_uri
        )
        print("Authentication successful! Tokens saved for future use.")
        return tokens

    def authenticate(self) -> bool:
        # Set the access token: the saved one while it has more than
        # EXPIRY_MARGIN seconds left, else a refreshed one, else one from a
        # new browser login. Saves any new tokens and returns True; raises
        # when the login fails. A saved file without expires_at counts as
        # expired.
        saved = load_tokens()
        if time.time() < saved.get('expires_at', 0) - EXPIRY_MARGIN:
            print("Using saved authentication.")
            tokens = saved
        else:
            # Merged over the saved tokens, because a refresh response
            # needn't repeat the membership id.
            # ** unpacks the dicts to key:value pairs.
            # unpacking both will merge left overwritten by right
            tokens = {**saved, **(self.refresh(saved) or self.browser_login())}
            save_tokens(tokens)
        self.access_token = tokens['access_token']
        self.membership_id = tokens['membership_id']
        return True
