# Armor preferences: their order, lookups and table (armor_preference). Each
# set has stat picks, an S-F grade and a rank within the grade (1 first); each
# exotic has stat picks only. Armor pruning follows them as saved, and only the
# editor changes them; db/ adds the default ones a database lacks.
import models
from analyze import armor_grades

# Position of each grade in GRADE_ORDER (S = 0); unclassified sets sort after F.
GRADE_INDEX = {g: i for i, g in enumerate(armor_grades.GRADE_ORDER)}


# Order: sets by grade, then by place in the grade; exotics after them.


def grade_members(prefs: dict, grade: str, exclude: str | None = None) -> list:
    # [(name, pref)] for the sets in grade, first place first.
    members = [
        (n, p) for n, p in prefs.items() if not p.is_exotic and p.grade == grade and n != exclude
    ]
    members.sort(key=lambda kv: (kv[1].rank, kv[0].lower()))
    return members


def set_ranks(members: list) -> None:
    # Number [(name, pref)] 1..n in list order.
    for rank, (_, pref) in enumerate(members, start=1):
        pref.rank = rank


def renumber_grade(prefs: dict, grade: str) -> None:
    # Close the gaps in a grade's ranks, keeping its order.
    set_ranks(grade_members(prefs, grade))


def sorted_prefs(prefs: dict) -> dict:
    # Sets in grade order (S to F, unclassified last) and rank, then exotics,
    # each by name within ties.
    return dict(
        sorted(
            prefs.items(),
            key=lambda kv: (
                kv[1].is_exotic,
                GRADE_INDEX.get(kv[1].grade, len(GRADE_INDEX)),
                kv[1].rank,
                kv[0].lower(),
            ),
        )
    )


def load_preferences(conn) -> dict:
    # The stored preferences, {name: ArmorPreference}, in sorted_prefs order.
    return sorted_prefs(
        {
            r['name']: models.ArmorPreference(
                r['stat_1'],
                r['stat_2'],
                r['stat_3'],
                r['grade'],
                r['rank'],
                bool(r['is_exotic']),
            )
            for r in conn.execute('SELECT * FROM armor_preference')
        }
    )


# Editing: lookups and the maps the editor's screens show.


def ci_get(prefs: dict, key: str):
    # (stored_key, value) for a name, ignoring case, or (None, None). Item
    # names change capitalization between patches ('Aion Renewal' vs
    # 'AION Renewal').
    if key in prefs:
        return key, prefs[key]
    key_lower = key.lower()
    for k, v in prefs.items():
        if k.lower() == key_lower:
            return k, v
    return None, None


def build_set_bonus_map(armor_instances) -> dict:
    # {set_name: ArmorSetBonus} from the armor copies, built once so the
    # editor's screens don't rescan every copy on each redraw.
    bonus_map = {}
    for inst in armor_instances or []:
        sb = inst.armor.set_bonus
        if sb and inst.armor.set_name not in bonus_map:
            bonus_map[inst.armor.set_name] = sb
    return bonus_map


def set_bonus_text(set_name: str, bonus_map: dict | None = None) -> tuple:
    # (two_pc_text, four_pc_text) for a set, each on one line; '' when unknown.
    sb = (bonus_map or {}).get(set_name)
    if sb:
        return (' '.join(sb.two_piece_bonus.split()), ' '.join(sb.four_piece_bonus.split()))
    return ('', '')


def build_exotic_effect_map(armor_instances) -> dict:
    # {exotic name: ExoticEffect} from the armor copies.
    effect_map = {}
    for inst in armor_instances or []:
        armor = inst.armor
        if armor.is_exotic and armor.exotic_effect and armor.name not in effect_map:
            effect_map[armor.name] = armor.exotic_effect
    return effect_map


def insert_into_grade(prefs: dict, name: str, grade: str, position: int) -> None:
    # Put the set at 1-based position in grade, then renumber that grade and the
    # one it left.
    pref = prefs[name]
    old_grade = pref.grade
    members = grade_members(prefs, grade, exclude=name)
    position = max(1, min(len(members) + 1, position))
    members.insert(position - 1, (name, pref))
    pref.grade = grade
    set_ranks(members)
    if old_grade and old_grade != grade:
        renumber_grade(prefs, old_grade)


def save_preferences(conn, prefs: dict) -> None:
    # Replace the stored preferences with prefs. Renumbers each grade and
    # reorders prefs in place (see sorted_prefs).
    for grade in armor_grades.GRADE_ORDER:
        renumber_grade(prefs, grade)
    ordered = sorted_prefs(prefs)
    with conn:
        conn.execute("DELETE FROM armor_preference")
        conn.executemany(
            "INSERT INTO armor_preference "
            "(name, is_exotic, stat_1, stat_2, stat_3, grade, rank) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    name,
                    int(pref.is_exotic),
                    pref.stat_1,
                    pref.stat_2,
                    pref.stat_3,
                    pref.grade,
                    pref.rank,
                )
                for name, pref in ordered.items()
            ],
        )
    prefs.clear()
    prefs.update(ordered)


# Lookups during scoring and reporting.


def pref_name(inst) -> str:
    # The preference an armor piece follows: its own for an exotic, its set's
    # otherwise.
    if inst.armor.is_exotic:
        return inst.armor.name
    return inst.armor.set_name


def get_pref(prefs: dict, name: str):
    # The ArmorPreference stored under name (case-insensitive), or None.
    _, val = ci_get(prefs, name)
    return val
