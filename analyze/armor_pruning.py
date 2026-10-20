# Armor pruning: scores every Armor 3.0 piece and exotic against its
# preference (saved to armor_score), then finds the capped pieces a three-stat
# build needs (armor_rescue). Which pieces go, and why, is the v_armor_pruning view
# over those two tables and the set grades. Armor 3.0 is the armor with gear
# tiers, set bonuses and tuning; earlier armor is legacy.
import itertools

import models
from analyze import armor_grades
from analyze.prefs import store

# Why a piece is flagged, in report order: code -> (title, explanation). The
# codes are v_armor_pruning's reasons; the single source for their labels in
# both report formats.
PRUNE_REASONS = {
    'cap_tier': (
        'Low score',
        f"Past its set's per-slot cap for its grade ({armor_grades.cap_summary()} copies per "
        "slot): the set keeps its best-scoring copies in each slot and class.",
    ),
    'exotic_dupe': (
        'Extra exotic copies',
        'Each exotic keeps its best copy on its stat picks; an exotic class item keeps one '
        'per perk pair.',
    ),
    'legacy': (
        'Legacy, before Armor 3.0',
        'From before Armor 3.0: no gear tier, set bonus or tuning.',
    ),
    'equal_same_set': (
        'Duplicate stats and Tuning',
        'The same stats and tuning stat as an older copy of the set, which stays.',
    ),
}

# Position of each stat in an ArmorStats tuple.
STAT_INDEX = {name: i for i, name in enumerate(models.ARMOR_STAT_NAMES)}


# Scoring: an ArmorScore for each piece, the ranking key when pruning.


def apply_mw_to_zeros(base: tuple) -> tuple:
    # Masterwork on Armor 3.0: +5 to each stat that is 0 (a piece of any gear
    # tier drops with three of them); the other stats are unchanged.
    return tuple(v + 5 if v == 0 else v for v in base)


def tuning_variants(base: tuple, tuning_stats: tuple) -> list:
    # Every stat spread the piece can reach, as (stats, label): untuned first,
    # then each swap its tuning socket offers, +5 to one of tuning_stats and -5
    # from another stat of at least 5. Masterwork is applied after the swap, so
    # tuning and masterwork never both raise the same zero.
    variants = [(apply_mw_to_zeros(base), '')]
    short = models.ARMOR_STAT_SHORT
    targets = [STAT_INDEX[stat] for stat in tuning_stats]
    for donor in range(6):
        if base[donor] < 5:
            continue
        for target in targets:
            if target == donor:
                continue
            tuned = list(base)
            tuned[donor] -= 5
            tuned[target] += 5
            variants.append(
                (
                    apply_mw_to_zeros(tuple(tuned)),
                    f"+5 {short[target]} / -5 {short[donor]}",
                )
            )
    return variants


def best_variant_for_prefs(
    base: tuple, priority: list, specified: int, tuning_stats: tuple
) -> tuple:
    # (stats, label) of the variant that does best on the priority stats,
    # compared in priority order (at least the top stat), then by total.
    picked = [STAT_INDEX[stat] for stat in priority[: max(specified, 1)]]
    return max(
        tuning_variants(base, tuning_stats),
        key=lambda v: (tuple(v[0][i] for i in picked), sum(v[0])),
    )


def pref_or_default(prefs: dict, name: str):
    # The preference stored under name (case-insensitive), else one with no
    # grade and no stat picks.
    return store.get_pref(prefs, name) or models.ArmorPreference()


# preferred_score = 3*stat[pref1] + 2*stat[pref2] + 1*stat[pref3].
PREFERRED_STAT_WEIGHTS = (3, 2, 1)


def weighted_score(stats: tuple, pref) -> float:
    # The score of a stat spread under pref (see PREFERRED_STAT_WEIGHTS);
    # without stat picks, the stat total.
    if pref.specified <= 0:
        return float(sum(stats))
    return float(
        sum(
            PREFERRED_STAT_WEIGHTS[i] * stats[STAT_INDEX[stat]]
            for i, stat in enumerate(pref.picks())
        )
    )


def compute_armor_score(inst: models.ArmorInstance, pref) -> models.ArmorScore:
    # One piece's ArmorScore under pref, from its best variant. tuning_gain is
    # what that variant's tuning swap adds to the untuned piece's score. An
    # exotic scores untuned: a Tier 5 exotic can tune any stat, so tuning
    # doesn't tell its copies apart.
    base = inst.stats.as_tuple()
    tuning_stats = inst.tuning_stats
    if inst.armor.is_exotic:
        tuning_stats = ()
    best_stats, label = best_variant_for_prefs(
        base, pref.full_priority(), pref.specified, tuning_stats
    )
    preferred_score = weighted_score(best_stats, pref)
    return models.ArmorScore(
        instance_id=inst.instance_id,
        preferred_score=preferred_score,
        best_tuning=label,
        best_stats=best_stats,
        tuning_gain=preferred_score - weighted_score(apply_mw_to_zeros(base), pref),
    )


