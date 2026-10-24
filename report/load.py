# Reads everything the report shows from the db: one query per list, each in
# the order the report shows it, so the templates only group consecutive rows.
# Nothing is recomputed; the counts, scores and flags are the stored results
# and the views over them.
import models
from analyze import aegis_rankings

# Each armor class's place in every class switch: most pieces first.
CLASS_N = """
SELECT armor_class, ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, armor_class) AS class_n
FROM v_armor
GROUP BY armor_class
"""

# The armor classes with their piece counts, the exotics owned (by name,
# ignoring case) out of the class's exotic armor in the manifest, and how many
# of the 20 three-stat builds the kept armor takes to 100 in each stat.
CLASSES = f"""
WITH build AS (
    SELECT DISTINCT armor_class, stat_1, stat_2, stat_3, MIN(total_1, total_2, total_3) AS low
    FROM v_armor_reach
)
SELECT a.armor_class, COUNT(*) AS pieces, SUM(NOT a.is_exotic) AS legendary,
       SUM(a.is_exotic) AS exotic,
       COUNT(DISTINCT CASE WHEN a.is_exotic THEN lower(a.name) END) AS exotics_owned,
       (SELECT COUNT(DISTINCT lower(d.name)) FROM DestinyInventoryItemDefinition d
        JOIN DestinyClassDefinition k ON k.classType = d.classType
        WHERE d.itemType = 2 AND d.tierType = 6 AND k.name = a.armor_class) AS exotics_total,
       (SELECT COUNT(*) FROM build b WHERE b.armor_class = a.armor_class AND b.low >= 100)
           AS covered
FROM v_armor a
JOIN ({CLASS_N}) c ON c.armor_class = a.armor_class
GROUP BY a.armor_class
ORDER BY c.class_n
"""

# The weapon copies left after pruning, each with its family's copy count and
# its place in the family (n): best wishlist score, then highest gear tier,
# then the oldest.
COPIES = """
SELECT v.instance_id, v.item_hash, v.name, v.family_name, v.slot, v.slot_order, v.wtype,
       v.wtype_icon, v.icon, v.watermark, v.ammo, v.ammo_icon, v.element, v.element_icon,
       v.archetype, v.archetype_icon, v.gear_tier,
       v.is_locked, v.is_masterworked, v.tier_overlay, v.masterwork_overlay,
       v.rpm, v.season_num, v.season_name, v.season_date, v.source,
       w.match_count, w.has_wishlist, d.tag, d.notes,
       COUNT(*) OVER (PARTITION BY v.family_name) AS copies,
       ROW_NUMBER() OVER (
           PARTITION BY v.family_name
           ORDER BY w.match_count DESC, COALESCE(v.gear_tier, 0) DESC, v.instance_id
       ) AS n
FROM v_weapon v
JOIN weapon_result w ON w.instance_id = v.instance_id
LEFT JOIN item_dim d ON d.instance_id = v.instance_id
WHERE v.instance_id NOT IN (SELECT instance_id FROM weapon_pruning)
"""

# The run's headline counts. families is Roll Quality's family count.
TOTALS = f"""
WITH copy AS ({COPIES})
SELECT (SELECT COUNT(*) FROM v_weapon) AS weapons, (SELECT COUNT(*) FROM v_armor) AS armor,
       (SELECT COUNT(*) FROM weapon_pruning WHERE reason = 'exact_duplicate') AS true_duplicates,
       (SELECT COUNT(*) FROM weapon_pruning WHERE reason = 'below_legendary') AS below_legendary,
       (SELECT COUNT(DISTINCT family_name) FROM copy WHERE copies > 1) AS families,
       COUNT(*) FILTER (WHERE w.match_count > 0) AS matched,
       COUNT(*) FILTER (WHERE NOT w.has_wishlist) AS uncovered,
       (SELECT COUNT(*) FROM v_armor_pruning WHERE NOT rescued) AS armor_to_purge,
       (SELECT COUNT(*) FROM v_armor_pruning WHERE rescued) AS rescued,
       (SELECT checked_at FROM source_status WHERE source = 'profile') AS checked_at
FROM weapon_result w
"""

