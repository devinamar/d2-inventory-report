-- The perks each weapon copy can equip in each of its perk sockets: the roll's
-- potential, which wishlist scoring and the duplicate checks compare. A perk
-- socket's plug is a barrel, magazine, stock, grip, trait or origin (its kind
-- in v_plug), or an intrinsic the copy can switch (Ergo Sum). Its perks are
-- the plugs it can switch to (component 310) in the same category, in the
-- game's order, plus the plugged one when the game doesn't list it.
CREATE VIEW v_weapon_roll AS
WITH perk_socket AS (
    SELECT s.itemInstanceId, s.socketIndex, s.plugHash, p.plugCategoryIdentifier, p.kind
    FROM DestinyItemSocketsComponent s
    JOIN DestinyItemComponent i ON i.itemInstanceId = s.itemInstanceId
    JOIN DestinyInventoryItemDefinition d ON d.hash = i.itemHash AND d.itemType = 3
    JOIN v_plug p ON p.hash = s.plugHash
    WHERE p.kind IS NOT NULL AND (p.kind != 'intrinsic' OR EXISTS (
        SELECT 1 FROM DestinyItemReusablePlugsComponent r
        WHERE r.itemInstanceId = s.itemInstanceId AND r.socketIndex = s.socketIndex))
),
perk AS (
    SELECT ps.itemInstanceId, ps.socketIndex, ps.kind, r.plugItemHash AS plugHash, r.position
    FROM perk_socket ps
    JOIN DestinyItemReusablePlugsComponent r
        ON r.itemInstanceId = ps.itemInstanceId AND r.socketIndex = ps.socketIndex
    JOIN DestinyInventoryItemDefinition p ON p.hash = r.plugItemHash
    WHERE p.plugCategoryIdentifier = ps.plugCategoryIdentifier
    UNION ALL
    SELECT ps.itemInstanceId, ps.socketIndex, ps.kind, ps.plugHash, -1
    FROM perk_socket ps
    WHERE NOT EXISTS (
        SELECT 1 FROM DestinyItemReusablePlugsComponent r
        WHERE r.itemInstanceId = ps.itemInstanceId AND r.socketIndex = ps.socketIndex
          AND r.plugItemHash = ps.plugHash)
)
SELECT pk.itemInstanceId AS instance_id, pk.socketIndex AS socket_idx, pk.kind,
       p.name AS perk, pk.plugHash AS plug_hash, MIN(pk.position) AS position
FROM perk pk
JOIN DestinyInventoryItemDefinition p ON p.hash = pk.plugHash
WHERE p.name != ''
GROUP BY pk.itemInstanceId, pk.socketIndex, pk.plugHash;
