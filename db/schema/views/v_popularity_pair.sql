-- Every trait pair d2-perk-popularity scores (its traits column: "A + B", A
-- from the first trait socket), one row per side, weapon and pair: its share
-- of the weapon's pairs with its 95% range, its rank (1 for the most picked
-- pair), rel (its share against the top pair's), and for each of its traits
-- the pair's share among that trait's pairs (trait1_cond, trait2_cond: how
-- often the trait is run with this partner) and the partner's place among
-- them (trait1_n, trait2_n: 1 for the trait's most run partner). A weapon with
-- one trait socket scores single traits in that column, not pairs; they
-- aren't listed.
CREATE VIEW v_popularity_pair AS
WITH pair AS (
    SELECT w.side, w.name, p.key + 1 AS rank, p.value ->> 'share' AS share,
           p.value ->> 'low' AS low, p.value ->> 'high' AS high,
           substr(p.value ->> 'perk', 1, instr(p.value ->> 'perk', ' + ') - 1) AS trait1,
           substr(p.value ->> 'perk', instr(p.value ->> 'perk', ' + ') + 3) AS trait2
    FROM perk_popularity_weapon w
    CROSS JOIN json_each(w.columns) c
    CROSS JOIN json_each(c.value, '$.perks') p
    WHERE c.value ->> 'kind' = 'traits' AND instr(p.value ->> 'perk', ' + ') > 0
)
SELECT side, name, trait1, trait2, share, low, high, rank,
       share / MAX(share) OVER (PARTITION BY side, name) AS rel,
       share / SUM(share) OVER (PARTITION BY side, name, trait1) AS trait1_cond,
       share / SUM(share) OVER (PARTITION BY side, name, trait2) AS trait2_cond,
       ROW_NUMBER() OVER (PARTITION BY side, name, trait1 ORDER BY share DESC, rank) AS trait1_n,
       ROW_NUMBER() OVER (PARTITION BY side, name, trait2 ORDER BY share DESC, rank) AS trait2_n
FROM pair;