# Every outside source with what it gives, a link and how it fared this run;
# ok is 0 for a failed, stale or skipped source, and for one never checked.
SOURCES = """
WITH source (source, name, gives, url, n) AS (
    VALUES ('manifest', 'Bungie manifest', 'Item, perk and set definitions',
            'https://www.bungie.net/', 1),
           ('profile', 'Bungie profile', 'Every weapon and armor copy',
            'https://www.bungie.net/', 2),
           ('dim', 'DIM', 'Your tags and notes', 'https://app.destinyitemmanager.com/', 3),
           ('clarity', 'Clarity', 'Community perk insights',
            'https://github.com/Database-Clarity/Live-Clarity-Database', 4),
           ('aegis', 'The Aegis', 'Armor set bonus rankings',
            'https://docs.google.com/spreadsheets/d/1JM-0SlxVDAi-C6rGVlLxa-J1WGewEeL8Qvq4htWZHhY/',
            6)
    UNION ALL
    SELECT 'wishlist:' || key, label, 'Weapon rolls to look for', url, 5 FROM wishlist_source
)
SELECT s.name, s.gives, s.url, st.checked_at,
       COALESCE(st.status IN ('fresh', 'cached'), 0) AS ok,
       CASE st.status
           WHEN 'fresh' THEN 'Up to date'
           WHEN 'cached' THEN 'Up to date'
           WHEN 'stale' THEN 'Download failed: the last good copy is used'
           WHEN 'failed' THEN 'Download failed, and no copy is stored'
           WHEN 'skipped' THEN 'Skipped'
           ELSE 'Not checked'
       END AS status
FROM source s
LEFT JOIN source_status st ON st.source = s.source
ORDER BY s.n, s.name
"""

# Every armor piece to purge (rescued ones stay): the Summary's DIM query.
ARMOR_PURGE = """
SELECT instance_id FROM v_armor_pruning WHERE NOT rescued ORDER BY instance_id
"""

# The armor pieces to purge, counted by reason, most first.
PURGE_COUNTS = """
SELECT reason, COUNT(*) AS n
FROM v_armor_pruning
WHERE NOT rescued
GROUP BY reason
ORDER BY n DESC, reason
"""

# The weapon copies weapon_pruning flags (the true duplicates and any copy below
# Legendary), by reason, then name.
WEAPON_FLAGS = """
SELECT p.instance_id, p.reason, p.keeper_id, v.name, v.wtype
FROM weapon_pruning p
JOIN v_weapon v ON v.instance_id = p.instance_id
ORDER BY p.reason, v.name, p.instance_id
"""

# Roll Quality: every weapon family with a copy left, by slot, weapon type and
# family, each family's copies best first; the families with more than one
# (copies > 1) are the ones to review. elements, archetypes, rpms and origins
# count the family's distinct elements, frames, rounds per minute and pairs of
# season and drop source; split gives a copy's completed wishlist rolls by
# list, like "2 Voltron, 1 Aegis Endgame", and trash the lists with a trash
# roll the copy fits, such as one trashing the whole weapon. kills is the
# count of the tracker plugged into its tracker socket, as DIM shows it:
# kill_kind what it counts (PvE, PvP or Gambit), kill_tracker its name and
# kill_icon its badge; NULL when the plugged tracker counts none of those.
ROLL_QUALITY = f"""
WITH copy AS ({COPIES}),
family AS (
    SELECT family_name, COUNT(DISTINCT element) AS elements,
           COUNT(DISTINCT archetype) AS archetypes, COUNT(DISTINCT rpm) AS rpms,
           COUNT(DISTINCT season_num || ' ' || season_name || ' ' || source) AS origins
    FROM copy
    GROUP BY family_name
),
tracker AS (
    SELECT instance_id, tracker, kind, kills, icon
    FROM v_kill_tracker
    WHERE is_plugged AND kind IS NOT NULL
)
SELECT copy.*, family.elements, family.archetypes, family.rpms, family.origins,
       tracker.kills, tracker.kind AS kill_kind, tracker.tracker AS kill_tracker,
       tracker.icon AS kill_icon,
       (SELECT group_concat(n || ' ' || label, ', ' ORDER BY ord)
        FROM (SELECT COUNT(*) AS n, l.label, l.rowid AS ord
              FROM instance_wishlist_match m
              JOIN wishlist_roll w ON w.roll_id = m.roll_id AND NOT w.is_trash
              JOIN wishlist_preference l ON l.key = w.source_key
              WHERE m.instance_id = copy.instance_id
              GROUP BY l.key)) AS split,
       (SELECT group_concat(label, ', ' ORDER BY ord)
        FROM (SELECT DISTINCT l.label, l.rowid AS ord
              FROM instance_wishlist_match m
              JOIN wishlist_roll w ON w.roll_id = m.roll_id AND w.is_trash
              JOIN wishlist_preference l ON l.key = w.source_key
              WHERE m.instance_id = copy.instance_id)) AS trash
FROM copy
JOIN family ON family.family_name = copy.family_name
LEFT JOIN tracker ON tracker.instance_id = copy.instance_id
ORDER BY copy.slot_order, copy.wtype, copy.family_name, copy.n
"""

