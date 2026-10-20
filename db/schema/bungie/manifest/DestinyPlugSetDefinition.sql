-- DestinyPlugSetDefinition: "Sometimes, we have large sets of reusable plugs
-- that are defined identically and thus can (and in some cases, are so large
-- that they *must*) be shared across the places where they are used. These are
-- the definitions for those reusable sets of plugs." A plug set is the list of
-- plugs one socket can hold, such as every barrel a weapon's barrel socket can
-- roll; its plugs are in DestinyItemSocketEntryPlugItemRandomizedDefinition.
-- Rows kept: the sets the stored sockets name. Observed 2026-10-14: the
-- manifest doesn't deduplicate plug sets. 424 lists appeared under two or more
-- hashes, often with one copy in use; each is kept under its own hash.
CREATE TABLE DestinyPlugSetDefinition (
    -- "The unique identifier for this entity. Guaranteed to be unique for the
    -- type of entity, but not globally. When entities refer to each other in
    -- Destiny content, it is this hash that they are referring to."
    hash  INTEGER PRIMARY KEY
);
