-- DestinyItemInvestmentStatDefinition: "Represents a "raw" investment stat,
-- before calculated stats are calculated and before any
-- DestinyStatGroupDefinition is applied to transform the stat into something
-- closer to what you see in-game. Because these won't match what you see in-
-- game, consider carefully whether you really want to use these stats. I have
-- left them in case someone can do something useful or interesting with the
-- pre-processed statistics." Rows: the investmentStats of each plug in
-- DestinyInventoryItemDefinition ("If the item has stats, this block will be
-- defined. It has the "raw" investment stats for the item."), in order. Armor
-- stat and tuning plugs have them.
CREATE TABLE DestinyItemInvestmentStatDefinition (
    -- The plug whose investmentStats this stat is in.
    itemHash      INTEGER NOT NULL
        REFERENCES DestinyInventoryItemDefinition(hash) ON DELETE CASCADE,
    -- The stat's position in investmentStats, from 0. A plug can list the same
    -- stat twice.
    position      INTEGER NOT NULL,
    -- "The hash identifier for the DestinyStatDefinition defining this stat."
    statTypeHash  INTEGER,
    -- "The raw "Investment" value for the stat, before transformations are
    -- performed to turn this raw stat into stats that are displayed in the
    -- game UI."
    value         INTEGER,
    PRIMARY KEY (itemHash, position)
);