# The columns of each Roll Quality family's tables: the perk sockets its copies
# have, labelled from their perks' plug category, after an Element column
# (socket_idx -1) when its copies differ in element.
ROLL_COLUMNS = f"""
WITH copy AS ({COPIES}),
family AS (SELECT * FROM copy),
socket AS (
    SELECT f.family_name, r.socket_idx,
           MIN(CASE pl.plugCategoryIdentifier
                   WHEN 'scopes' THEN 'Scope' WHEN 'tubes' THEN 'Tube'
                   WHEN 'bowstrings' THEN 'String' WHEN 'arrows' THEN 'Arrow'
                   WHEN 'blades' THEN 'Blade' WHEN 'guards' THEN 'Guard'
                   WHEN 'hafts' THEN 'Haft' WHEN 'batteries' THEN 'Battery'
                   ELSE upper(substr(r.kind, 1, 1)) || substr(r.kind, 2)
               END) AS label
    FROM v_weapon_roll r
    JOIN family f ON f.instance_id = r.instance_id
    JOIN v_plug pl ON pl.hash = r.plug_hash
    GROUP BY f.family_name, r.socket_idx
    UNION ALL
    SELECT family_name, -1, 'Element'
    FROM family
    GROUP BY family_name
    HAVING COUNT(DISTINCT element) > 1
)
SELECT s.family_name, s.socket_idx, s.label
FROM socket s
JOIN (SELECT DISTINCT family_name, slot_order, wtype FROM family) f
    ON f.family_name = s.family_name
ORDER BY f.slot_order, f.wtype, s.family_name, s.socket_idx
"""

