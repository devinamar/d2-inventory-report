-- The champion breaker each plug gives, from the perk of its own that names
-- one (DestinyInventoryItemDefinition.perks): every weapon's intrinsic frame
-- has one, like "[Stagger] Unstoppable", its token the breaker type (the text
-- writes Shield Piercing as [Shield-Piercing]) and then the champion. breaker
-- is the type's name (DestinyBreakerTypeDefinition: Stagger, Disruption,
-- Shield Piercing) and breaker_icon its icon, as a full URL. A plug naming
-- none has no row.
CREATE VIEW v_plug_breaker AS
SELECT d.hash AS plug_hash, bt.name AS breaker,
       'https://www.bungie.net' || bt.icon AS breaker_icon
FROM DestinyInventoryItemDefinition d
CROSS JOIN json_each(d.perks) p
CROSS JOIN DestinySandboxPerkDefinition sp ON sp.hash = p.value ->> 'perkHash'
JOIN DestinyBreakerTypeDefinition bt
    ON sp.name LIKE '[' || replace(bt.name, ' ', '-') || ']%';
