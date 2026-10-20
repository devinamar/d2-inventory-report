-- The kill trackers on each weapon copy and the count each keeps. A copy can
-- switch between its trackers (Kill Tracker for enemies, Crucible Tracker for
-- players, a crafted weapon's memento tracker); each keeps its own count, and
-- is_plugged marks the one the game shows. Every tracker objective is an
-- Integer (inProgressValueStyle 6), so kills is a plain count. kind is what the
-- objective counts, as DIM reads it (its killTrackerObjectivesByHash): 'PvE',
-- 'PvP' or 'Gambit', NULL for one DIM doesn't count, such as a raid memento's.
-- icon is the objective's badge (a shield for enemies, crossed swords for
-- Crucible opponents) as a full URL.
CREATE VIEW v_kill_tracker AS
SELECT o.itemInstanceId AS instance_id, p.name AS tracker,
       CASE o.objectiveHash
           WHEN 90275515 THEN 'PvE' WHEN 2579044636 THEN 'PvE' WHEN 73837075 THEN 'PvE'
           WHEN 3387796140 THEN 'PvE'
           WHEN 1501870536 THEN 'PvP' WHEN 2439952408 THEN 'PvP' WHEN 74070459 THEN 'PvP'
           WHEN 890482414 THEN 'PvP' WHEN 2109364169 THEN 'PvP'
           WHEN 345540971 THEN 'Gambit'
       END AS kind,
       CASE WHEN COALESCE(ob.icon, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || ob.icon END AS icon,
       COALESCE(ob.progressDescription, '') AS description, COALESCE(o.progress, 0) AS kills,
       EXISTS (
           SELECT 1 FROM DestinyItemSocketsComponent s
           WHERE s.itemInstanceId = o.itemInstanceId AND s.plugHash = o.plugHash
       ) AS is_plugged
FROM DestinyItemPlugObjectivesComponent o
JOIN DestinyInventoryItemDefinition p ON p.hash = o.plugHash
JOIN DestinyObjectiveDefinition ob ON ob.hash = o.objectiveHash
WHERE p.plugCategoryIdentifier = 'v400.plugs.weapons.masterworks.trackers';
