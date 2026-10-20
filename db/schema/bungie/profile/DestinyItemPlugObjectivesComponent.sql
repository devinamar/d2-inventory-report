-- DestinyItemPlugObjectivesComponent (component 309). Bungie gives the
-- component no description; its objectivesPerPlug "is keyed by the Item Hash
-- (DestinyInventoryItemDefinition) of the plug whose objectives are being
-- returned, with the value being the list of those objectives." "Sometimes,
-- Plugs may have objectives: generally, these are used for flavor and display
-- purposes. For instance, a Plug might be tracking the number of PVP kills you
-- have made." Rows: one per objective, a DestinyObjectiveProgress ("Returns
-- data about a character's status with a given Objective."). Kill trackers,
-- crafted weapon levels and memento progress are here.
CREATE TABLE DestinyItemPlugObjectivesComponent (
    -- The copy this objective belongs to.
    itemInstanceId   TEXT NOT NULL
        REFERENCES DestinyItemComponent(itemInstanceId) ON DELETE CASCADE,
    -- The plug: the key of objectivesPerPlug. It may be a plug the copy can
    -- switch to rather than the one plugged.
    plugHash         INTEGER NOT NULL REFERENCES DestinyInventoryItemDefinition(hash),
    -- "The unique identifier of the Objective being referred to. Use to look
    -- up the DestinyObjectiveDefinition in static data."
    objectiveHash    INTEGER NOT NULL REFERENCES DestinyObjectiveDefinition(hash),
    -- "If progress has been made, and the progress can be measured
    -- numerically, this will be the value of that progress." It "need not be a
    -- literal numeric progression. It could be one of a number of possible
    -- values, even a Timestamp. Always examine
    -- DestinyObjectiveDefinition.inProgressValueStyle or completedValueStyle
    -- before rendering progress." NULL when the profile sends none.
    progress         INTEGER,
    -- "As of Forsaken, objectives' completion value is determined dynamically
    -- at runtime. This value represents the threshold of progress you need to
    -- surpass in order for this objective to be considered "complete"."
    completionValue  INTEGER,
    -- "Whether or not the Objective is completed."
    complete         INTEGER,
    -- "If this is true, the objective is visible in-game. Otherwise, it's not
    -- yet visible to the player."
    visible          INTEGER,
    PRIMARY KEY (itemInstanceId, plugHash, objectiveHash)
);
