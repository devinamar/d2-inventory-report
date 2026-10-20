# Armor set grades, best first: each grade's code, label and slot_cap, how
# many copies of each slot a set of that grade keeps, per class. Their only
# source is the armor_grade view (db/schema/app/armor_grade.sql); they're read
# from its file once, so the preference editor needs no connection.
import dataclasses
import sqlite3

from db import migrate


@dataclasses.dataclass(frozen=True)
class Grade:
    code: str
    label: str
    slot_cap: int  # copies of each slot the set keeps, per class


def read_grades() -> tuple:
    # The grades S to F from armor_grade.sql, run in an in-memory database;
    # Unclassified (code '') is left out.
    conn = sqlite3.connect(':memory:')
    conn.executescript((migrate.SCHEMA_DIR / 'app' / 'armor_grade.sql').read_text(encoding='utf-8'))
    rows = conn.execute(
        "SELECT grade, label, slot_cap FROM armor_grade WHERE grade != '' ORDER BY position"
    ).fetchall()
    conn.close()
    return tuple(Grade(*r) for r in rows)


GRADES = read_grades()
GRADE_ORDER = tuple(g.code for g in GRADES)  # best first
GRADE_LABELS = {g.code: g.label for g in GRADES}


def cap_summary() -> str:
    # Caps as prose, grouping grades that share a cap: 'S 4, A/B 2, C/D/E/F 1'.
    groups = []
    for g in GRADES:
        if groups and groups[-1][1] == g.slot_cap:
            groups[-1][0].append(g.code)
        else:
            groups.append(([g.code], g.slot_cap))
    return ', '.join(f"{'/'.join(codes)} {cap}" for codes, cap in groups)
