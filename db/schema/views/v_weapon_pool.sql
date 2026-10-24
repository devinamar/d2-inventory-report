-- The perks each weapon definition can roll in each of its perk sockets: the
-- socket's plug set, randomized or fixed. can_roll is 0 for a perk the set
-- still lists but no longer drops; a perk the set lists twice can roll if
-- either entry can. position is its place in the set (the first, for a perk
-- listed twice), the order the game and DIM show the perks in. Compared with
-- v_weapon_roll, it shows where a copy's roll sits in what the weapon could have
-- rolled.
CREATE VIEW v_weapon_pool AS
SELECT d.hash AS item_hash, ds.key AS socket_idx, p.kind, p.name AS perk,
       p.hash AS plug_hash, MAX(COALESCE(e.value ->> 'currentlyCanRoll', 1)) AS can_roll,
       MIN(e.key) AS position
FROM DestinyInventoryItemDefinition d
CROSS JOIN json_each(d.socketEntries) ds
CROSS JOIN DestinyPlugSetDefinition ps
    ON ps.hash = COALESCE(ds.value ->> 'randomizedPlugSetHash', ds.value ->> 'reusablePlugSetHash')
CROSS JOIN json_each(ps.reusablePlugItems) e
CROSS JOIN v_plug p ON p.hash = e.value ->> 'plugItemHash'
WHERE d.itemType = 3 AND p.kind IS NOT NULL AND p.name != ''
GROUP BY d.hash, ds.key, p.hash;
