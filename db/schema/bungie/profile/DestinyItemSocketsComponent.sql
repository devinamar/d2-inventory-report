-- DestinyItemSocketsComponent (component 305): "Instanced items can have
-- sockets, which are slots on the item where plugs can be inserted." Rows: one
-- per entry in sockets ("The list of all sockets on the item, and their status
-- information.") of each copy, a DestinyItemSocketState: "The status of a
-- given item's socket." socketIndex matches the definition's
-- DestinyItemSocketEntryDefinition rows.
CREATE TABLE DestinyItemSocketsComponent (
    -- The copy this socket belongs to.
    itemInstanceId  TEXT NOT NULL REFERENCES DestinyItemComponent(itemInstanceId) ON DELETE CASCADE,
    -- The socket's position in sockets, from 0.
    socketIndex     INTEGER NOT NULL,
    -- "The currently active plug, if any. Note that, because all plugs are
    -- statically defined, its effect on stats and perks can be statically
    -- determined using the plug item's definition." NULL for an empty socket,
    -- or a plug that isn't a stored plug.
    plugHash        INTEGER REFERENCES DestinyInventoryItemDefinition(hash),
    -- "Even if a plug is inserted, it doesn't mean it's enabled. This flag
    -- indicates whether the plug is active and providing its benefits."
    isEnabled       INTEGER,
    -- "A plug may theoretically provide benefits but not be visible - for
    -- instance, some older items use a plug's damage type perk to modify their
    -- own damage type. These, though they are not visible, still affect the
    -- item. This field indicates that state. An invisible plug, while it
    -- provides benefits if it is Enabled, cannot be directly modified by the
    -- user."
    isVisible       INTEGER,
    PRIMARY KEY (itemInstanceId, socketIndex)
);
