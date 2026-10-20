# End-of-run summary: counts read from the db once the report is written,
# printed to the console.
from report import load


def summary_counts(conn) -> dict:
    # Counts for the end-of-run summary: the Summary page's weapons to review,
    # true duplicates and armor pieces to purge (load.TOTALS); weapon copies
    # some wishlist covers; and the armor sets you have a piece of.
    totals = conn.execute(load.TOTALS).fetchone()

    def count(sql):
        return conn.execute(sql).fetchone()[0]

    return {
        'families': totals['families'],
        'covered': count("SELECT COUNT(*) FROM weapon_result WHERE has_wishlist = 1"),
        'true_duplicates': totals['true_duplicates'],
        'sets': count("SELECT COUNT(DISTINCT set_name) FROM v_armor WHERE set_hash IS NOT NULL"),
        'flagged': totals['armor_to_purge'],
    }


def dim_summary(conn) -> dict:
    # Counts for the DIM summary lines.
    row = conn.execute(
        "SELECT "
        "  SUM(CASE WHEN COALESCE(tag, '') != '' THEN 1 ELSE 0 END) tagged, "
        "  SUM(CASE WHEN COALESCE(notes, '') != '' THEN 1 ELSE 0 END) noted "
        "FROM item_dim"
    ).fetchone()
    return {
        'tagged': row['tagged'] or 0,
        'noted': row['noted'] or 0,
    }


def plural(n, one, many) -> str:
    # n with the word for its number, like "1 weapon" or "2 weapons".
    if n == 1:
        return f"{n} {one}"
    return f"{n} {many}"


def print_summary(conn) -> None:
    # End-of-run summary, counted from the db.
    print(f"\n{'=' * 60}")
    print("Done!")
    print(f"{'=' * 60}\n")

    counts = {**summary_counts(conn), **dim_summary(conn)}
    print("Summary:")
    if counts['families']:
        weapons = plural(counts['families'], 'weapon', 'weapons')
        print(f"  - {weapons} to review: more than one copy each")
    if counts['covered']:
        copies = plural(counts['covered'], 'weapon copy', 'weapon copies')
        print(f"  - {copies} covered by a wishlist")
    if counts['true_duplicates']:
        print(f"  - {plural(counts['true_duplicates'], 'true duplicate', 'true duplicates')}")
    if counts['sets']:
        print(f"  - {plural(counts['sets'], 'armor set', 'armor sets')} in vault")
    if counts['flagged']:
        print(f"  - {plural(counts['flagged'], 'armor piece', 'armor pieces')} to purge")
    if counts['tagged'] or counts['noted']:
        tagged = plural(counts['tagged'], 'tagged item', 'tagged items')
        print(f"  - DIM: {tagged}, {counts['noted']} with notes")
    print()
