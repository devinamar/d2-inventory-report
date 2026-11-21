-- Each weapon copy left after pruning, with the card the weapons page shows it
-- on: the weapon d2-perk-popularity scores its version as (entry; a family
-- whose versions roll different trait pools is a card per pool), else its
-- family, for a version no scored weapon lists. card is the card's name, and
-- grid_id names its perk grid: the scored weapon's (v_popularity_version),
-- else the lowest version hash among the card's copies. k is the copy's place
-- in the card by instance id, and copies the card's number of copies. It reads
-- the copies' definitions, not v_weapon: SQLite inlines a view wherever it is
-- named, the grid queries name this one many times, and SQLite 3.54 refuses a
-- statement that opens 1000 cursors.
CREATE VIEW v_weapon_card AS
WITH copy AS (
    SELECT i.itemInstanceId AS instance_id, i.itemHash AS item_hash, w.family_name AS family,
           pv.name AS entry, COALESCE(pv.name, w.family_name) AS card, pv.grid_id
    FROM DestinyItemComponent i
    JOIN v_weapon_definition w ON w.item_hash = i.itemHash
    LEFT JOIN v_popularity_version pv ON pv.item_hash = i.itemHash
    WHERE i.itemInstanceId NOT IN (SELECT instance_id FROM weapon_pruning)
)
SELECT instance_id, item_hash, card, entry, family,
       COALESCE(MAX(grid_id) OVER (PARTITION BY card), MIN(item_hash) OVER (PARTITION BY card))
           AS grid_id,
       ROW_NUMBER() OVER (PARTITION BY card ORDER BY instance_id) AS k,
       COUNT(*) OVER (PARTITION BY card) AS copies
FROM copy;