# Every cell of Roll Quality's tables, in the report's order. Each family has a
# table per view of the wishlists: scope '*' counts every list's rolls, and
# when more than one list has rolls for the weapon, each list's own follow (its
# key as scope); shows lists the values of the wishlist switch a table answers
# ('*' for All lists, and the key of a list that is the only one). A table's
# rows are the Wishlist row (n 0) and each copy's (its n); a cell is a perk
# socket's slot there (socket_idx -1 is the Element column when copies differ
# in element). The Wishlist row holds the perks the view's rolls name in the
# weapons' perk pool, those more lists name first, then those more rolls name
# (state pick; lists names the lists). A copy's row puts its perk of the same
# name under each, or a blank (NULL perk), then its other perks in the game's
# order, gap marking the first of them; state is hit for a perk in a roll of
# the view the copy completes, named for one the view's rolls name, '' for
# the rest. rings gives the places (in wishlist_preference's order, 1 first)
# of the lists whose colours a pick or a hit or named perk's ring shows, like
# '1-3': in the view, the lists naming a pick or named perk, those with a roll
# the copy completes naming a hit. faded is 1 when copy #1 has the perk too.
# score is the rolls of the view the copy completes, NULL in '*' when no
# wishlist covers the weapon. text is the perk's description, Clarity's when it
# has one, else Bungie's.
ROLL_CELLS = f"""
WITH copy AS ({COPIES}),
family AS MATERIALIZED (SELECT * FROM copy),
copy_perk AS MATERIALIZED (
    SELECT f.family_name, f.instance_id, f.n, r.socket_idx, r.perk, r.plug_hash,
           MIN(r.position) AS position
    FROM v_weapon_roll r
    JOIN family f ON f.instance_id = r.instance_id
    GROUP BY f.instance_id, r.socket_idx, r.perk
),
pool AS MATERIALIZED (
    SELECT family_name, socket_idx, perk, plug_hash, MIN(position) AS position
    FROM (
        SELECT f.family_name, p.socket_idx, p.perk, p.plug_hash, p.position
        FROM v_weapon_pool p
        JOIN (SELECT DISTINCT family_name, item_hash FROM family) f ON f.item_hash = p.item_hash
        WHERE p.can_roll AND EXISTS (
            SELECT 1 FROM copy_perk cp
            WHERE cp.family_name = f.family_name AND cp.socket_idx = p.socket_idx)
        UNION ALL
        SELECT family_name, socket_idx, perk, plug_hash, NULL FROM copy_perk
    )
    GROUP BY family_name, socket_idx, perk
),
named AS MATERIALIZED (
    SELECT DISTINCT f.family_name, w.source_key, w.roll_id, d.name AS perk
    FROM (SELECT DISTINCT family_name, item_hash FROM family) f
    JOIN wishlist_roll w
        ON w.item_hash IN (f.item_hash, {models.WILDCARD_ITEM_HASH}) AND NOT w.is_trash
    JOIN DestinyInventoryItemDefinition d
        ON d.hash IN (w.perk1, w.perk2, w.perk3, w.perk4, w.perk5, w.perk6)
),
completed AS MATERIALIZED (
    SELECT m.instance_id, w.source_key, w.roll_id
    FROM family f
    JOIN instance_wishlist_match m ON m.instance_id = f.instance_id
    JOIN wishlist_roll w ON w.roll_id = m.roll_id AND NOT w.is_trash
),
hit AS MATERIALIZED (
    SELECT DISTINCT c.instance_id, c.source_key, d.name AS perk
    FROM completed c
    JOIN wishlist_roll w ON w.roll_id = c.roll_id
    JOIN DestinyInventoryItemDefinition d
        ON d.hash IN (w.perk1, w.perk2, w.perk3, w.perk4, w.perk5, w.perk6)
),
list AS MATERIALIZED (
    SELECT key, ROW_NUMBER() OVER (ORDER BY rowid) AS place FROM wishlist_preference
),
covered AS MATERIALIZED (
    SELECT DISTINCT n.family_name, n.source_key AS scope, l.rowid AS ord
    FROM named n
    JOIN wishlist_preference l ON l.key = n.source_key
),
scope AS MATERIALIZED (
    SELECT f.family_name, '*' AS scope, 0 AS ord,
           '*' || CASE WHEN COUNT(c.scope) = 1 THEN ' ' || MIN(c.scope) ELSE '' END AS shows
    FROM (SELECT DISTINCT family_name FROM family) f
    LEFT JOIN covered c ON c.family_name = f.family_name
    GROUP BY f.family_name
    UNION ALL
    SELECT family_name, scope, ord, scope
    FROM covered
    WHERE family_name IN (SELECT family_name FROM covered GROUP BY family_name HAVING COUNT(*) > 1)
),
pick AS MATERIALIZED (
    SELECT s.family_name, s.scope, p.socket_idx, p.perk, p.plug_hash,
           ROW_NUMBER() OVER (
               PARTITION BY s.family_name, s.scope, p.socket_idx
               ORDER BY COUNT(DISTINCT n.source_key) DESC, COUNT(DISTINCT n.roll_id) DESC, p.perk
           ) AS slot,
           COUNT(*) OVER (PARTITION BY s.family_name, s.scope, p.socket_idx) AS picks
    FROM scope s
    JOIN pool p ON p.family_name = s.family_name
    JOIN named n ON n.family_name = s.family_name AND n.perk = p.perk
                AND (s.scope = '*' OR n.source_key = s.scope)
    GROUP BY s.family_name, s.scope, p.socket_idx, p.perk
),
picks AS MATERIALIZED (
    SELECT DISTINCT family_name, scope, socket_idx, picks FROM pick
),
pick_rings AS MATERIALIZED (
    SELECT pk.family_name, pk.scope, pk.perk, group_concat(l.place, '-' ORDER BY l.place) AS rings
    FROM (SELECT DISTINCT family_name, scope, perk FROM pick) pk
    JOIN (SELECT DISTINCT family_name, source_key, perk FROM named) n
        ON n.family_name = pk.family_name AND n.perk = pk.perk
       AND (pk.scope = '*' OR n.source_key = pk.scope)
    JOIN list l ON l.key = n.source_key
    GROUP BY pk.family_name, pk.scope, pk.perk
),
hit_rings AS MATERIALIZED (
    SELECT s.scope, h.instance_id, h.perk, group_concat(l.place, '-' ORDER BY l.place) AS rings
    FROM hit h
    JOIN family f ON f.instance_id = h.instance_id
    JOIN scope s ON s.family_name = f.family_name AND (s.scope = '*' OR h.source_key = s.scope)
    JOIN list l ON l.key = h.source_key
    GROUP BY s.scope, h.instance_id, h.perk
),
slot AS MATERIALIZED (
    SELECT f.family_name, pk.scope, f.instance_id, f.n, pk.socket_idx, pk.slot, cp.perk,
           cp.plug_hash, 1 AS named, 0 AS gap
    FROM family f
    JOIN pick pk ON pk.family_name = f.family_name
    LEFT JOIN copy_perk cp
        ON cp.instance_id = f.instance_id AND cp.socket_idx = pk.socket_idx AND cp.perk = pk.perk
    UNION ALL
    SELECT family_name, scope, instance_id, n, socket_idx, picks + k, perk, plug_hash, 0,
           k = 1 AND picks > 0
    FROM (
        SELECT f.family_name, s.scope, f.instance_id, f.n, cp.socket_idx, cp.perk, cp.plug_hash,
               COALESCE(ps.picks, 0) AS picks,
               ROW_NUMBER() OVER (
                   PARTITION BY s.scope, f.instance_id, cp.socket_idx ORDER BY cp.position, cp.perk
               ) AS k
        FROM family f
        JOIN scope s ON s.family_name = f.family_name
        JOIN copy_perk cp ON cp.instance_id = f.instance_id
        LEFT JOIN pick pk
            ON pk.family_name = s.family_name AND pk.scope = s.scope
           AND pk.socket_idx = cp.socket_idx AND pk.perk = cp.perk
        LEFT JOIN picks ps
            ON ps.family_name = s.family_name AND ps.scope = s.scope
           AND ps.socket_idx = cp.socket_idx
        WHERE pk.perk IS NULL
    )
),
lists AS MATERIALIZED (
    SELECT family_name, perk, group_concat(label, ', ' ORDER BY ord) AS lists
    FROM (
        SELECT DISTINCT n.family_name, n.perk, l.label, l.rowid AS ord
        FROM named n
        JOIN wishlist_preference l ON l.key = n.source_key
    )
    GROUP BY family_name, perk
),
first AS MATERIALIZED (
    SELECT family_name, socket_idx, perk FROM copy_perk WHERE n = 1
),
score AS MATERIALIZED (
    SELECT s.family_name, s.scope, f.instance_id,
           CASE WHEN s.scope <> '*' THEN (
                    SELECT COUNT(*) FROM completed c
                    WHERE c.instance_id = f.instance_id AND c.source_key = s.scope)
                WHEN f.has_wishlist THEN f.match_count
           END AS score
    FROM scope s
    JOIN family f ON f.family_name = s.family_name
),
cell AS (
    SELECT pk.family_name, pk.scope, 0 AS n, pk.socket_idx, pk.slot, pk.perk, pk.plug_hash,
           'pick' AS state, pr.rings, 0 AS faded, 0 AS gap, NULL AS score, ls.lists
    FROM pick pk
    LEFT JOIN lists ls ON ls.family_name = pk.family_name AND ls.perk = pk.perk
    LEFT JOIN pick_rings pr
        ON pr.family_name = pk.family_name AND pr.scope = pk.scope AND pr.perk = pk.perk
    UNION ALL
    SELECT sl.family_name, sl.scope, sl.n, sl.socket_idx, sl.slot, sl.perk, sl.plug_hash,
           CASE WHEN sl.perk IS NULL THEN NULL
                WHEN NOT sl.named THEN ''
                WHEN hr.rings IS NOT NULL THEN 'hit'
                ELSE 'named'
           END,
           CASE WHEN sl.named THEN COALESCE(hr.rings, pr.rings) END,
           sl.n > 1 AND t.perk IS NOT NULL, sl.gap, sc.score, NULL
    FROM slot sl
    JOIN score sc
        ON sc.family_name = sl.family_name AND sc.scope = sl.scope
       AND sc.instance_id = sl.instance_id
    LEFT JOIN first t
        ON t.family_name = sl.family_name AND t.socket_idx = sl.socket_idx AND t.perk = sl.perk
    LEFT JOIN hit_rings hr
        ON hr.scope = sl.scope AND hr.instance_id = sl.instance_id AND hr.perk = sl.perk
    LEFT JOIN pick_rings pr
        ON pr.family_name = sl.family_name AND pr.scope = sl.scope AND pr.perk = sl.perk
    UNION ALL
    SELECT f.family_name, sc.scope, f.n, -1, 1, f.element, NULL, '', NULL,
           f.n > 1 AND f.element = t.element, 0, sc.score, NULL
    FROM family f
    JOIN score sc ON sc.family_name = f.family_name AND sc.instance_id = f.instance_id
    JOIN family t ON t.family_name = f.family_name AND t.n = 1
    WHERE f.family_name IN (
        SELECT family_name FROM family GROUP BY family_name HAVING COUNT(DISTINCT element) > 1)
)
SELECT c.family_name, c.scope, s.shows, c.n, c.socket_idx, c.slot, c.perk, c.plug_hash,
       CASE WHEN c.socket_idx = -1 THEN e.element_icon ELSE pl.icon END AS icon,
       COALESCE(cn.text, pl.description, '') AS text,
       c.state, c.rings, c.faded, c.gap, c.score, c.lists
FROM cell c
JOIN scope s ON s.family_name = c.family_name AND s.scope = c.scope
JOIN (SELECT DISTINCT family_name, slot_order, wtype FROM family) f
    ON f.family_name = c.family_name
LEFT JOIN family e ON c.socket_idx = -1 AND e.family_name = c.family_name AND e.n = c.n
LEFT JOIN v_plug pl ON pl.hash = c.plug_hash
LEFT JOIN clarity_note cn ON cn.plug_hash = c.plug_hash
ORDER BY f.slot_order, f.wtype, c.family_name, s.ord, c.n, c.socket_idx, c.slot
"""

