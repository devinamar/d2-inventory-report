# d2-perk-popularity: a companion project that scores the weapon rolls players
# actually use, per weapon, for PvE and PvP, from Bungie's post-game carnage
# reports, and publishes them weekly as perk_scores.json on the public
# d2-weapon-perk-scores repo's data branch. Fetches that file;
# extract/perk_popularity.py saves it to the db.
import requests

SCORES_URL = (
    'https://raw.githubusercontent.com/devinamar/d2-weapon-perk-scores/data/perk_scores.json'
)


def fetch_scores() -> dict:
    # perk_scores.json, parsed; raises on a network/HTTP failure.
    resp = requests.get(SCORES_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()
