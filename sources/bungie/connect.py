# Logs in to Bungie (OAuth), downloads the manifest, and looks up the
# player; returns everything the extract phase needs as a Session. The Bungie
# app's credentials come from the BUNGIE_* environment variables, which main
# loads from .env.
import dataclasses
import os
import pathlib
import sys

from sources.bungie import oauth as bungie_oauth
from sources.bungie.api import BungieAPI
from sources.bungie.manifest import download_manifest


@dataclasses.dataclass
class Session:
    # An authenticated API client plus the player being reported on. The
    # manifest stays on disk; extract reads it from manifest_path.
    oauth: bungie_oauth.OAuthHandler
    has_oauth: bool
    api: BungieAPI
    manifest_path: pathlib.Path
    manifest_version: str
    membership_type: int
    membership_id: str
    display_name: str


def connect(player_name: str) -> Session:
    # Log in, download the manifest, and find the player (exits if not
    # found). If OAuth fails the run continues, but only equipped perks are
    # visible.
    print("Authenticating...")
    oauth = bungie_oauth.OAuthHandler(
        os.environ['BUNGIE_CLIENT_ID'],
        os.environ['BUNGIE_CLIENT_SECRET'],
        os.environ.get('BUNGIE_REDIRECT_URI', bungie_oauth.DEFAULT_REDIRECT_URI),
    )
    try:
        has_oauth = oauth.authenticate()
    except Exception as e:
        print(f"  OAuth failed: {e}")
        print("  Continuing without OAuth (only equipped perks will be visible)")
        has_oauth = False

    # Only a completed login's token is used: authenticate() can fail after
    # setting it.
    if has_oauth:
        access_token = oauth.access_token
    else:
        access_token = None
    api = BungieAPI(os.environ['BUNGIE_API_KEY'], access_token=access_token)
    manifest_path, manifest_version = download_manifest(api)

    print(f"\nLooking up player: {player_name}")
    try:
        player = api.search_player(player_name)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    session = Session(
        oauth=oauth,
        has_oauth=has_oauth,
        api=api,
        manifest_path=manifest_path,
        manifest_version=manifest_version,
        membership_type=player['membershipType'],
        membership_id=player['membershipId'],
        display_name=player.get('bungieGlobalDisplayName', player_name),
    )
    print(
        f"  Found: {session.display_name} (type={session.membership_type}, "
        f"id={session.membership_id})"
    )
    return session
