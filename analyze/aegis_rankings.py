# The Aegis's set-bonus rankings, which the preference editor shows beside each
# set for reference, read from the aegis_bonus table extract/aegis.py fills.
# Names are compared after normalizing (case, punctuation, a trailing " Set"),
# since manifest names drift from the sheet's spelling ('Iron Panoply Set').
import re

import models


def normalize(name: str) -> str:
    # Fold a set name for matching: lowercase, drop trailing ' Set',
    # collapse punctuation/whitespace runs to single spaces.
    n = name.lower().strip()
    n = re.sub(r'\s+set$', '', n)
    return re.sub(r'[^a-z0-9]+', ' ', n).strip()


def load_aegis_bonuses(conn) -> list:
    # [AegisBonus] in rank order.
    return [
        models.AegisBonus(
            set_name=r['set_name'],
            pieces=r['pieces'],
            bonus_name=r['bonus_name'],
            source=r['source'],
            season=r['season'],
            tags=tuple(r['tags'].splitlines()),
            trigger=r['trigger_text'],
            effect=r['effect'],
            analysis=r['analysis'],
            rank=r['rank'],
            grade=r['grade'],
        )
        for r in conn.execute("SELECT * FROM aegis_bonus ORDER BY rank")
    ]


def load(conn) -> dict:
    # {normalized set name: [AegisBonus] in rank order}: the aegis argument
    # of the lookups below.
    by_set = {}
    for b in load_aegis_bonuses(conn):
        by_set.setdefault(normalize(b.set_name), []).append(b)
    return by_set


def get_aegis_bonuses(aegis: dict, set_name: str) -> list:
    # The set's [AegisBonus] in rank order (2pc and 4pc are ranked
    # independently); [] when the set is absent from the sheet.
    if not set_name:
        return []
    return aegis.get(normalize(set_name), [])


def get_aegis_ranking(aegis: dict, set_name: str):
    # The set's best-ranked AegisBonus (its first appearance on the sheet), or
    # None when the sheet doesn't list the set (older sets without a bonus,
    # PvP-only ornament sets, or sets newer than the sheet).
    bonuses = get_aegis_bonuses(aegis, set_name)
    if bonuses:
        return bonuses[0]
    return None