def compute_armor_scores(all_instances: list, prefs: dict) -> dict:
    # {instance_id: ArmorScore} for every Armor 3.0 piece and every exotic,
    # each under the preference it follows (its set's, or the exotic's own).
    # A piece below gear tier 5 has no tuning socket, so it scores untuned.
    scores = {}
    for inst in all_instances:
        if not inst.gear_tier and not inst.armor.is_exotic:
            continue  # legacy: always dropped, no score
        pref = pref_or_default(prefs, store.pref_name(inst))
        scores[inst.instance_id] = compute_armor_score(inst, pref)
    return scores


# Rescue: the capped pieces a three-stat build needs.

TRIPLE_THRESHOLD = 100  # what each stat of a three-stat build should reach

# The capped pieces, lowest itemInstanceId first, with what the rescue ranks
# them by: their set grade's position (1 best) and rank in it, and their score.
CAPPED = """
SELECT a.*, g.position AS grade_position, p.rank, s.preferred_score
FROM v_armor_pruning f
JOIN v_armor a ON a.instance_id = f.instance_id
JOIN armor_score s ON s.instance_id = f.instance_id
LEFT JOIN armor_preference p ON p.name = a.set_name COLLATE NOCASE
JOIN armor_grade g ON g.grade = COALESCE(p.grade, '')
WHERE f.reason = 'cap_tier'
ORDER BY a.instance_id
"""


def set_rank(piece) -> tuple:
    # Higher for a better set: its grade, then its rank within the grade.
    # Sets without a rank come after the ranked ones of their grade.
    return (-piece['grade_position'], -(piece['rank'] or float('inf')))


def load_reach(conn) -> dict:
    # {(armor_class, stat names): (totals, {slot: values})}: how far the kept
    # pieces take each three-stat build (v_armor_reach).
    reach = {}
    for r in conn.execute("SELECT * FROM v_armor_reach"):
        build = (r['armor_class'], (r['stat_1'], r['stat_2'], r['stat_3']))
        totals = (r['total_1'], r['total_2'], r['total_3'])
        per_slot = reach.setdefault(build, (totals, {}))[1]
        per_slot[r['slot']] = (r['value_1'], r['value_2'], r['value_3'])
    return reach


def triple_rescue(conn) -> dict:
    # Stage 4: for each class and three-stat build the kept pieces can't take
    # to TRIPLE_THRESHOLD in every stat, keep the capped piece that can, else
    # the two from different slots: the better set first (a pair counts its better
    # set), then the higher new minimum, then the higher scores, then the lower
    # itemInstanceId. Raw stats, as the reach. Returns {instance_id: [(stat
    # names, new min)]}; reads the saved scores, so it runs after them.
    capped = conn.execute(CAPPED).fetchall()
    rescued = {}
    for (armor_class, build), (totals, per_slot) in load_reach(conn).items():
        if min(totals) >= TRIPLE_THRESHOLD:
            continue
        # The class's capped pieces that beat their slot's best for this
        # build, each with what it adds to each stat.
        gains = []
        for piece in capped:
            if piece['armor_class'] != armor_class:
                continue
            values = [piece[stat] for stat in build]
            best = per_slot.get(piece['slot'], (0, 0, 0))
            if (min(values), sum(values)) > (min(best), sum(best)):
                gains.append((piece, [v - b for v, b in zip(values, best, strict=True)]))
        for size in (1, 2):
            choice = None
            for combo in itertools.combinations(gains, size):
                if len({piece['slot'] for piece, _ in combo}) < size:
                    continue
                new_min = min(t + sum(gain[i] for _, gain in combo) for i, t in enumerate(totals))
                if new_min < TRIPLE_THRESHOLD:
                    continue
                key = (
                    max(set_rank(piece) for piece, _ in combo),
                    new_min,
                    sum(piece['preferred_score'] for piece, _ in combo),
                )
                if choice is None or key > choice[0]:
                    choice = (key, new_min, combo)
            if choice:
                for piece, _ in choice[2]:
                    rescued.setdefault(piece['instance_id'], []).append((build, choice[1]))
                break
    return rescued
