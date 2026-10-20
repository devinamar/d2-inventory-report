# Where the app keeps its files: all under the repo root, all gitignored.
import pathlib

ROOT = pathlib.Path(__file__).parent

# API credentials, written by the setup wizard.
ENV_FILE = ROOT / '.env'

# Bungie OAuth tokens, kept between runs, and the self-signed certificate the
# local OAuth callback server uses.
BUNGIE_TOKEN_FILE = ROOT / '.bungie_tokens.json'
OAUTH_CERT_FILE = ROOT / '.bungie_oauth_cert.pem'
OAUTH_KEY_FILE = ROOT / '.bungie_oauth_key.pem'

# The manifest download, one SQLite file per game version.
MANIFEST_CACHE_DIR = ROOT / '.cache' / 'manifest'

# The SQLite database every phase reads and writes.
DB_FILE = ROOT / 'd2_inventory.db'
