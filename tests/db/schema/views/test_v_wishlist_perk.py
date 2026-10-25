# Tests for v_wishlist_perk (db/schema/views/v_wishlist_perk.sql): each
# wishlist roll's perks by name, with its list's place.
from tests import conftest as c


def test_a_rolls_perks_are_named_with_its_lists_place(conn):
    # Aegis Endgame is the second default list. A roll naming no perks (any
    # roll of the weapon) has no rows; a trash roll keeps its flag.
    with conn:
        conn.execute(
            "INSERT INTO wishlist_source (key, label, url) VALUES ('aegis_endgame', 'Aegis', '')"
        )
        conn.executemany(
            "INSERT INTO wishlist_roll (roll_id, source_key, item_hash, perk1, perk2, is_trash) "
            "VALUES (?, 'aegis_endgame', 100, ?, ?, ?)",
            [
                (1, c.BARREL_PERK_X, c.TRAIT_PERK_A, 0),
                (2, None, None, 0),
                (3, c.TRAIT_PERK_B, None, 1),
            ],
        )
    rows = conn.execute(
        "SELECT roll_id, source_key, place, item_hash, is_trash, perk FROM v_wishlist_perk "
        "ORDER BY roll_id, perk"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (1, 'aegis_endgame', 2, 100, 0, 'Hammer-Forged Rifling'),
        (1, 'aegis_endgame', 2, 100, 0, 'Rampage'),
        (3, 'aegis_endgame', 2, 100, 1, 'Kill Clip'),
    ]
