# Bungie extract: loads the manifest into its definition tables (when it has
# changed), writes the app's stat vocabulary, then saves the player's weapon
# and armor copies as the profile reports them.
import sys

from extract import source_status
from extract.bungie import inventory, manifest, profile
from sources.bungie import api_mappings
from sources.bungie import constants as bungie_constants
from sources.bungie.connect import Session


def save_vocabulary(conn, stat_keys: dict) -> None:
    # Replace stat_key ({stat hash: key}).
    with conn:
        conn.execute("DELETE FROM stat_key")
        conn.executemany("INSERT INTO stat_key VALUES (?, ?)", stat_keys.items())


def extract(conn, session: Session, args) -> None:
    # Ingest the manifest, fetch the profile once and save every weapon and
    # armor copy. Exits, saving nothing, when the profile has no socket data.
    if manifest.ingest_manifest(conn, session.manifest_path, session.manifest_version):
        status = 'fresh'
    else:
        status = 'cached'
    source_status.save(conn, 'manifest', status, session.manifest_version)
    save_vocabulary(conn, api_mappings.STAT_KEYS)
    response = session.api.get_profile(
        session.membership_type, session.membership_id, bungie_constants.PROFILE_COMPONENTS
    )
    source_status.save(conn, 'profile', 'fresh')

    print("Fetching inventory...")
    rows = profile.profile_rows(conn, response)
    if not rows.reusable_plugs:
        print("\n  WARNING: No reusablePlugs data returned!")
        print("  OAuth may not be working correctly.")
        print("  Falling back to currently equipped perks only.\n")
    if not rows.sockets:
        print("\nNo socket data in the profile. Check OAuth status.")
        sys.exit(1)

    inventory.save_snapshot(conn, rows)
    sockets, plugs, stats = conn.execute(
        "SELECT (SELECT COALESCE(SUM(json_array_length(sockets)), 0) "
        "        FROM DestinyItemSocketsComponent), "
        "       (SELECT COUNT(*) FROM DestinyItemReusablePlugsComponent r "
        "        CROSS JOIN json_each(r.plugs) s CROSS JOIN json_each(s.value)), "
        "       (SELECT COUNT(*) FROM DestinyItemStatsComponent t CROSS JOIN json_each(t.stats))"
    ).fetchone()
    print(
        f"  Weapon and armor copies: {len(rows.items):,} ({sockets:,} sockets, "
        f"{plugs:,} switchable plugs, {stats:,} stats)"
    )
    weapons = conn.execute("SELECT COUNT(*), COUNT(DISTINCT item_hash) FROM v_weapon").fetchone()
    armor = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT i.itemHash) FROM DestinyItemComponent i "
        "JOIN DestinyInventoryItemDefinition d ON d.hash = i.itemHash WHERE d.itemType = 2"
    ).fetchone()
    print(f"  Weapons: {weapons[0]} copies of {weapons[1]} weapons")
    print(f"  Armor: {armor[0]} copies of {armor[1]} pieces")
    if args.debug_weapon:
        inventory.trace_weapon(conn, args.debug_weapon)
