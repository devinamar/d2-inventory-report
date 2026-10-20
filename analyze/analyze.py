# Analyze phase: each function reads the stored inventory, runs its analyses
# and saves every result the report shows: weapon_result and weapon_pruning
# for weapons; armor_score and armor_rescue for armor, from which the
# v_armor_pruning view works out the pieces to dismantle. Also holds the
# --edit-armor-prefs mode.
import collections
import sys

from analyze import aegis_rankings, armor_pruning, inventory, results, weapon_pruning
from analyze.prefs import editor, store
from analyze.wishlists import scorer


def edit_prefs(conn):
    # --edit-armor-prefs: open the preference editor, save, exit.
    prefs = store.load_preferences(conn)
    if not prefs:
        print("No armor preferences stored yet; run a report first.")
        sys.exit(1)
    armor_instances = inventory.load_armor(conn)
    print("Launching armor preferences editor...")
    editor.edit_menu(
        prefs,
        aegis_rankings.load(conn),
        store.build_set_bonus_map(armor_instances),
        store.build_exotic_effect_map(armor_instances),
    )
    store.save_preferences(conn, prefs)
    print("Preferences saved.")


def weapons(conn) -> None:
    # Score every Legendary and Exotic copy against the stored wishlists
    # (analyze/wishlists/scorer.py) and save the scores, then flag every true
    # duplicate (analyze/weapon_pruning.py), whose keeper the saved scores help
    # pick, and every copy below Legendary.
    weapon_instances = inventory.load_weapons(conn)
    rolls_by_source = scorer.load_all(conn)
    scores = {}
    if rolls_by_source:
        print("\nScoring weapon instances against wishlists...")
        scores = scorer.score_all_instances(
            weapon_instances, rolls_by_source, scorer.PlugCatalog(conn)
        )
        endorsed = sum(1 for s in scores.values() if s.match_count > 0)
        uncovered = sum(1 for s in scores.values() if not s.has_wishlist)
        total_matches = sum(s.match_count for s in scores.values())
        print(
            f"  Scored {len(scores)} instances: {endorsed} match at least one wishlist roll "
            f"({total_matches} total matches), {uncovered} have no wishlist coverage"
        )
    results.save_weapon_results(conn, weapon_instances, scores)

    below = inventory.load_below_legendary(conn)
    duplicated = weapon_pruning.find_exact_duplicates(conn)
    print(f"\nWeapons: {len(duplicated)} true duplicates, {len(below)} below Legendary")
    results.save_weapon_pruning(
        conn,
        [(iid, 'below_legendary', None) for iid in below]
        + [(iid, 'exact_duplicate', keeper_id) for iid, keeper_id in duplicated],
    )


def ensure_preferences(conn, armor_instances) -> dict:
    # The stored preferences, after prompting for any set or exotic without
    # one that you own an Armor 3.0 piece of (any gear tier), and any exotic
    # without one that you own two or more copies of; saved when anything
    # changed.
    prefs = store.load_preferences(conn)
    sets_needed = {
        inst.armor.set_name
        for inst in armor_instances
        if inst.armor.set_name and inst.gear_tier and not inst.armor.is_exotic
    }
    # Exotics group by name ignoring case, as v_armor_pruning groups them;
    # each is asked for under its first copy's name.
    exotic_copies = collections.defaultdict(list)
    for inst in armor_instances:
        if inst.armor.is_exotic:
            exotic_copies[inst.armor.name.lower()].append(inst)
    exotics_needed = {
        copies[0].armor.name
        for copies in exotic_copies.values()
        if len(copies) > 1 or any(inst.gear_tier for inst in copies)
    }
    if sets_needed or exotics_needed:
        prefs, changed = editor.ensure_preferences(
            sets_needed, exotics_needed, armor_instances, prefs, aegis_rankings.load(conn)
        )
        if changed:
            store.save_preferences(conn, prefs)
    return prefs


def armor(conn) -> None:
    # Make sure every new set and exotic has preferences (may prompt),
    # then save the armor scores and the pieces rescued for three-stat builds.
    armor_instances = inventory.load_armor(conn)
    if not armor_instances:
        print("  No armor found in inventory")
    prefs = ensure_preferences(conn, armor_instances)
    results.save_armor_scores(conn, armor_pruning.compute_armor_scores(armor_instances, prefs))
    rescued = armor_pruning.triple_rescue(conn)
    results.save_armor_rescue(conn, rescued)
    counts = conn.execute(
        "SELECT reason, COUNT(*) - SUM(rescued) FROM v_armor_pruning "
        "GROUP BY reason ORDER BY reason"
    ).fetchall()
    print(
        f"  Armor to dismantle: {', '.join(f'{reason}={n}' for reason, n in counts)}; "
        f"{len(rescued)} rescued"
    )
