# The shapes every phase shares: weapons, armor, DIM tags, wishlist rolls,
# Aegis rankings, armor preferences, and the analysis results the db stores.
import dataclasses


@dataclasses.dataclass
class PerkSocket:
    # One perk socket on a weapon copy and the names of every perk the copy can
    # equip in it, in the game's order (v_weapon_roll).
    kind: str  # 'barrel', 'magazine', 'stock', 'grip', 'trait', 'origin' or 'intrinsic'
    perks: list  # perk names


@dataclasses.dataclass
class WeaponInstance:
    # One weapon copy in your vault, as wishlist scoring reads it.
    instance_id: str
    item_hash: int
    roll: list  # [PerkSocket] in socket order: barrel, magazine, traits, origin, ...


# Armor stat names in canonical order (matches ArmorStats.as_tuple())
ARMOR_STAT_NAMES = ('health', 'melee', 'grenade', 'super_stat', 'class_stat', 'weapons')


ARMOR_STAT_SHORT = ('Hlt', 'Mel', 'Gre', 'Sup', 'Cls', 'Wep')


# Canonical internal-name -> short-label map (single source for reports + prefs UI)
ARMOR_STAT_SHORT_MAP = dict(zip(ARMOR_STAT_NAMES, ARMOR_STAT_SHORT, strict=True))


@dataclasses.dataclass
class ArmorStats:
    # The six armor stats, in canonical order: health, melee, grenade, super,
    # class, weapons.
    health: int = 0
    melee: int = 0
    grenade: int = 0
    super_stat: int = 0
    class_stat: int = 0
    weapons: int = 0

    def total(self) -> int:
        return (
            self.health
            + self.melee
            + self.grenade
            + self.super_stat
            + self.class_stat
            + self.weapons
        )

    def as_tuple(self) -> tuple:
        return (
            self.health,
            self.melee,
            self.grenade,
            self.super_stat,
            self.class_stat,
            self.weapons,
        )


@dataclasses.dataclass
class ArmorSetBonus:
    # An armor set's 2-piece and 4-piece bonuses, each perk's name and text.
    two_piece_bonus: str = ''
    four_piece_bonus: str = ''


@dataclasses.dataclass
class ExoticEffect:
    # An exotic armor piece's intrinsic perk (its build-defining effect).
    name: str = ''
    description: str = ''


@dataclasses.dataclass
class Armor:
    # An armor definition; each copy carries one, built from its row.
    name: str
    set_name: str
    set_bonus: ArmorSetBonus | None = None
    is_exotic: bool = False
    exotic_effect: ExoticEffect | None = None


@dataclasses.dataclass
class ArmorInstance:
    # One armor copy in your vault, as the armor analysis reads it.
    instance_id: str
    armor: Armor
    stats: ArmorStats
    gear_tier: int | None = None
    tuning_stats: tuple = ()  # the stats its tuning socket can raise, in stat order; () for none


@dataclasses.dataclass
class DIMAnnotation:
    # A user-supplied tag and/or notes for one item, fetched from DIM.
    tag: str | None = None
    notes: str | None = None


# DIM's wildcard item hash: the roll applies to any weapon that can roll its
# perks. Stored as-is; the scorer checks these rolls against every copy.
WILDCARD_ITEM_HASH = -69420


@dataclasses.dataclass
class WishlistRoll:
    # One wishlist roll for one weapon, stored as one wishlist_roll row. perks
    # are plug hashes in DIM's column order (barrel, magazine, trait 1, trait 2,
    # plus up to two extras); empty for a line naming no perks, which fits any
    # roll of the weapon. roll_id is the row id once stored, which copies'
    # matches refer to.
    item_hash: int
    roll_id: int = 0
    perks: tuple = ()  # tuple[plug_hash, ...] in file order
    tags: set = dataclasses.field(default_factory=set)  # {'pve', 'pvp', ...}
    is_trash: bool = False


@dataclasses.dataclass(frozen=True)
class AegisBonus:
    # One ranked set bonus from The Aegis's "Set Bonuses" sheet. A set's 2pc
    # and 4pc bonuses are ranked independently. Persisted as an aegis_bonus row.
    set_name: str  # sheet spelling
    pieces: int  # 2 or 4
    bonus_name: str
    source: str = ''  # activity / location the set drops from
    season: str = ''
    tags: tuple = ()  # ('survivability', 'damage', ...)
    trigger: str = ''  # cells may embed newlines
    effect: str = ''
    analysis: str = ''
    rank: int = 0  # 1 = best bonus overall
    grade: str = ''  # 'S'..'F'


@dataclasses.dataclass
class ArmorPreference:
    # Stat picks for one armor set or exotic, plus a set's grade and its rank
    # within the grade (1 comes first). Only the 1-3 explicit picks are
    # stored; full_priority() expands them to all six stats.
    stat_1: str | None = None
    stat_2: str | None = None
    stat_3: str | None = None
    grade: str = ''  # 'S'..'F'; '' for an exotic or a set not yet classified
    rank: int = 0  # 1 = first within the grade
    is_exotic: bool = False

    def picks(self) -> list:
        # Return only the explicitly-picked stats, in priority order (0-3 entries).
        return [s for s in (self.stat_1, self.stat_2, self.stat_3) if s]

    @property
    def specified(self) -> int:
        # Count of stats the user explicitly picked (0-3).
        return len(self.picks())

    def full_priority(self) -> list:
        # All six stats in priority order: the picks, then the rest in canonical
        # order.
        picks = self.picks()
        remaining = [s for s in ARMOR_STAT_NAMES if s not in picks]
        return picks + remaining


@dataclasses.dataclass
class InstanceWishlistScore:
    # One copy's wishlist score. match_count is how many non-trash wishlist
    # rolls (from every source) the copy can equip; higher ranks higher.
    # has_wishlist is False when no source covers the weapon at all.
    # matched_roll_ids are the wishlist_roll rows it matched, trash included,
    # which the report groups by source.
    match_count: int = 0
    has_wishlist: bool = False
    matched_roll_ids: tuple = ()  # tuple[int, ...]


@dataclasses.dataclass
class ArmorScore:
    # Per-piece score used to rank inside (class, slot, set) pruning buckets
    # and persisted to armor_score. Every exotic and every Armor 3.0 piece has
    # one; legacy Legendary pieces are always flagged and have none.
    instance_id: str
    preferred_score: float = 0.0  # 3*stat[pref1] + 2*stat[pref2] + stat[pref3] (ranking key)
    best_tuning: str = ''  # variant label that maximises preferred_score
    best_stats: tuple = (0, 0, 0, 0, 0, 0)  # that variant's stats, masterwork included
    tuning_gain: float = 0.0  # what best_tuning adds to the untuned piece's score
