-- DestinyEquipableItemSetDefinition: "Perks that are active only when you have
-- a certain number of set items equipped." An armor set with a set bonus; its
-- bonuses are in DestinyItemSetPerkDefinition. Rows kept: all.
CREATE TABLE DestinyEquipableItemSetDefinition (
    -- "The unique identifier for this entity. Guaranteed to be unique for the
    -- type of entity, but not globally. When entities refer to each other in
    -- Destiny content, it is this hash that they are referring to."
    hash  INTEGER PRIMARY KEY,
    -- displayProperties.name: the set's name. Bungie's documentation gives no
    -- description.
    name  TEXT
);
