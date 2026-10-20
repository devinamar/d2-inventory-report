# Client for the DIM (Destiny Item Manager) API at api.destinyitemmanager.com.
# Reads the player's DIM tags and notes. Needs a DIM API key and the
# run's Bungie OAuth token, which it trades for a DIM token.
import requests

import models

BASE_URL = "https://api.destinyitemmanager.com"


class DIMClient:
    # One requests session carrying the DIM API key and, once authenticated,
    # the DIM token.

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers["X-API-Key"] = api_key

    def authenticate(self, bungie_token: str, bungie_membership_id: str) -> bool:
        # Trade the Bungie OAuth token for a DIM token. Returns False (after
        # printing why) if DIM refuses.
        try:
            resp = self.session.post(
                f"{BASE_URL}/auth/token",
                json={"bungieAccessToken": bungie_token, "membershipId": bungie_membership_id},
                timeout=30,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"  DIM auth error: {e}")
            return False
        self.session.headers["Authorization"] = f"Bearer {resp.json()['accessToken']}"
        return True

    def get_profile(self, membership_id: str, component: str) -> dict:
        # One component (such as 'tags') of the player's DIM profile.
        resp = self.session.get(
            f"{BASE_URL}/profile",
            params={"platformMembershipId": membership_id, "components": component},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_tags(self, membership_id: str) -> dict:
        # {instance_id: DIMAnnotation} with the player's DIM tags and notes.
        return {
            str(ann["id"]): models.DIMAnnotation(tag=ann.get("tag"), notes=ann.get("notes"))
            for ann in self.get_profile(membership_id, "tags").get("tags", [])
            if ann.get("id")
        }
