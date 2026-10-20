# Destiny 2 Inventory Report

Reads your Destiny 2 vault and tells you what to keep and what to dismantle.

## Setup

1. Install the dependencies (Python 3.11 or newer):

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. Create a Bungie app at <https://www.bungie.net/en/Application>:
   - OAuth Client Type: Confidential
   - Redirect URL: `https://localhost:7777/callback`
   - Scope: Read your Destiny 2 information

> [!NOTE]
> The Bungie app is required for the application, as this is locally run and private. This
> allows for caching tokens.

3. Run it with your Bungie Name. The first run asks for the app's API key, client_id and
   client_secret, and an optional [DIM](https://destinyitemmanager.com/) (Destiny Item Manager)
   [API key](https://github.com/DestinyItemManager/dim-api#get-an-api-key) for your DIM tags
   and notes, then saves them to `.env`:

   ```bash
   ./d2-report "Name#1234"
   ```

## Usage

```bash
./d2-report "Name#1234"                   # full run
./d2-report "Name#1234" --report-only     # report again, no downloads
./d2-report --edit-armor-prefs            # edit armor preferences
./d2-report --add-wishlist "My list" URL  # add a wishlist
./d2-report --help                        # everything else
```

Reports are written to the folder you run it from. Three
[wishlists](https://github.com/DestinyItemManager/DIM/wiki/Creating-Wish-Lists) come built in;
`--add-wishlist` adds your own.

## The report

One HTML page (and a Markdown copy) with:

- **Summary**: what to review and what to purge
- **Weapons**: duplicates, and each roll against the wishlists
- **Armor sets**: what each set keeps and purges
- **Builds**: stat builds your armor falls short in
- **Exotics**: extra exotic copies
- **Preferences**: your armor picks and wishlists

## Structure

| Path | What it does |
| --- | --- |
| `main.py` | Runs the steps in order |
| `cli.py` | Command-line options |
| `setup_wizard.py` | First-run credentials |
| `paths.py` | Where every file lives |
| `models.py` | The data shapes passed between steps |
| `db/` | The SQLite database and its schema |
| `sources/` | Downloads from Bungie, DIM, [Clarity](https://github.com/Database-Clarity/Live-Clarity-Database), [The Aegis](https://docs.google.com/spreadsheets/d/1JM-0SlxVDAi-C6rGVlLxa-J1WGewEeL8Qvq4htWZHhY/) and the wishlists |
| `extract/` | Saves what the sources return to the db |
| `analyze/` | Scores rolls, finds duplicates, picks armor to purge |
| `report/` | Writes the HTML and Markdown report |
| `tests/` | Mirrors the folders above |