# The Armor 3.0 Legendary pieces, every gear tier, by class, set (grade, then
# rank within it) and slot, each slot's copies best score first: the set cards.
# tier_overlay is the gear tier's pip image ('' without one).
# tuning lists a piece's tuning stats (comma-separated stat keys), builds the
# builds it is kept for (stat keys, builds separated by ';'). purge counts the
# set's pieces to purge (rescued ones stay), flagged those to purge or kept
# for a build.
SET_PIECES = f"""
WITH tuning AS (
    SELECT instance_id, group_concat(stat, ',' ORDER BY stat) AS stats
    FROM v_armor_tuning
    GROUP BY instance_id
),
rescue AS (
    SELECT instance_id, group_concat(stat_1 || ',' || stat_2 || ',' || stat_3, ';') AS builds
    FROM armor_rescue
    GROUP BY instance_id
)
SELECT a.instance_id, a.armor_class, a.set_name, a.slot, a.name, a.icon, a.watermark,
       a.gear_tier, COALESCE(gt.url, '') AS tier_overlay,
       a.health, a.melee, a.grenade, a.super_stat, a.class_stat, a.weapons,
       s.preferred_score AS score, s.best_tuning, s.tuning_gain, t.stats AS tuning, r.builds,
       g.grade, g.label AS grade_label, g.slot_cap, p.rank, p.stat_1, p.stat_2, p.stat_3,
       pr.reason, pr.keeper_id, COALESCE(pr.rescued, 0) AS rescued,
       COUNT(*) OVER set_pieces AS copies,
       SUM(pr.reason IS NOT NULL AND NOT pr.rescued) OVER set_pieces AS purge,
       COUNT(pr.reason) OVER set_pieces AS flagged
FROM v_armor a
JOIN armor_score s ON s.instance_id = a.instance_id
JOIN ({CLASS_N}) c ON c.armor_class = a.armor_class
LEFT JOIN armor_preference p ON p.name = a.set_name COLLATE NOCASE
JOIN armor_grade g ON g.grade = COALESCE(p.grade, '')
LEFT JOIN v_armor_pruning pr ON pr.instance_id = a.instance_id
LEFT JOIN tuning t ON t.instance_id = a.instance_id
LEFT JOIN rescue r ON r.instance_id = a.instance_id
LEFT JOIN v_gear_tier gt ON gt.tier = a.gear_tier
WHERE NOT a.is_exotic
WINDOW set_pieces AS (PARTITION BY a.armor_class, a.set_name)
ORDER BY c.class_n, g.position, p.rank, a.set_name, a.slot_order, s.preferred_score DESC,
         a.instance_id
"""

