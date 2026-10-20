# D2 Inventory Report: takes a Bungie name, pulls the player's vault into a
# local SQLite db, and writes a Markdown + HTML report on duplicate weapons
# and armor worth dismantling.

# Imports are in the order main() uses them.
import cli  # noqa: I001  command-line options and banner
import setup_wizard  # first-run credential setup; loads .env
from sources.bungie.connect import connect  # Bungie login, manifest download, player lookup
from db import connection  # open the SQLite db, creating or migrating it
from extract import extract  # pull Bungie, DIM, Clarity, wishlist and Aegis data into the db
from analyze import analyze  # score weapons against wishlists, flag armor to dismantle
from report import report, summary  # write the reports to --output, then the summary


def main():
    args = cli.parse_args()

    # The preference editor runs on its own and exits; no Bungie login.
    if args.edit_armor_prefs:
        analyze.edit_prefs(connection.open_db())
        return

    # So does adding a wishlist source, which the next run downloads.
    if args.add_wishlist:
        if not extract.add_wishlist(connection.open_db(), *args.add_wishlist):
            raise SystemExit(1)
        return

    # Reports go to --output, the current directory by default.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cli.print_header(args)

    # --report-only writes the report again from what the db holds: no login,
    # downloads or analysis, so nothing prompts.
    if args.report_only:
        conn = connection.open_db()
        report.write(conn, args.output_dir, args.player)
        summary.print_summary(conn)
        return

    # Ask for the API credentials on the first run, then load them.
    setup_wizard.ensure_credentials()

    # Log in to Bungie, download the manifest, and find the player.
    session = connect(args.player)

    # Extract and analyze write to this SQLite db; the report reads from it.
    conn = connection.open_db()

    # Extract: each step pulls one source into the db.
    extract.bungie(conn, session, args)
    extract.dim(conn, session)
    extract.clarity(conn)
    extract.wishlists(conn)
    extract.aegis(conn)

    # Analyze: each step reads the stored inventory and saves its results.
    analyze.weapons(conn)
    analyze.armor(conn)

    # Report: renders the stored inventory and results as HTML and Markdown.
    report.write(conn, args.output_dir, args.player)

    summary.print_summary(conn)


if __name__ == '__main__':
    main()
