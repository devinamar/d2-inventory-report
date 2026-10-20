-- One row per weapon copy, with its definition. family_name is the name without
-- " (Adept)", " (Timelost)" or " (Harrowed)", so special editions group with
-- the base weapon; slot is the name of the weapon's bucket and slot_order its
-- bucketOrder, Bungie's order for the buckets. The season comes from the
-- weapon's release traits (a '.season' trait first, then '.annual', then any
-- other, in release_tag_season); 0 and '' when none is known. source is where
-- it drops, as its collection entry says ('' when it has none, or when
-- Bungie's text there, "Random Perks: ...", names no place). ammo is the
-- weapon's ammo type (primary, special or heavy; '' when unknown) and
-- ammo_icon Bungie's badge for it. element is the copy's damage type, else the
-- weapon's default, and element_icon its icon; archetype is the intrinsic in
-- socket 0 (the starting one if the copy's has no name); rpm is the copy's
-- rounds-per-minute stat; tier is the tierType (5 is Legendary, 6 Exotic).
-- wtype_icon is the weapon type's picture: the icon of the Gunsmith Order
-- named after the type ("Hand Cannons"; "Bows" for a Combat Bow), '' when no
-- order has the name. tier_overlay is the pip image for the copy's gear tier,
-- and masterwork_overlay the gold border of a masterworked copy (the exotic
-- one for an exotic), from the constants table's one row; each '' when it has
-- none.
CREATE VIEW v_weapon AS
WITH by_trait AS (
    SELECT d.hash, r.season_num, r.season_name, r.season_date,
           ROW_NUMBER() OVER (PARTITION BY d.hash ORDER BY
               CASE WHEN t.value LIKE '%.season' THEN 0
                    WHEN t.value LIKE '%.annual' THEN 1
                    ELSE 2 END,
               t.key) AS n
    FROM DestinyInventoryItemDefinition d, json_each(d.traitIds) t
    JOIN release_tag_season r ON r.traitId = t.value
    WHERE d.itemType = 3
),
type_icon AS (
    SELECT name, MIN(icon) AS icon
    FROM DestinyInventoryItemDefinition
    WHERE itemTypeDisplayName = 'Gunsmith Order' AND icon <> ''
    GROUP BY name
)
SELECT i.itemInstanceId AS instance_id, i.itemHash AS item_hash,
       COALESCE(d.name, '') AS name,
       CASE WHEN substr(d.name, -8) = ' (Adept)'
                THEN trim(substr(d.name, 1, length(d.name) - 8))
            WHEN substr(d.name, -11) IN (' (Timelost)', ' (Harrowed)')
                THEN trim(substr(d.name, 1, length(d.name) - 11))
            ELSE COALESCE(d.name, '') END AS family_name,
       COALESCE(b.name, 'Unknown') AS slot, COALESCE(b.bucketOrder, 0) AS slot_order,
       COALESCE(d.itemTypeDisplayName, 'Unknown') AS wtype,
       COALESCE('https://www.bungie.net' || ti.icon, '') AS wtype_icon,
       COALESCE(d.tierType, 0) AS tier,
       CASE WHEN COALESCE(d.icon, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || d.icon END AS icon,
       CASE WHEN COALESCE(d.iconWatermark, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || d.iconWatermark END AS watermark,
       COALESCE(d.tierType, 0) = 6 AS is_exotic,
       COALESCE(NULLIF(c.sourceString,
           'Random Perks: This item cannot be reacquired from Collections.'), '') AS source,
       COALESCE(bt.season_num, 0) AS season_num,
       COALESCE(bt.season_name, '') AS season_name,
       COALESCE(bt.season_date, '') AS season_date,
       CASE d.ammoType WHEN 1 THEN 'primary' WHEN 2 THEN 'special' WHEN 3 THEN 'heavy'
            ELSE '' END AS ammo,
       COALESCE('https://www.bungie.net/img/destiny_content/ammo_types/'
                || CASE d.ammoType WHEN 1 THEN 'primary' WHEN 2 THEN 'special'
                                   WHEN 3 THEN 'heavy' END || '.png', '') AS ammo_icon,
       COALESCE(dt.name, wdt.name, 'Unknown') AS element,
       CASE WHEN COALESCE(dt.icon, wdt.icon, '') = '' THEN ''
            ELSE 'https://www.bungie.net' || COALESCE(dt.icon, wdt.icon) END AS element_icon,
       COALESCE(NULLIF(cp.name, ''), NULLIF(ip.name, ''), 'Unknown') AS archetype,
       COALESCE(NULLIF(cp.icon, ''), ip.icon, '') AS archetype_icon,
       COALESCE(st.value, 0) AS rpm,
       COALESCE(n.value, 0) AS power, n.gearTier AS gear_tier, i.state & 1 AS is_locked,
       (i.state & 4) > 0 AS is_masterworked, COALESCE(n.isEquipped, 0) AS is_equipped,
       COALESCE(gt.url, '') AS tier_overlay,
       CASE WHEN i.state & 4 THEN COALESCE('https://www.bungie.net' || NULLIF(
                CASE WHEN d.tierType = 6 THEN k.masterworkExoticBorderedOverlayPath
                     ELSE k.masterworkBorderedOverlayPath END, ''), '')
            ELSE '' END AS masterwork_overlay
FROM DestinyItemComponent i
JOIN DestinyInventoryItemDefinition d ON d.hash = i.itemHash AND d.itemType = 3
LEFT JOIN DestinyItemInstanceComponent n ON n.itemInstanceId = i.itemInstanceId
LEFT JOIN DestinyInventoryBucketDefinition b ON b.hash = d.bucketTypeHash
LEFT JOIN DestinyCollectibleDefinition c ON c.hash = d.collectibleHash
LEFT JOIN by_trait bt ON bt.hash = d.hash AND bt.n = 1
LEFT JOIN DestinyDamageTypeDefinition dt ON dt.hash = n.damageTypeHash
LEFT JOIN DestinyDamageTypeDefinition wdt ON wdt.hash = d.defaultDamageTypeHash
LEFT JOIN DestinyItemSocketsComponent s0
    ON s0.itemInstanceId = i.itemInstanceId AND s0.socketIndex = 0
LEFT JOIN v_plug cp ON cp.hash = s0.plugHash
LEFT JOIN DestinyItemSocketEntryDefinition ds0
    ON ds0.itemHash = i.itemHash AND ds0.socketIndex = 0
LEFT JOIN v_plug ip ON ip.hash = ds0.singleInitialItemHash
LEFT JOIN stat_key sk ON sk.key = 'rpm'
LEFT JOIN DestinyItemStatsComponent st
    ON st.itemInstanceId = i.itemInstanceId AND st.statHash = sk.statHash
LEFT JOIN type_icon ti ON ti.name = CASE d.itemTypeDisplayName
    WHEN 'Combat Bow' THEN 'Bows' ELSE d.itemTypeDisplayName || 's' END
LEFT JOIN v_gear_tier gt ON gt.tier = n.gearTier
LEFT JOIN DestinyInventoryItemConstantsDefinition k ON TRUE;
