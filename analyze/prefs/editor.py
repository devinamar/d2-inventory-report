# Interactive terminal editor for armor preferences. Asks a new set for its stat
# picks, grade and place (showing The Aegis's rankings for reference) and a
# new exotic for its stat picks, then offers a menu to move, reorder or
# re-prompt them. Entry points: ensure_preferences during a run, edit_menu for
# --edit-armor-prefs. The caller loads and saves the preferences.
import models
from analyze import aegis_rankings, armor_grades
from analyze.prefs import store, suggest, terminal

# Stat name -> short label (from models.py).
STAT_SHORT = models.ARMOR_STAT_SHORT_MAP


# Fixed numbered menu: number → (internal name, display name)
STAT_DISPLAY_NAMES = {
    1: ('health', 'Health'),
    2: ('melee', 'Melee'),
    3: ('grenade', 'Grenade'),
    4: ('super_stat', 'Super'),
    5: ('class_stat', 'Class'),
    6: ('weapons', 'Weapons'),
    7: (None, 'None'),  # sentinel — ends selection
}


def aegis_bonus_lines(set_name: str, aegis: dict) -> list:
    # The Aegis sheet's trigger, effect and analysis lines for each bonus, in
    # ASCII (a cp1252 Windows console can't print arbitrary Unicode). [] when
    # the set isn't in the sheet.
    lines = []
    for b in aegis_rankings.get_aegis_bonuses(aegis, set_name):
        text = (
            f"  Aegis #{b.rank} [{b.grade}] {b.pieces}pc "
            f"{b.bonus_name}: {b.trigger} -> {b.effect}"
            f" | {b.analysis}"
        )
        text = ' '.join(text.split())  # sheet cells embed newlines
        lines.append('  ' + text.encode('ascii', 'replace').decode())
    return lines


def format_set_bonus(set_name: str, aegis: dict, bonus_map: dict | None = None) -> str:
    # Multi-line 2pc/4pc bonus block shown while prompting for a set,
    # plus the Aegis sheet's trigger/effect/analysis per bonus (which also
    # feeds the suggested-stat heuristic).
    two, four = store.set_bonus_text(set_name, bonus_map)
    lines = []
    if two or four:
        lines.append(f"  2pc: {two or '(unknown)'}\n  4pc: {four or '(unknown)'}")
    lines.extend(aegis_bonus_lines(set_name, aegis))
    if not lines:
        return "  (set bonus descriptions not available)"
    return "\n".join(lines)


def bonus_inline(
    set_name: str, bonus_map: dict | None, indent: str = '          ', width: int = 0
) -> list:
    # Short indented 2- and 4-piece bonus lines for the classification and
    # reorder views; [] when no bonus is known. width > 0 truncates each line.
    two, four = store.set_bonus_text(set_name, bonus_map)
    lines = []
    for label, text in (('2pc', two), ('4pc', four)):
        if not text:
            continue
        line = f"{indent}{label} {text}"
        if width and len(line) > width:
            line = line[: width - 3] + '...'
        lines.append(line)
    return lines


def prompt_stat_priority(set_name: str, bonus_desc: str) -> list:
    # Ask for up to three priority stats with single keypresses (1-6 pick a
    # stat, 7 stops early). Shows the bonus text and a priority guessed from it.
    # Returns the picks, padded with None to three.
    print(f"\n{set_name} armor stat preferences?")
    print(bonus_desc)
    suggested = suggest.suggest_stats(bonus_desc)
    if suggested:
        print(f"  Suggested: {' > '.join(STAT_SHORT[s] for s in suggested)}")

    selected = []
    # Track which number keys are still available (1-6 are stats, 7 is None)
    available = set(range(1, 8))  # {1,2,3,4,5,6,7}

    for pick_num in range(1, 4):  # up to 3 picks
        print()
        for num in sorted(available):
            _, display = STAT_DISPLAY_NAMES[num]
            print(f"  {num}. {display}")

        valid_keys = sorted(available)
        if len(valid_keys) <= 3:
            valid_str = ','.join(str(k) for k in valid_keys)
        else:
            # Compact range display
            valid_str = f"{valid_keys[0]}-{valid_keys[-1]}"

        ordinal = {1: '1st', 2: '2nd', 3: '3rd'}[pick_num]
        prompt_text = f"Select {ordinal} priority [{valid_str}]: "
        print(prompt_text, end='', flush=True)

        while True:
            ch = terminal.read_single_key()

            if ch.isdigit() and int(ch) in available:
                choice = int(ch)
                stat_name, display = STAT_DISPLAY_NAMES[choice]
                print(ch)  # echo the keypress
                print(f"  -> {display}")

                if choice == 7:
                    # 7 ends the selection.
                    break
                else:
                    selected.append(stat_name)
                    available.discard(choice)
                    break
            # Other keys are ignored.
        else:
            continue

        if choice == 7:
            break

    # No picks means no preference.
    if not selected:
        print(f"  No preference -- dominance comparison skipped for {set_name}")
        return [None, None, None]

    labels = [STAT_SHORT[s] for s in models.ArmorPreference(*selected).full_priority()]
    display = ' > '.join(
        f'[{label}]' if i < len(selected) else label for i, label in enumerate(labels)
    )
    print(f"\nPriorities: {display}")
    return (selected + [None, None, None])[:3]


