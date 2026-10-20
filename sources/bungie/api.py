# Minimal client for Bungie's Destiny 2 REST API: sends the API key (and the
# OAuth token, when there is one) with every request and raises on errors.
import requests


class BungieAPI:
    # Requests share one session, which carries the auth headers.

    BASE_URL = "https://www.bungie.net/Platform"

    def __init__(self, api_key: str, access_token: str | None = None):
        # Without access_token (the OAuth bearer token), profile data shows only
        # equipped perks.
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers['X-API-Key'] = api_key
        if access_token:
            self.session.headers['Authorization'] = f"Bearer {access_token}"

    def api_get(self, endpoint: str, params: dict | None = None) -> dict:
        # GET a Platform endpoint (e.g. "/Destiny2/Manifest/") and return the
        # 'Response' part. Raises on HTTP errors and on Bungie errors
        # (ErrorCode != 1).
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get('ErrorCode') != 1:
            raise Exception(f"API Error: {data.get('Message')}")
        return data['Response']

    def get_manifest(self) -> dict:
        # Current manifest metadata, including the database download paths.
        return self.api_get("/Destiny2/Manifest/")

    def search_player(self, bungie_name: str) -> dict:
        # The first player matching a Bungie name like 'Player#1234'. Raises if
        # the name is malformed or no player matches.
        if '#' not in bungie_name:
            raise ValueError(f"Invalid Bungie name format '{bungie_name}' — expected 'Name#1234'")
        name, code = bungie_name.rsplit('#', 1)
        try:
            code_int = int(code)
        except ValueError:
            # from None: this message replaces int()'s, so the error shows
            # once instead of as two chained tracebacks.
            raise ValueError(f"Invalid Bungie name code '{code}' — must be numeric") from None
        response = self.session.post(
            f"{self.BASE_URL}/Destiny2/SearchDestinyPlayerByBungieName/-1/",
            json={"displayName": name, "displayNameCode": code_int},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if data.get('ErrorCode') != 1 or not data['Response']:
            raise Exception(f"Player not found: {bungie_name}")
        return data['Response'][0]

    def get_profile(self, membership_type: int, membership_id: str, components: list) -> dict:
        # A player's profile with the given components (see
        # constants.PROFILE_COMPONENTS). membership_type is the platform:
        # 1 Xbox, 2 PSN, 3 Steam, and so on.
        endpoint = f"/Destiny2/{membership_type}/Profile/{membership_id}/"
        params = {"components": ",".join(str(c) for c in components)}
        return self.api_get(endpoint, params)
