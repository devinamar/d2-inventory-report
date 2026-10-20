-- DestinyItemStatsComponent (component 304): "If you want the stats on an
-- item's instanced data, get this component. These are stats like Attack,
-- Defense etc... and *not* historical stats. Note that some stats have
-- additional computation in-game at runtime - for instance, Magazine Size -
-- and thus these stats might not be 100% accurate compared to what you see in-
-- game for some stats." Rows: one per entry in stats ("If the item has stats
-- that it provides (damage, defense, etc...), it will be given here.") of each
-- copy, such as a weapon's rounds per minute.
CREATE TABLE DestinyItemStatsComponent (
    -- The copy this stat belongs to.
    itemInstanceId  TEXT NOT NULL REFERENCES DestinyItemComponent(itemInstanceId) ON DELETE CASCADE,
    -- "The hash identifier for the Stat. Use it to look up the
    -- DestinyStatDefinition for static data about the stat."
    statHash        INTEGER NOT NULL REFERENCES DestinyStatDefinition(hash),
    -- "The current value of the Stat."
    value           INTEGER,
    PRIMARY KEY (itemInstanceId, statHash)
);