# The Legendary pieces from before Armor 3.0 (always purged), by class and
# slot.
LEGACY = f"""
SELECT a.instance_id, a.armor_class, a.name, a.slot, a.set_name,
       a.health, a.melee, a.grenade, a.super_stat, a.class_stat, a.weapons
FROM v_armor_pruning p
JOIN v_armor a ON a.instance_id = p.instance_id
JOIN ({CLASS_N}) c ON c.armor_class = a.armor_class
WHERE p.reason = 'legacy'
ORDER BY c.class_n, a.slot_order, a.set_name, a.name, a.instance_id
"""

# The three-stat builds the kept armor leaves short of 100 in some stat, by
# class, shortest first.
SHORT_BUILDS = f"""
SELECT DISTINCT r.armor_class, r.stat_1, r.stat_2, r.stat_3, r.total_1, r.total_2, r.total_3,
       MIN(r.total_1, r.total_2, r.total_3) AS low
FROM v_armor_reach r
JOIN ({CLASS_N}) c ON c.armor_class = r.armor_class
WHERE MIN(r.total_1, r.total_2, r.total_3) < 100
ORDER BY c.class_n, low, r.stat_1, r.stat_2, r.stat_3
"""

# The pieces kept past their set's cap for a build, by class and build.
RESCUES = f"""
SELECT r.stat_1, r.stat_2, r.stat_3, r.new_min, a.instance_id, a.armor_class, a.name,
       a.slot, a.set_name, COALESCE(p.grade, '') AS grade
FROM armor_rescue r
JOIN v_armor a ON a.instance_id = r.instance_id
JOIN ({CLASS_N}) c ON c.armor_class = a.armor_class
LEFT JOIN armor_preference p ON p.name = a.set_name COLLATE NOCASE
ORDER BY c.class_n, r.stat_1, r.stat_2, r.stat_3, a.slot_order, a.instance_id
"""

