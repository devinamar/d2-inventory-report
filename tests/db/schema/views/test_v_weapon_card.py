# Tests for v_weapon_card (db/schema/views/v_weapon_card.sql): each copy left
# after pruning, with the card it shows on and the card's grid.
from tests import conftest as c


def test_copies_show_on_their_scored_weapons_card_or_their_familys(conn):
    # Gun's versions roll two trait pools, so its copies split into two cards.
    # Rifle's versions aren't scored, so their copies share a card named after
    # the family, its grid named after its lowest version. A pruned copy is on
    # no card.
    for item_hash, name in ((100, 'Gun'), (101, 'Gun'), (200, 'Rifle'), (201, 'Rifle (Adept)')):
        c.add_weapon_def(conn, item_hash, name=name)
    c.add_popularity(conn, 'Gun (Raid)', [100], family='Gun')
    c.add_popularity(conn, 'Gun (Pantheon)', [101], family='Gun')
    for instance_id, item_hash in (
        ('a', 100),
        ('b', 101),
        ('c', 101),
        ('d', 201),
        ('e', 200),
        ('f', 200),
    ):
        c.add_copy(conn, instance_id, item_hash)
    with conn:
        conn.execute(
            "INSERT INTO weapon_pruning (instance_id, reason, keeper_id) "
            "VALUES ('f', 'exact_duplicate', 'e')"
        )
    rows = conn.execute(
        "SELECT instance_id, card, entry, family, grid_id, k, copies FROM v_weapon_card "
        "ORDER BY instance_id"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('a', 'Gun (Raid)', 'Gun (Raid)', 'Gun', 100, 1, 1),
        ('b', 'Gun (Pantheon)', 'Gun (Pantheon)', 'Gun', 101, 1, 2),
        ('c', 'Gun (Pantheon)', 'Gun (Pantheon)', 'Gun', 101, 2, 2),
        ('d', 'Rifle', None, 'Rifle', 200, 1, 2),
        ('e', 'Rifle', None, 'Rifle', 200, 2, 2),
    ]


def test_an_unscored_version_joins_the_card_its_family_name_shares(conn):
    # Vigil is scored only under its first version: a copy of the other one
    # shares its card and its grid.
    c.add_weapon_def(conn, 300, name='Vigil')
    c.add_weapon_def(conn, 301, name='Vigil')
    c.add_popularity(conn, 'Vigil', [300])
    c.add_copy(conn, 'x', 300)
    c.add_copy(conn, 'y', 301)
    rows = conn.execute(
        "SELECT instance_id, card, entry, grid_id, copies FROM v_weapon_card ORDER BY instance_id"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('x', 'Vigil', 'Vigil', 300, 2),
        ('y', 'Vigil', None, 300, 2),
    ]
