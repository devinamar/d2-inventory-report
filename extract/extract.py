# Extract phase: each source has its own module in extract/, and this file
# re-exports their extract() functions under the source's name, so main.py can
# call extract.bungie(...), extract.dim(...) and so on. A new source adds
# extract/<name>.py with an extract() function and an import here.
# add_wishlist is --add-wishlist, which saves a wishlist source to download.

# Imports are in the order main() calls them.
from extract.wishlists import add_source as add_wishlist  # noqa: I001
from extract.bungie import extract as bungie
from extract.dim import extract as dim
from extract.clarity import extract as clarity
from extract.wishlists import extract as wishlists
from extract.aegis import extract as aegis

__all__ = ['add_wishlist', 'bungie', 'dim', 'clarity', 'wishlists', 'aegis']
