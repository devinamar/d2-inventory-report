-- DestinyItemReusablePlugsComponent (component 310). Bungie gives the
-- component no description; its plugs are "the list of plugs that are allowed
-- to be used for the socket, and any relevant information about whether they
-- are "enabled", whether they are allowed to be inserted". "KEY = The INDEX
-- into the item's list of sockets. VALUE = The set of plugs for that socket.
-- If a socket doesn't have any reusable plugs defined at the item scope, there
-- will be no entry for that socket." Rows: one per plug, a
-- DestinyItemPlugBase, in the game's order.
CREATE TABLE DestinyItemReusablePlugsComponent (
    -- The copy this plug belongs to.
    itemInstanceId  TEXT NOT NULL,
    -- The socket: the key of plugs.
    socketIndex     INTEGER NOT NULL,
    -- The plug's place in the game's list for the socket, from 0.
    position        INTEGER NOT NULL,
    -- "The hash identifier of the DestinyInventoryItemDefinition that
    -- represents this plug."
    plugItemHash    INTEGER NOT NULL REFERENCES DestinyInventoryItemDefinition(hash),
    -- "If true, this plug has met all of its insertion requirements. Big if
    -- true."
    canInsert       INTEGER,
    -- "If true, this plug will provide its benefits while inserted."
    enabled         INTEGER,
    PRIMARY KEY (itemInstanceId, socketIndex, position),
    FOREIGN KEY (itemInstanceId, socketIndex)
        REFERENCES DestinyItemSocketsComponent(itemInstanceId, socketIndex) ON DELETE CASCADE
);
