# Which weapon copies to flag, and why: every true duplicate (an exact copy of
# one that stays), found here, and every copy below Legendary
# (inventory.load_below_legendary). The flags go to weapon_pruning through
# analyze/results.py.

# Why a copy is flagged: the label on its tile, in report order.
PRUNE_REASONS = {
    'below_legendary': 'Below Legendary',
    'exact_duplicate': 'True duplicate',
}

# A copy's roll as one string, each perk socket in socket order with its perks
# by name (names, since a reissue has new perk hashes), then the copies that
# share family, element, archetype and roll, ranked best first.
EXACT_DUPLICATES = """
WITH socket AS (
    SELECT instance_id, socket_idx, kind, group_concat(perk, ', ' ORDER BY perk) AS perks
    FROM v_weapon_roll
    GROUP BY instance_id, socket_idx
),
roll AS (
    SELECT instance_id, group_concat(kind || ': ' || perks, '; ' ORDER BY socket_idx) AS perks
    FROM socket
    GROUP BY instance_id
),
ranked AS (
    SELECT v.instance_id,
           FIRST_VALUE(v.instance_id) OVER copies AS keeper_id,
           ROW_NUMBER() OVER copies AS n
    FROM v_weapon v
    JOIN weapon_result w ON w.instance_id = v.instance_id
    JOIN roll ON roll.instance_id = v.instance_id
    WINDOW copies AS (
        PARTITION BY v.family_name, v.element, v.archetype, roll.perks
        ORDER BY COALESCE(v.gear_tier, 0) DESC, w.match_count DESC, v.instance_id
    )
)
SELECT instance_id, keeper_id FROM ranked WHERE n > 1 ORDER BY instance_id
"""


def find_exact_duplicates(conn) -> list:
    # [(instance_id, keeper_id)] for every scored copy that duplicates a kept
    # one. Reads the scores, so it runs after save_weapon_results.
    return [(r['instance_id'], r['keeper_id']) for r in conn.execute(EXACT_DUPLICATES)]