def render_classification(prefs: dict, aegis: dict, bonus_map: dict | None = None) -> str:
    # The current set classification by grade, as printable text. With a
    # bonus_map, each set's 2- and 4-piece bonuses show under its name.
    lines = [
        "",
        "== Armor Set Classification ==",
        "   (#n = the set's best Aegis set-bonus rank, for reference)",
    ]
    for grade in armor_grades.GRADE_ORDER:
        members = store.grade_members(prefs, grade)
        lines.append(f"\n  [{grade}] {armor_grades.GRADE_LABELS[grade]}")
        if not members:
            lines.append("      (empty)")
            continue
        for rank, (name, _) in enumerate(members, start=1):
            ranking = aegis_rankings.get_aegis_ranking(aegis, name)
            if ranking:
                marker = f"  #{ranking.rank}"
            else:
                marker = "  (not on the Aegis sheet)"
            lines.append(f"      {rank:>2}. {name}{marker}")
            lines.extend(bonus_inline(name, bonus_map))
    return "\n".join(lines)


def render_exotic_prefs(prefs: dict) -> str:
    # The exotics' stat picks, as printable text.
    exotics = sorted((n for n, p in prefs.items() if p.is_exotic), key=str.lower)
    lines = ["", "== Exotic Stat Preferences =="]
    if not exotics:
        lines.append("  (none)")
    for name in exotics:
        picks = prefs[name].picks()
        if picks:
            summary = ' > '.join(STAT_SHORT[p] for p in picks)
        else:
            summary = '(no preference)'
        lines.append(f"  {name}: {summary}")
    return "\n".join(lines)


def prompt_grade(set_name: str) -> str:
    # Prompt for a grade code — returns one of GRADE_ORDER ('S'..'F').
    print(f"\nClassify {set_name}:")
    for i in range(0, len(armor_grades.GRADES), 4):
        print(
            '  '
            + '   '.join(
                f"[{g.code}] {g.label:<13}" for g in armor_grades.GRADES[i : i + 4]
            ).rstrip()
        )
    print("Select grade: ", end='', flush=True)
    while True:
        ch = terminal.read_single_key()
        if not ch:
            continue
        up = ch.upper()
        if up in armor_grades.GRADE_ORDER:
            print(up)
            print(f"  -> {armor_grades.GRADE_LABELS[up]}")
            return up


def prompt_position(
    set_name: str,
    grade: str,
    prefs: dict,
    exclude: str | None = None,
    bonus_map: dict | None = None,
) -> int:
    # Show current grade members and prompt for a 1-based insert position.
    members = store.grade_members(prefs, grade, exclude=exclude or set_name)
    print(f"\n{grade} grade current order:")
    if not members:
        print("      (empty)")
    for rank, (name, _) in enumerate(members, start=1):
        print(f"      {rank:>2}. {name}")
        for line in bonus_inline(name, bonus_map, width=90):
            print(line)
    end_pos = len(members) + 1
    print(f"      {end_pos:>2}. <end>")
    max_pos = end_pos

    while True:
        raw = input(f"Insert {set_name} at position [1-{max_pos}, default={max_pos}]: ").strip()
        if not raw:
            return max_pos
        try:
            pos = int(raw)
        except ValueError:
            print("  Invalid position.")
            continue
        if 1 <= pos <= max_pos:
            return pos
        print("  Invalid position.")


def format_exotic_effect(name: str, effect_map: dict | None = None) -> str:
    # Multi-line effect block shown while prompting for an exotic.
    eff = (effect_map or {}).get(name)
    if not eff or not (eff.name or eff.description):
        return "  (exotic effect description not available)"
    if eff.name:
        head = f"  Effect: {eff.name}"
    else:
        head = "  Effect:"
    if eff.description:
        return f"{head}\n  {' '.join(eff.description.split())}"
    return head