# The exotics with copies to purge: each kept copy (keeper) with the copies it
# beat, by class, slot and name, then best score first. tie marks a purged
# copy that scores the same as its keeper.
EXOTIC_DUPES = f"""
WITH perks AS (
    SELECT instance_id, group_concat(perk, ' + ' ORDER BY perk) AS names
    FROM v_armor_perk
    GROUP BY instance_id
)
SELECT a.instance_id, a.armor_class, a.name, a.slot, a.icon, a.watermark, a.gear_tier,
       a.health, a.melee, a.grenade, a.super_stat, a.class_stat, a.weapons,
       s.preferred_score AS score,
       CASE WHEN a.slot = 'Class Armor' THEN k.names END AS perks,
       p.stat_1, p.stat_2, p.stat_3, pr.reason,
       COALESCE(pr.keeper_id, a.instance_id) AS keeper_id,
       COALESCE(ks.preferred_score = s.preferred_score, 0) AS tie
FROM v_armor a
JOIN armor_score s ON s.instance_id = a.instance_id
JOIN ({CLASS_N}) c ON c.armor_class = a.armor_class
LEFT JOIN v_armor_pruning pr ON pr.instance_id = a.instance_id
LEFT JOIN armor_score ks ON ks.instance_id = pr.keeper_id
LEFT JOIN armor_preference p ON p.name = a.name COLLATE NOCASE
LEFT JOIN perks k ON k.instance_id = a.instance_id
WHERE a.is_exotic AND (pr.reason = 'exotic_dupe' OR a.instance_id IN (
    SELECT keeper_id FROM v_armor_pruning WHERE reason = 'exotic_dupe'))
ORDER BY c.class_n, a.slot_order, lower(a.name), COALESCE(pr.keeper_id, a.instance_id),
         s.preferred_score DESC, a.instance_id
"""

# Every armor set's bonuses, 2-piece first: Bungie's name, text and icon for
# each, by set name.
SET_BONUSES = """
SELECT DISTINCT s.name AS set_name, sp.value ->> 'requiredSetCount' AS pieces, sb.name,
       COALESCE(sb.description, '') AS description,
       CASE WHEN COALESCE(sb.icon, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || sb.icon END AS icon
FROM DestinyEquipableItemSetDefinition s
CROSS JOIN json_each(s.setPerks) sp
CROSS JOIN DestinySandboxPerkDefinition sb ON sb.hash = sp.value ->> 'sandboxPerkHash'
ORDER BY s.name, pieces
"""

# Every armor set preference as stored: by grade (S first, unclassified last),
# rank within the grade, then name. set_name and set_hash are the armor set of
# that name, NULL when the manifest has none.
SET_PREFERENCES = """
WITH armor_set AS (
    SELECT lower(name) AS name, MIN(name) AS set_name, MIN(hash) AS set_hash
    FROM DestinyEquipableItemSetDefinition
    GROUP BY lower(name)
)
SELECT p.name, p.stat_1, p.stat_2, p.stat_3, p.grade, g.label AS grade_label,
       a.set_name, a.set_hash
FROM armor_preference p
LEFT JOIN armor_grade g ON g.grade = p.grade
LEFT JOIN armor_set a ON a.name = lower(p.name)
WHERE NOT p.is_exotic
ORDER BY g.position NULLS LAST, p.rank, p.name COLLATE NOCASE
"""

# Each armor set's badges, one per class in the class switches' order: the
# icon and watermark of its helmet, else of its first piece by slot.
SET_BADGES = f"""
WITH piece AS (
    SELECT d.equipableItemSetHash AS set_hash, k.name AS armor_class, c.class_n, d.icon,
           d.iconWatermark,
           ROW_NUMBER() OVER (
               PARTITION BY d.equipableItemSetHash, d.classType ORDER BY b.bucketOrder, d.hash
           ) AS n
    FROM DestinyInventoryItemDefinition d
    JOIN DestinyInventoryBucketDefinition b ON b.hash = d.bucketTypeHash
    JOIN DestinyClassDefinition k ON k.classType = d.classType
    LEFT JOIN ({CLASS_N}) c ON c.armor_class = k.name
    WHERE d.itemType = 2 AND d.equipableItemSetHash IS NOT NULL AND COALESCE(d.icon, '') <> ''
)
SELECT set_hash, armor_class, 'https://www.bungie.net' || icon AS icon,
       CASE WHEN COALESCE(iconWatermark, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || iconWatermark END AS watermark
FROM piece
WHERE n = 1
ORDER BY set_hash, class_n NULLS LAST, armor_class
"""

