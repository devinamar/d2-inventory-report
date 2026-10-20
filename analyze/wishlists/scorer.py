# Wishlist scoring: a copy's score (match_count) is how many non-trash
# wishlist rolls it can equip. A roll fits when each of its perks sits in a
# socket of the right kind on the copy, with the two trait perks in different
# trait sockets. Perks match by name, so reissued weapons with new perk hashes
# still match. Wildcard rolls (DIM's item=-69420) are checked against every
# copy, and a roll naming no perks (any roll of the weapon, or with
# item=-<hash> trash the whole weapon) fits every copy of its weapon. Matched
# trash rolls are recorded but don't add to the score.
import collections
import itertools

import models

# The perk kinds a roll is matched on. Origin traits, intrinsics and
# masterworks aren't.
SCORED_KINDS = ('barrel', 'magazine', 'stock', 'grip', 'trait')


# Load: the stored wishlist rolls and the plugs they name.


def row_perks(row) -> tuple:
    # Non-null perk1..perk6, in file order.
    return tuple(
        plug_hash for plug_hash in (row[f'perk{i}'] for i in range(1, 7)) if plug_hash is not None
    )


def load_wishlist(conn, source_key: str) -> dict:
    # {item_hash: [WishlistRoll]} for one source, in file order.
    rolls_by_item = {}
    for r in conn.execute(
        "SELECT * FROM wishlist_roll WHERE source_key = ? ORDER BY roll_id",
        (source_key,),
    ):
        rolls_by_item.setdefault(r['item_hash'], []).append(
            models.WishlistRoll(
                item_hash=r['item_hash'],
                roll_id=r['roll_id'],
                perks=row_perks(r),
                tags={t for t in r['tags'].split(',') if t},
                is_trash=bool(r['is_trash']),
            )
        )
    return rolls_by_item


def load_all(conn) -> dict:
    # {source_key: {item_hash: [WishlistRoll]}} for every source with rolls.
    rolls_by_source = {}
    for (source_key,) in conn.execute("SELECT key FROM wishlist_source ORDER BY key"):
        rolls_by_item = load_wishlist(conn, source_key)
        if rolls_by_item:
            rolls_by_source[source_key] = rolls_by_item
    return rolls_by_source


class PlugCatalog:
    # Every plug's name and kind (v_plug) in memory, for fast lookups by plug
    # hash during wishlist scoring. Unknown hashes give ''.

    def __init__(self, conn):
        # {plug_hash: row}
        self.plugs = {r['hash']: r for r in conn.execute("SELECT hash, name, kind FROM v_plug")}

    def field(self, plug_hash, column):
        plug = self.plugs.get(plug_hash)
        if plug:
            return plug[column]
        return ''

    def get_plug_name(self, plug_hash):
        return self.field(plug_hash, 'name')

    def get_plug_kind(self, plug_hash):
        return self.field(plug_hash, 'kind')


# Scoring: which rolls each copy can equip.


def classify_roll(roll, plugs) -> dict | None:
    # Convert a wishlist roll's perks into {kind: [name, ...]}: {} for a roll
    # naming no perks, which every copy fits. Returns None when the roll names
    # perks but none it can match (unknown hashes, or only origin traits,
    # catalysts and masterworks).
    if not roll.perks:
        return {}
    by_kind = collections.defaultdict(list)
    for ph in roll.perks:
        name = plugs.get_plug_name(ph)
        kind = plugs.get_plug_kind(ph)
        if name and kind in SCORED_KINDS:
            by_kind[kind].append(name)
    if by_kind:
        return dict(by_kind)
    return None


def copy_pools(instance) -> dict:
    # Per-kind list of per-socket name sets for one copy.
    # {'trait': [{socket 1 names}, {socket 2 names}], 'barrel': [{names}], 'magazine': [{names}]}
    pools = collections.defaultdict(list)
    for socket in instance.roll:
        if socket.kind in SCORED_KINDS:
            pools[socket.kind].append(set(socket.perks))
    return dict(pools)


def can_equip(roll_by_kind: dict, pools: dict) -> bool:
    # True when every perk in the roll fits a different socket of its kind on
    # the copy. Brute force over socket orders is fine: at most two trait
    # sockets, and one of each other kind.
    for kind, wanted in roll_by_kind.items():
        sockets = pools.get(kind, [])
        if len(wanted) > len(sockets):
            return False
        if not any(
            all(wanted[i] in sockets[idx[i]] for i in range(len(wanted)))
            for idx in itertools.permutations(range(len(sockets)), len(wanted))
        ):
            return False
    return True


def score_all_instances(all_instances: list, rolls_by_source: dict, plugs) -> dict:
    # {instance_id: InstanceWishlistScore} for every copy. rolls_by_source is
    # {source_key: {item_hash: [WishlistRoll]}} from load_all.
    if not rolls_by_source:
        return {}

    # Classify every roll once, trash included: trash matches don't score, but
    # the report flags the copies they fit. Rolls are bucketed by item_hash;
    # wildcard rolls are checked for every copy. A weapon any list mentions is
    # covered, whether or not its rolls can be scored.
    specific = collections.defaultdict(list)  # {item_hash: [(roll_id, is_trash, by_kind)]}
    wildcards = []  # [(roll_id, is_trash, by_kind)]
    covered = set()
    for rolls_by_item in rolls_by_source.values():
        for item_hash, rolls in rolls_by_item.items():
            if item_hash == models.WILDCARD_ITEM_HASH:
                bucket = wildcards
            else:
                covered.add(item_hash)
                bucket = specific[item_hash]
            for roll in rolls:
                by_kind = classify_roll(roll, plugs)
                if by_kind is None:
                    continue
                bucket.append((roll.roll_id, roll.is_trash, by_kind))

    scores = {}
    for inst in all_instances:
        pools = copy_pools(inst)
        matched = [
            (roll_id, is_trash)
            for roll_id, is_trash, by_kind in specific.get(inst.item_hash, []) + wildcards
            if can_equip(by_kind, pools)
        ]
        match_count = sum(1 for _, trash in matched if not trash)
        scores[inst.instance_id] = models.InstanceWishlistScore(
            match_count=match_count,
            has_wishlist=inst.item_hash in covered,
            matched_roll_ids=tuple(roll_id for roll_id, _ in matched),
        )
    return scores
