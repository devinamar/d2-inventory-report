-- d2-perk-popularity's scores, one row per weapon and side, as perk_scores.json
-- publishes them: every weapon players finished activities with, ranked by
-- popularity. A weapon is its family: Adept, Timelost, Harrowed and reissued
-- versions count as one. Scores come from two groups, hard content and normal
-- content, scored apart and merged by credibility. Replaced wholesale by
-- extract/perk_popularity.py.
CREATE TABLE perk_popularity_weapon (
    side            TEXT NOT NULL,      -- 'pve' or 'pvp'
    name            TEXT NOT NULL,      -- the family's name
    type            TEXT NOT NULL,      -- the weapon type, like 'Shotgun'
    item_hash       INTEGER NOT NULL,   -- the version most of its copies are
    rank            INTEGER NOT NULL,   -- its place in the side's popularity, 1 first
    players         INTEGER NOT NULL,   -- copies voting, one vote per copy
    active_players  INTEGER NOT NULL,   -- those used within the window (window_days)
    hard            INTEGER NOT NULL,   -- 1 when hard content holds at least half its scores
    hard_weight     REAL NOT NULL,      -- hard content's part of its scores, 0 to 1
    last_seen       TEXT NOT NULL,      -- its newest use (ISO 8601, UTC)
    stale           INTEGER NOT NULL,   -- 1 when no copy was used within the window
    -- Each group's copies voting and their effective number of votes, as JSON:
    -- {"hard": {"copies", "n_eff"}, "normal": {"copies", "n_eff"}}.
    groups          TEXT NOT NULL,
    -- Its scored columns in socket order, as a JSON array; [] for a fixed roll
    -- (most exotics). Each column: kind (barrel, magazine, stock, grip, origin,
    -- or traits, both trait columns as one combo), n_eff (the merged score's
    -- effective number of votes), credibility (n_eff / (n_eff + credibility_k)),
    -- confidence ('high' from 100 votes, 'medium' from 30, 'low' from 10, else
    -- 'very low'), hard and normal ({n_eff, credibility}, null when that group
    -- has no votes there), and perks by share: perk (its name; an enhanced perk
    -- counts with its base, a traits perk is a combo like 'A + B'), share (of
    -- the column's votes, 0 to 1), low and high (its 95% Wilson range), and
    -- hard and normal (its share in each group, null without votes there).
    columns         TEXT NOT NULL,
    PRIMARY KEY (side, name)
);
