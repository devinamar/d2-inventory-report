# Command-line options and the run banner.
import argparse
import dataclasses
import pathlib

EXAMPLES = '''
Examples:
  d2-report "Player#1234"
  d2-report "Player#1234" --debug-weapon "Chroma Rush"
  d2-report "Player#1234" --output ~/reports/
  d2-report "Player#1234" --report-only
  d2-report --add-wishlist "My list" https://example.com/my_wishlist.txt
        '''


@dataclasses.dataclass
class Options:
    # Parsed command-line options for one run.
    player: str | None  # None only with edit_armor_prefs or add_wishlist
    output_dir: pathlib.Path
    edit_armor_prefs: bool = False
    add_wishlist: list | None = None  # [label, url]
    report_only: bool = False
    debug_weapon: str | None = None


def parse_args(argv=None) -> Options:
    # Parse the command line into Options.
    parser = argparse.ArgumentParser(
        prog='d2-report',
        description='Analyze a Destiny 2 vault: wishlist scores, duplicates and armor pruning.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES,
    )
    parser.add_argument(
        'player',
        nargs='?',
        default=None,
        help='Bungie name (e.g., "Player#1234"). Not required with --edit-armor-prefs or '
        '--add-wishlist.',
    )
    parser.add_argument(
        '--edit-armor-prefs',
        action='store_true',
        help='Launch the armor set and exotic preferences editor and exit. No Bungie API call.',
    )
    parser.add_argument(
        '--add-wishlist',
        nargs=2,
        metavar=('LABEL', 'URL'),
        help='Add a DIM wishlist (the URL of its raw .txt file) to the ones every run downloads, '
        'and exit. No Bungie API call.',
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Write the report from the stored database: no Bungie login, downloads or analysis.',
    )
    parser.add_argument(
        '--debug-weapon',
        help='Trace a specific weapon through the pipeline',
    )
    parser.add_argument(
        '--output',
        '-o',
        type=pathlib.Path,
        default=pathlib.Path('.'),
        help='Output directory for reports',
    )
    args = parser.parse_args(argv)

    if not args.player and not (args.edit_armor_prefs or args.add_wishlist):
        parser.error("player is required unless --edit-armor-prefs or --add-wishlist is given")

    return Options(
        player=args.player,
        output_dir=args.output,
        edit_armor_prefs=args.edit_armor_prefs,
        add_wishlist=args.add_wishlist,
        report_only=args.report_only,
        debug_weapon=args.debug_weapon,
    )


def print_header(args: Options) -> None:
    print(f"\n{'=' * 60}")
    print("D2 Inventory Report")
    print(f"{'=' * 60}")
    print(f"Player: {args.player}")
    if args.debug_weapon:
        print(f"Debug weapon: {args.debug_weapon}")
    print()