# Every exotic preference as stored, by class (in the class switches' order)
# and name. The rest comes from the exotic armor of that name in the manifest,
# its Armor 3.0 version (the one with a tuning socket) when it has one:
# armor_class, item_hash, icon and watermark for its badge, and its exotic perk
# (the first named plug in an intrinsic or exotic socket) with Clarity's text,
# else Bungie's. Each is NULL when the manifest has no exotic of that name.
EXOTIC_PREFERENCES = f"""
WITH version AS (
    SELECT lower(d.name) AS name, k.name AS armor_class, d.hash, d.icon, d.iconWatermark,
           ROW_NUMBER() OVER (
               PARTITION BY lower(d.name)
               ORDER BY EXISTS (
                   SELECT 1 FROM json_each(d.socketEntries) e
                   CROSS JOIN DestinyInventoryItemDefinition t
                       ON t.hash = e.value ->> 'singleInitialItemHash'
                   WHERE t.plugCategoryIdentifier
                         = 'core.gear_systems.armor_tiering.plugs.tuning.mods'
               ) DESC, d.hash
           ) AS n
    FROM DestinyInventoryItemDefinition d
    JOIN DestinyClassDefinition k ON k.classType = d.classType
    WHERE d.itemType = 2 AND d.tierType = 6
),
perk AS (
    SELECT d.hash AS itemHash, t.hash, t.name, t.description,
           ROW_NUMBER() OVER (PARTITION BY d.hash ORDER BY e.key) AS n
    FROM DestinyInventoryItemDefinition d
    CROSS JOIN json_each(d.socketEntries) e
    CROSS JOIN DestinyInventoryItemDefinition t ON t.hash = e.value ->> 'singleInitialItemHash'
    WHERE t.name <> '' AND (t.plugCategoryIdentifier = 'intrinsics'
                            OR t.plugCategoryIdentifier LIKE 'enhancements.exotic%')
)
SELECT p.name, p.stat_1, p.stat_2, p.stat_3, v.armor_class, v.hash AS item_hash,
       CASE WHEN COALESCE(v.icon, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || v.icon END AS icon,
       CASE WHEN COALESCE(v.iconWatermark, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || v.iconWatermark END AS watermark,
       pk.name AS perk, COALESCE(cn.text, pk.description, '') AS perk_text
FROM armor_preference p
LEFT JOIN version v ON v.name = lower(p.name) AND v.n = 1
LEFT JOIN perk pk ON pk.itemHash = v.hash AND pk.n = 1
LEFT JOIN clarity_note cn ON cn.plug_hash = pk.hash
LEFT JOIN ({CLASS_N}) c ON c.armor_class = v.armor_class
WHERE p.is_exotic
ORDER BY c.class_n NULLS LAST, v.armor_class NULLS LAST, p.name COLLATE NOCASE
"""

# The wishlist sources every run downloads, in the order they were added: the
# defaults first.
WISHLISTS = "SELECT key, label, url FROM wishlist_preference ORDER BY rowid"


def load_set_bonuses(conn) -> dict:
    # {set name: [bonus]}, each bonus SET_BONUSES' columns plus aegis, The
    # Aegis's AegisBonus for the set and piece count, or None. Set names are
    # matched as aegis_rankings matches them, since the sheet spells some
    # differently ('Iron Battalion' for 'Iron Battalion Set').
    aegis = aegis_rankings.load(conn)
    bonuses = {}
    for r in conn.execute(SET_BONUSES):
        match = next(
            (
                b
                for b in aegis_rankings.get_aegis_bonuses(aegis, r['set_name'])
                if b.pieces == r['pieces']
            ),
            None,
        )
        bonuses.setdefault(r['set_name'], []).append({**dict(r), 'aegis': match})
    return bonuses


def load(conn) -> dict:
    # Everything the report shows, by the names the templates use.
    def rows(sql):
        return conn.execute(sql).fetchall()

    return {
        'totals': conn.execute(TOTALS).fetchone(),
        'sources': rows(SOURCES),
        'classes': rows(CLASSES),
        'grades': rows("SELECT grade, label, slot_cap FROM armor_grade ORDER BY position"),
        'armor_purge': rows(ARMOR_PURGE),
        'purge_counts': rows(PURGE_COUNTS),
        'weapon_flags': rows(WEAPON_FLAGS),
        'roll_quality': rows(ROLL_QUALITY),
        'roll_columns': rows(ROLL_COLUMNS),
        'roll_cells': rows(ROLL_CELLS),
        'set_pieces': rows(SET_PIECES),
        'legacy': rows(LEGACY),
        'short_builds': rows(SHORT_BUILDS),
        'rescues': rows(RESCUES),
        'exotic_dupes': rows(EXOTIC_DUPES),
        'set_bonuses': load_set_bonuses(conn),
        'set_preferences': rows(SET_PREFERENCES),
        'set_badges': rows(SET_BADGES),
        'exotic_preferences': rows(EXOTIC_PREFERENCES),
        'wishlists': rows(WISHLISTS),
        'stat_icons': dict(rows("SELECT key, icon FROM v_stat_icon")),
        'stat_names': dict(
            rows(
                "SELECT k.key, d.name FROM stat_key k "
                "JOIN DestinyStatDefinition d ON d.hash = k.statHash"
            )
        ),
        'text_icons': dict(rows("SELECT token, icon FROM v_text_icon")),
    }
