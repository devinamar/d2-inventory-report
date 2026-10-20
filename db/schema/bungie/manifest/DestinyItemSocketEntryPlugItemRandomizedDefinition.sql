-- The plugs of each plug set: DestinyPlugSetDefinition.reusablePlugItems, "a
-- list of pre-determined plugs that can be plugged into this socket, without
-- the character having the plug in their inventory. If this list is populated,
-- you will not be allowed to plug an arbitrary item in the socket: you will
-- only be able to choose from one of these reusable plugs." Bungie gives the
-- type no description of its own. Rows: each stored set's entries, in order;
-- an entry whose plug isn't a stored plug is left out. A set can list a plug
-- twice.
CREATE TABLE DestinyItemSocketEntryPlugItemRandomizedDefinition (
    -- The set whose reusablePlugItems this entry is in.
    plugSetHash       INTEGER NOT NULL REFERENCES DestinyPlugSetDefinition(hash) ON DELETE CASCADE,
    -- The entry's position in reusablePlugItems, from 0.
    position          INTEGER NOT NULL,
    -- "The hash identifier of a DestinyInventoryItemDefinition representing
    -- the plug that can be inserted."
    plugItemHash      INTEGER NOT NULL REFERENCES DestinyInventoryItemDefinition(hash),
    -- "Indicates if the plug can be rolled on the current version of the item.
    -- For example, older versions of weapons may have plug rolls that are no
    -- longer possible on the current versions." 1 or 0.
    currentlyCanRoll  INTEGER,
    PRIMARY KEY (plugSetHash, position)
);