# Prompts for entries a run needs: new sets, sets without a grade, and
# exotics without stat picks.


def prompt_add_new_set(
    set_name: str, prefs: dict, aegis: dict, bonus_map: dict | None = None
) -> None:
    # Flow for a brand-new set: its stat picks, grade and place, with its Aegis
    # bonus rankings shown above the prompts for reference.
    print(render_classification(prefs, aegis, bonus_map))
    picks = prompt_stat_priority(set_name, format_set_bonus(set_name, aegis, bonus_map))
    grade = prompt_grade(set_name)
    prefs[set_name] = models.ArmorPreference(*picks)
    position = prompt_position(set_name, grade, prefs, bonus_map=bonus_map)
    store.insert_into_grade(prefs, set_name, grade, position)


def prompt_classify_existing(
    set_name: str, prefs: dict, aegis: dict, bonus_map: dict | None = None
) -> None:
    # Back-fill flow for an entry that has stat prefs but no grade.
    print(render_classification(prefs, aegis, bonus_map))
    print(f"\n{set_name}: missing grade classification.")
    print(format_set_bonus(set_name, aegis, bonus_map))
    grade = prompt_grade(set_name)
    position = prompt_position(set_name, grade, prefs, bonus_map=bonus_map)
    store.insert_into_grade(prefs, set_name, grade, position)


def prompt_exotic_priority(name: str, prefs: dict, effect_map: dict | None = None) -> None:
    # Prompt stat picks for one exotic, showing its intrinsic effect.
    picks = prompt_stat_priority(name, format_exotic_effect(name, effect_map))
    prefs[name] = models.ArmorPreference(*picks, is_exotic=True)


# The editor menu: move, reorder or re-prompt any entry.


def prompt_move(prefs: dict, aegis: dict, bonus_map: dict | None = None) -> bool:
    # Move an existing set to a new grade and/or position.
    print(render_classification(prefs, aegis, bonus_map))
    raw = input("\nSet to move (name, blank to cancel): ").strip()
    if not raw:
        return False
    canon, entry = store.ci_get(prefs, raw)
    if entry is None or entry.is_exotic:
        print(f"  {raw!r} is not a set.")
        return False
    grade = prompt_grade(canon)
    position = prompt_position(canon, grade, prefs, exclude=canon, bonus_map=bonus_map)
    store.insert_into_grade(prefs, canon, grade, position)
    return True


def arrow_reorder_grade(prefs: dict, grade: str, bonus_map: dict | None = None) -> bool:
    # Arrow-key reorder UI for a single grade.
    #
    # Up/Down move the cursor. Enter picks the highlighted set up; Up/Down
    # then slide it through the list. Enter again drops it. ESC cancels
    # (any in-progress drag is reverted). Returns True if the order changed.
    members = store.grade_members(prefs, grade)
    if len(members) < 2:
        print(f"  {grade} grade has fewer than 2 members; nothing to reorder.")
        return False

    original = [name for name, _ in members]
    cursor = 0
    picked = False

    while True:
        terminal.clear_screen()
        print(f"== Reorder {grade} ({armor_grades.GRADE_LABELS[grade]}) ==\n")
        if picked:
            print("  Dragging. Up/Down: move  |  Enter: drop  |  ESC: cancel\n")
        else:
            print("  Up/Down: navigate  |  Enter: pick up  |  ESC: done\n")

        for i, (name, _) in enumerate(members):
            if picked and i == cursor:
                marker = '[>]'
            elif i == cursor:
                marker = ' > '
            else:
                marker = '   '
            print(f"  {marker}{i + 1:>2}. {name}")
            if i == cursor:
                for line in bonus_inline(name, bonus_map, indent='        ', width=78):
                    print(line)
        print()

        key = terminal.read_key()
        if key == 'UP':
            if cursor == 0:
                continue
            if picked:
                members[cursor - 1], members[cursor] = members[cursor], members[cursor - 1]
            cursor -= 1
        elif key == 'DOWN':
            if cursor == len(members) - 1:
                continue
            if picked:
                members[cursor + 1], members[cursor] = members[cursor], members[cursor + 1]
            cursor += 1
        elif key == 'ENTER':
            # Pick up the highlighted set, or drop it at the current
            # position. After dropping, stay in the reorder loop so the
            # user can move another set without bouncing back to the menu.
            picked = not picked
        elif key == 'ESC':
            # ESC always exits. If a drag is in progress, the set stays
            # where it currently sits (treated as a commit).
            picked = False
            break

    if [name for name, _ in members] == original:
        return False
    store.set_ranks(members)
    return True


