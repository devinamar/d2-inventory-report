# Saves the analysis results, one group of tables per analysis (the tables in
# db/schema/results/). Each save replaces its tables, since every run
# recomputes everything.
import models


def save_weapon_results(conn, weapons: list, scores: dict) -> None:
    # Replace weapon_result and instance_wishlist_match: one result row per
    # copy in weapons, one match row per roll it matched. scores is
    # {instance_id: InstanceWishlistScore}, empty when no wishlist is stored.
    no_score = models.InstanceWishlistScore()
    result_rows = []
    match_rows = []
    for inst in weapons:
        score = scores.get(inst.instance_id, no_score)
        result_rows.append((inst.instance_id, score.match_count, int(score.has_wishlist)))
        match_rows.extend((inst.instance_id, roll_id) for roll_id in score.matched_roll_ids)
    with conn:
        conn.execute("DELETE FROM instance_wishlist_match")
        conn.execute("DELETE FROM weapon_result")
        conn.executemany("INSERT INTO weapon_result VALUES (?, ?, ?)", result_rows)
        conn.executemany("INSERT INTO instance_wishlist_match VALUES (?, ?)", match_rows)


def save_weapon_pruning(conn, flagged: list) -> None:
    # Replace weapon_pruning with flagged: [(instance_id, reason, keeper_id)].
    with conn:
        conn.execute("DELETE FROM weapon_pruning")
        conn.executemany("INSERT INTO weapon_pruning VALUES (?, ?, ?)", flagged)


def save_armor_scores(conn, scores: dict) -> None:
    # Replace armor_score with one row per ArmorScore ({instance_id:
    # ArmorScore}). Legacy pieces have no score unless exotic; they are
    # always flagged.
    rows = [
        (
            score.instance_id,
            score.preferred_score,
            score.best_tuning,
            score.tuning_gain,
            *score.best_stats,
        )
        for score in scores.values()
    ]
    with conn:
        conn.execute("DELETE FROM armor_score")
        conn.executemany(
            "INSERT INTO armor_score VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def save_armor_rescue(conn, rescued: dict) -> None:
    # Replace armor_rescue with one row per rescued piece and three-stat build
    # it takes to 100: rescued is {instance_id: [(stat names, new min)]}.
    with conn:
        conn.execute("DELETE FROM armor_rescue")
        conn.executemany(
            "INSERT INTO armor_rescue VALUES (?, ?, ?, ?, ?)",
            [
                (iid, *stats, new_min)
                for iid, builds in rescued.items()
                for stats, new_min in builds
            ],
        )
