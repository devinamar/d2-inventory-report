# Clarity: community-written perk descriptions (DIM shows them as "Community
# Insight"), from github.com/Database-Clarity/Live-Clarity-Database.
# Fetches Clarity's version and dim.json, and parses dim.json into
# {perk_hash: text}; extract/clarity.py decides when to download and saves the
# result to the db.
import json

import requests

CLARITY_RAW_BASE = "https://raw.githubusercontent.com/Database-Clarity/Live-Clarity-Database/live"
CLARITY_VERSIONS_URL = f"{CLARITY_RAW_BASE}/versions.json"
CLARITY_DIM_JSON_URL = f"{CLARITY_RAW_BASE}/descriptions/dim.json"


def fetch_version() -> str:
    # Clarity's published version (versions.json) as compact JSON text, e.g.
    # '{"descriptions": 2.0625}'.
    resp = requests.get(CLARITY_VERSIONS_URL, timeout=10)
    resp.raise_for_status()
    return json.dumps(resp.json(), sort_keys=True)


def fetch_descriptions() -> dict:
    # dim.json: {perk hash: entry} for every perk Clarity describes.
    resp = requests.get(CLARITY_DIM_JSON_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


# Clarity's icon segments that stand for an inline token of Bungie's text:
# elements and champion types. Its other icons (ammo types, classes, the
# enhanced arrow) are left out.
ICON_TOKENS = {
    'kinetic': '[Kinetic]',
    'arc': '[Arc]',
    'solar': '[Solar]',
    'void': '[Void]',
    'stasis': '[Stasis]',
    'strand': '[Strand]',
    'barrier': '[Shield-Piercing]',
    'overload': '[Disruption]',
    'unstoppable': '[Stagger]',
}


def segment_text(segment: dict) -> str:
    # A line segment's text, or for an icon segment the token Bungie's text
    # uses for that icon; '' for any other icon.
    if segment.get("text"):
        return segment["text"]
    for name in segment.get("classNames") or []:
        if name in ICON_TOKENS:
            return ICON_TOKENS[name]
    return ''


def parse_description(entry: dict) -> str:
    # One dim.json entry's English description: each line's segments joined as
    # written (they carry their own spaces), the lines joined by newlines.
    lines = []
    for block in entry.get("descriptions", {}).get("en", []):
        line = ''.join(segment_text(s) for s in block.get("linesContent", [])).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def parse_clarity_json(raw: dict) -> dict:
    # {perk_hash: description} for every entry that has English text.
    lookup = {}
    for hash_str, entry in raw.items():
        try:
            perk_hash = int(hash_str)
        except (ValueError, TypeError):
            continue
        desc = parse_description(entry)
        if desc:
            lookup[perk_hash] = desc

    print(f"  Clarity: {len(lookup)} perk descriptions loaded.")
    return lookup
