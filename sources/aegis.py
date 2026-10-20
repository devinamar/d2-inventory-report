# The Aegis's endgame analysis spreadsheet ranks every armor set bonus, S to F;
# the app keeps the rankings for reference beside the armor preferences. Fetches
# the "Set Bonuses" tab as CSV through Google Sheets' public export and parses
# each ranked row into an AegisBonus. extract/aegis.py saves them to the db.
# Sheet: https://docs.google.com/spreadsheets/d/1JM-0SlxVDAi-C6rGVlLxa-J1WGewEeL8Qvq4htWZHhY/
# Video: https://www.youtube.com/watch?v=4yRRkyEa6Ic
import csv
import io

import requests

import models

SHEET_ID = '1JM-0SlxVDAi-C6rGVlLxa-J1WGewEeL8Qvq4htWZHhY'
SET_BONUSES_GID = 1665223292
CSV_URL = (
    f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SET_BONUSES_GID}'
)


def fetch_csv() -> str:
    # The "Set Bonuses" tab as CSV text; raises on a network/HTTP failure.
    resp = requests.get(CSV_URL, timeout=15)
    resp.raise_for_status()
    return resp.text


# Row 1 is the section banner (INFO / ANALYSIS), row 2 the column names:
# icon, #, Set (name + newline + source), Season, Bonus, Pcs, Tags,
# Trigger, Effect, Description, # (rank), Tier (S to F; the app calls it the
# grade).
HEADER_ROWS = 2
COLUMNS = 12
GRADES = frozenset('SABCDEF')


def parse_row(row: list):
    # One sheet row as an AegisBonus, or None if it isn't a ranked bonus.
    if len(row) < COLUMNS:
        return None
    cells = [cell.strip() for cell in row[:COLUMNS]]
    _, _, set_cell, season, bonus_name, pieces, tags, trigger, effect, analysis, rank, grade = cells
    set_name, _, source = set_cell.partition('\n')
    if not set_name or not pieces.isdigit() or not rank.isdigit() or grade not in GRADES:
        return None
    return models.AegisBonus(
        set_name=set_name.strip(),
        pieces=int(pieces),
        bonus_name=bonus_name,
        source=source.strip(),
        season=season,
        tags=tuple(tag.strip() for tag in tags.splitlines() if tag.strip()),
        trigger=trigger,
        effect=effect,
        analysis=analysis,
        rank=int(rank),
        grade=grade,
    )


def parse_csv(text: str) -> list:
    # [AegisBonus] in sheet order; blank or malformed rows are skipped.
    rows = list(csv.reader(io.StringIO(text)))[HEADER_ROWS:]
    return [bonus for bonus in map(parse_row, rows) if bonus is not None]
