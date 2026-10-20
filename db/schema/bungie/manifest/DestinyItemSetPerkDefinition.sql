-- The bonuses of each armor set: DestinyEquipableItemSetDefinition.setPerks,
-- "The perks conferred by this set of armor pieces." Bungie gives the type no
-- description of its own. Rows: each set's setPerks, in order.
CREATE TABLE DestinyItemSetPerkDefinition (
    -- The set whose setPerks this bonus is in.
    equipableItemSetHash  INTEGER NOT NULL
        REFERENCES DestinyEquipableItemSetDefinition(hash) ON DELETE CASCADE,
    -- The bonus's position in setPerks, from 0.
    position              INTEGER NOT NULL,
    -- "The number of set pieces required to activate the perk." 2 or 4.
    requiredSetCount      INTEGER,
    -- "The perk this set confers." Its name and text are in
    -- DestinySandboxPerkDefinition.
    sandboxPerkHash       INTEGER,
    PRIMARY KEY (equipableItemSetHash, position)
);
