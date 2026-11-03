# Methodology

How the report decides what to dismantle, and how it ranks the rest. It reads your inventory
through Bungie's API, with player popularity from
[d2-perk-popularity](https://github.com/devinamar/d2-perk-popularity), three wishlists, and
optionally your DIM tags and notes.

## Weapons

Only two kinds of copy are flagged:

- **Below Legendary:** anything under Legendary.
- **True duplicates:** copies with the same family, element, archetype and roll. Perks are compared
  by name, so a reissue matches its original. The copy kept is the highest gear tier, then the one
  with the most wishlist matches.

Every other copy is shown on its weapon's card, ranked for PvE and PvP, for you to decide:

- **Popularity score (0 to 1):** the mean, over the weapon's scored columns, of the copy's best perk
  against the column's most-used perk. The two traits count as one column, scored by the copy's
  best trait pair, when the weapon has pair scores.
- **Order:** by score, then wishlist matches, then gear tier.
- **Endgame badge:** at least 50 of the weapon's voting copies on that side come from hard content,
  and at least 30% of them.
- **Wishlists:** Voltron, Aegis Endgame and the Aegis Shopping List, plus your own
  (`--add-wishlist`). A copy's matches are the non-trash wishlist rolls it can equip.

Each card's perk grid lists what the weapon can roll, by popularity. Once a family has 100
effective votes in a column, only perks players were seen with are listed, since the manifest
includes some that never drop; perks late in a plug set need only 30. Trait rows under 30% of their
column's top recede unless you own them, a wishlist picks them, or they're in a top pair.

## Armor

Armor 3.0 (gear tiers, set bonuses and tuning) is scored; anything older is legacy.

**Preferences.** Each set and exotic has up to three priority stats, and each set a grade from S to
F with a rank inside it (`--edit-armor-prefs`, with the Aegis set-bonus rankings beside each set).
The grade caps how many copies of each slot the set keeps, per class:

| Grade | S | A | B | C to F, or none |
| --- | --- | --- | --- | --- |
| Copies per slot | 4 | 2 | 2 | 1 |

**Score.** Three times the first priority stat, twice the second, plus the third (the stat total
without picks), at the piece's best spread for those stats: each tuning swap (+5 to one stat, −5
from another), with the masterwork's +5 to each zero stat. Exotics, and pieces below gear tier 5,
score as they are.

**Flagged**, in this order:

1. **Legacy:** a non-exotic piece from before Armor 3.0.
2. **Duplicate stats and tuning:** the same class, slot, set, stats and tuning stat as an older
   copy, which stays.
3. **Low score:** past its set grade's cap in its class and slot, the best scores kept first.
4. **Extra exotic copies:** each exotic keeps its best copy on its stat picks; an exotic class item
   keeps one per perk pair.

**Rescue.** For each class, every three-stat build is checked on raw stats: where the kept armor
can't reach 100 in all three, the capped piece that gets there stays, or a pair from different
slots, the better set first. The Builds page lists the builds still short.
