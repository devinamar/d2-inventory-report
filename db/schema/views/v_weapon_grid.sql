-- Every perk grid's rows, one per column and perk: a grid for each scored
-- weapon (v_popularity_version's grid_id), and for each card whose versions
-- no scored weapon lists (v_weapon_card). A grid's perks are what its versions
-- can roll (v_weapon_pool), the perks d2-perk-popularity saw in its columns
-- (a column the pool doesn't list, like an origin trait every weapon got),
-- and its copies' perks; own is 1 for a perk only a copy has. A non-trait
-- perk the pool lists is dropped when the family has popularity_rule's
-- seen_votes in that column and none of its copies was seen with it: the
-- manifest lists barrels and magazines that never drop on a weapon. col is the
-- column's key (v_weapon_pool's), col_order its first socket and label what
-- the weapon calls it. Per side (pve_, pvp_): share and rank (the published
-- ones), rel (share against the column's top; 0 for an unvoted perk, NULL when
-- the column has no scores on the side), heat (rel in tenths, 0 to 10), pos
-- (the perk's place in its column: by share, then the game's order), and quiet
-- (a trait below popularity_rule's quiet_rel of its column's top and not in
-- the side's top five pairs).
-- ponytail: one seen_votes cutoff for every column, so a real perk under
-- about 1% of a family's votes can hide too; raise it if one goes missing.
CREATE VIEW v_weapon_grid AS
WITH grid AS MATERIALIZED (
    SELECT DISTINCT grid_id, name AS entry, family FROM v_popularity_version
    UNION
    SELECT DISTINCT grid_id, NULL, family FROM v_weapon_card
    WHERE entry IS NULL AND grid_id NOT IN (SELECT grid_id FROM v_popularity_version)
),
version AS MATERIALIZED (
    SELECT grid_id, item_hash FROM v_popularity_version
    UNION
    SELECT grid_id, item_hash FROM v_weapon_card WHERE entry IS NULL
),
voted AS MATERIALIZED (
    SELECT side, name, col, perk, share, rank, rel FROM v_popularity_perk
),
seen AS MATERIALIZED (
    SELECT DISTINCT v.family, p.col, p.perk
    FROM voted p
    JOIN (SELECT DISTINCT name, family FROM v_popularity_version) v ON v.name = p.name
),
pool AS (
    SELECT v.grid_id, p.col, p.perk, MIN(p.position) AS position, MIN(p.socket_idx) AS socket_idx
    FROM version v
    JOIN v_weapon_pool p ON p.item_hash = v.item_hash
    WHERE p.can_roll AND p.kind != 'intrinsic'
    GROUP BY v.grid_id, p.col, p.perk
),
kept AS (
    SELECT po.grid_id, po.col, po.perk, po.position, po.socket_idx
    FROM pool po
    JOIN grid g ON g.grid_id = po.grid_id
    CROSS JOIN popularity_rule r
    LEFT JOIN v_popularity_family f ON f.family = g.family AND f.col = po.col
    LEFT JOIN seen s ON s.family = g.family AND s.col = po.col AND s.perk = po.perk
    WHERE po.col LIKE 'trait%' OR COALESCE(f.votes, 0) < r.seen_votes OR s.perk IS NOT NULL
),
owned AS (
    SELECT c.grid_id, k.col, k.perk, MIN(k.socket_idx) AS socket_idx
    FROM v_weapon_card c
    JOIN v_copy_perk k ON k.instance_id = c.instance_id
    GROUP BY c.grid_id, k.col, k.perk
),
cell AS MATERIALIZED (
    SELECT grid_id, col, perk, MIN(position) AS position, MIN(socket_idx) AS socket_idx,
           MIN(own) AS own
    FROM (
        SELECT grid_id, col, perk, position, socket_idx, 0 AS own FROM kept
        UNION ALL
        SELECT DISTINCT g.grid_id, p.col, p.perk, NULL, NULL, 0
        FROM grid g
        JOIN voted p ON p.name = g.entry
        UNION ALL
        SELECT grid_id, col, perk, NULL, socket_idx, 1 FROM owned
    )
    GROUP BY grid_id, col, perk
),
label AS (
    SELECT name, kind, MIN(label) AS label
    FROM v_plug
    WHERE kind IS NOT NULL AND name != ''
    GROUP BY name, kind
),
col AS (
    SELECT c.grid_id, c.col,
           COALESCE(MIN(c.socket_idx),
                    CASE c.col WHEN 'intrinsic' THEN 0 WHEN 'barrel' THEN 1 WHEN 'magazine' THEN 2
                               WHEN 'trait1' THEN 3 WHEN 'trait2' THEN 4 ELSE 8 END) AS col_order,
           CASE WHEN c.col LIKE 'trait%' THEN 'Trait ' || substr(c.col, 6)
                ELSE COALESCE(MIN(l.label), upper(substr(c.col, 1, 1)) || substr(c.col, 2)) END
               AS label
    FROM cell c
    LEFT JOIN label l ON l.name = c.perk AND l.kind = c.col
    GROUP BY c.grid_id, c.col
),
side (side) AS (
    VALUES ('pve'), ('pvp')
),
top_pair AS (
    SELECT side, name, 'trait1' AS col, trait1 AS perk FROM v_popularity_pair WHERE rank <= 5
    UNION
    SELECT side, name, 'trait2', trait2 FROM v_popularity_pair WHERE rank <= 5
),
scored AS (
    SELECT c.grid_id, c.col, c.perk, s.side, p.share, p.rank,
           CASE WHEN pc.col IS NULL THEN NULL ELSE COALESCE(p.rel, 0) END AS rel,
           c.col LIKE 'trait%' AND COALESCE(p.rel, 0) < r.quiet_rel AND t.perk IS NULL AS quiet,
           ROW_NUMBER() OVER (
               PARTITION BY c.grid_id, c.col, s.side
               ORDER BY p.share IS NULL, p.share DESC, c.position IS NULL, c.position, c.perk
           ) AS pos
    FROM cell c
    JOIN grid g ON g.grid_id = c.grid_id
    CROSS JOIN side s
    CROSS JOIN popularity_rule r
    LEFT JOIN v_popularity_column pc ON pc.side = s.side AND pc.name = g.entry AND pc.col = c.col
    LEFT JOIN voted p
        ON p.side = s.side AND p.name = g.entry AND p.col = c.col AND p.perk = c.perk
    LEFT JOIN top_pair t
        ON t.side = s.side AND t.name = g.entry AND t.col = c.col AND t.perk = c.perk
)
SELECT c.grid_id, c.col, k.col_order, k.label, c.perk, c.position, c.own,
       MAX(CASE WHEN r.side = 'pve' THEN r.share END) AS pve_share,
       MAX(CASE WHEN r.side = 'pve' THEN r.rank END) AS pve_rank,
       MAX(CASE WHEN r.side = 'pve' THEN r.rel END) AS pve_rel,
       MAX(CASE WHEN r.side = 'pve' THEN CAST(round(10 * r.rel) AS INTEGER) END) AS pve_heat,
       MAX(CASE WHEN r.side = 'pve' THEN r.pos END) AS pve_pos,
       MAX(CASE WHEN r.side = 'pve' THEN r.quiet END) AS pve_quiet,
       MAX(CASE WHEN r.side = 'pvp' THEN r.share END) AS pvp_share,
       MAX(CASE WHEN r.side = 'pvp' THEN r.rank END) AS pvp_rank,
       MAX(CASE WHEN r.side = 'pvp' THEN r.rel END) AS pvp_rel,
       MAX(CASE WHEN r.side = 'pvp' THEN CAST(round(10 * r.rel) AS INTEGER) END) AS pvp_heat,
       MAX(CASE WHEN r.side = 'pvp' THEN r.pos END) AS pvp_pos,
       MAX(CASE WHEN r.side = 'pvp' THEN r.quiet END) AS pvp_quiet
FROM cell c
JOIN col k ON k.grid_id = c.grid_id AND k.col = c.col
JOIN scored r ON r.grid_id = c.grid_id AND r.col = c.col AND r.perk = c.perk
GROUP BY c.grid_id, c.col, c.perk;
