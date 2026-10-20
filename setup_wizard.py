# API credentials. On the first run, walks the user through registering a
# Bungie API app (and, optionally, getting a DIM API key) and writes the
# credentials to .env at the repo root. Every run then loads .env into the
# environment, where the API clients read them.
import os
import sys

import paths
from sources.bungie import oauth

REQUIRED_KEYS = ("BUNGIE_API_KEY", "BUNGIE_CLIENT_ID", "BUNGIE_CLIENT_SECRET")
BUNGIE_APP_URL = "https://www.bungie.net/en/Application"
DIM_KEY_URL = "https://github.com/DestinyItemManager/dim-api#get-an-api-key"


def read_env() -> dict:
    if not paths.ENV_FILE.exists():
        return {}
    out = {}
    for line in paths.ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


def has_required(data: dict) -> bool:
    return all(data.get(k) for k in REQUIRED_KEYS)


def prompt(label: str, optional: bool = False) -> str:
    if optional:
        suffix = " (Enter to skip)"
    else:
        suffix = ""
    while True:
        try:
            value = input(f"  {label}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("Setup cancelled.")
            sys.exit(1)
        if value or optional:
            return value
        print("  This field is required. Try again.")


def write_env(values: dict) -> None:
    lines = [f"{k}={v}" for k, v in values.items() if v]
    paths.ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_wizard() -> None:
    # Prompt for the credentials and write them to .env.
    print()
    print("=" * 60)
    print(" First-run setup")
    print("=" * 60)
    print()
    print("This tool needs API credentials before it can pull your inventory.")
    print("It looks like your .env file is missing or incomplete, so let's")
    print("walk through getting it set up. Both halves take a few minutes.")
    print()
    print("---- Step 1: Register a Bungie API app (required) ----")
    print()
    print("Open this URL in your browser:")
    print()
    print(f"  {BUNGIE_APP_URL}")
    print()
    print("Sign in with your Bungie account, then click 'Create New App'.")
    print("Fill in the form like this:")
    print()
    print("  Application Name:    anything (e.g. d2-inventory-report)")
    print("  Website:             anything (e.g. http://localhost)")
    print("  OAuth Client Type:   Confidential")
    print(f"  Redirect URL:        {oauth.DEFAULT_REDIRECT_URI}")
    print("  Scope:               check 'Read your Destiny 2 information")
    print("                       (Vault, Inventory and Vendor Items, etc.)'")
    print()
    print("After saving, the app's detail page will show three values you'll")
    print("need to paste below: API Key, OAuth client_id, OAuth client_secret.")
    print()

    api_key = prompt("Bungie API Key")
    client_id = prompt("OAuth client_id")
    client_secret = prompt("OAuth client_secret")

    print()
    print("---- Step 2: DIM API key (optional) ----")
    print()
    print("If you want DIM tag and note integration (recommended),")
    print("you'll also need a DIM API key. Skip this and the script runs")
    print("without DIM data; everything else still works.")
    print()
    print("To register a DIM app and get a key, follow the instructions at:")
    print()
    print(f"  {DIM_KEY_URL}")
    print()
    print("It's a separate registration from the Bungie one above. Paste the")
    print("key it gives you below, or just press Enter to skip for now.")
    print()

    dim_key = prompt("DIM API Key", optional=True)

    values = {
        "BUNGIE_API_KEY": api_key,
        "BUNGIE_CLIENT_ID": client_id,
        "BUNGIE_CLIENT_SECRET": client_secret,
        "BUNGIE_REDIRECT_URI": oauth.DEFAULT_REDIRECT_URI,
        "DIM_API_KEY": dim_key,
    }
    write_env(values)

    print()
    print(f"Saved credentials to {paths.ENV_FILE}")
    print("You can edit that file later to update keys or add a DIM key.")
    print("Continuing with the main script...")
    print()


def ensure_credentials() -> None:
    # Run the wizard when .env lacks the Bungie values, then load .env into
    # the environment. Variables already set in the environment win.
    if not has_required(read_env()):
        run_wizard()
    for key, value in read_env().items():
        os.environ.setdefault(key, value)