def prompt_reorder(prefs: dict, aegis: dict, bonus_map: dict | None = None) -> bool:
    # Pick a grade, then launch the arrow-key reorder UI.
    print(render_classification(prefs, aegis, bonus_map))
    print("\nReorder which grade?")
    print("  [S] [A] [B] [C] [D] [E] [F]")
    print("Select grade: ", end='', flush=True)
    grade = None
    while grade is None:
        ch = terminal.read_single_key()
        if not ch:
            continue
        up = ch.upper()
        if up in armor_grades.GRADE_ORDER:
            print(up)
            grade = up
        elif ch in ('\x1b', '\r', '\n'):
            print()
            return False
    return arrow_reorder_grade(prefs, grade, bonus_map)


def prompt_edit_priorities(
    prefs: dict, aegis: dict, bonus_map: dict | None = None, effect_map: dict | None = None
) -> bool:
    # Re-run the stat priority prompt for a set or an exotic.
    raw = input("Set or exotic to re-prompt (name, blank to cancel): ").strip()
    if not raw:
        return False
    canon, entry = store.ci_get(prefs, raw)
    if entry is None:
        print(f"  {raw!r} not found.")
        return False
    if entry.is_exotic:
        desc = format_exotic_effect(canon, effect_map)
    else:
        desc = format_set_bonus(canon, aegis, bonus_map)
    entry.stat_1, entry.stat_2, entry.stat_3 = prompt_stat_priority(canon, desc)
    return True


def edit_menu(
    prefs: dict, aegis: dict, bonus_map: dict | None = None, effect_map: dict | None = None
) -> None:
    # Free-form editor loop shown after any required prompts finish.
    while True:
        print(render_classification(prefs, aegis, bonus_map))
        print(render_exotic_prefs(prefs))
        print("\n[M]ove between grades   [R]eorder within grade   [E]dit stat priorities   [Q]uit")
        print("Action: ", end='', flush=True)
        ch = terminal.read_single_key()
        if not ch:
            continue
        up = ch.upper()
        print(up)
        if up == 'Q':
            return
        elif up == 'M':
            prompt_move(prefs, aegis, bonus_map)
        elif up == 'R':
            prompt_reorder(prefs, aegis, bonus_map)
        elif up == 'E':
            prompt_edit_priorities(prefs, aegis, bonus_map, effect_map)


# Entry point during a run.


def ensure_preferences(
    sets_needed, exotics_needed, armor_instances, existing_prefs, aegis
) -> tuple:
    # Make sure every set in sets_needed has stat picks and a grade, and every
    # exotic in exotics_needed has stat picks; returns (preferences, changed).
    # A set with no entry gets the add flow (stats, grade and position), an
    # entry without a valid grade gets the classify flow, and an exotic without
    # an entry is asked for stat picks. If anything was prompted, the editor
    # menu opens before returning; saved entries change only through it, or
    # take a set's new capitalization when the game renames it.
    prefs = dict(existing_prefs)
    bonus_map = store.build_set_bonus_map(armor_instances)
    effect_map = store.build_exotic_effect_map(armor_instances)

    mandatory_new = []
    mandatory_classify = []
    renamed = False
    for set_name in sorted(sets_needed):
        canon_key, existing = store.ci_get(prefs, set_name)
        if existing is not None:
            if canon_key != set_name:
                prefs[set_name] = existing
                del prefs[canon_key]
                canon_key = set_name
                renamed = True
            if existing.grade not in armor_grades.GRADE_ORDER:
                mandatory_classify.append(canon_key)
        else:
            mandatory_new.append(set_name)
    pending_exotics = [n for n in sorted(exotics_needed) if store.ci_get(prefs, n)[1] is None]

    for set_name in mandatory_new:
        prompt_add_new_set(set_name, prefs, aegis, bonus_map)
    for set_name in mandatory_classify:
        prompt_classify_existing(set_name, prefs, aegis, bonus_map)
    for name in pending_exotics:
        prompt_exotic_priority(name, prefs, effect_map)

    did_work = bool(mandatory_new or mandatory_classify or pending_exotics)
    if did_work:
        edit_menu(prefs, aegis, bonus_map, effect_map)
    return prefs, did_work or renamed
