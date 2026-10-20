# Tests for saving the profile's copies (extract/bungie/inventory.py): one
# current set of rows per copy. Copies gone from the profile are deleted, and a
# copy's own row is updated in place, so its DIM tag survives the next
# snapshot.
import models
from extract import dim
from extract.bungie import inventory, profile
from tests import conftest as c


def save(conn, weapon_ids=(), armor_ids=()):
    # Save a profile holding copies of weapon 100 and armor piece 400, the
    # way a run saves it.
    response = c.make_profile(
        vault=[{'itemHash': 100, 'itemInstanceId': i} for i in weapon_ids]
        + [{'itemHash': 400, 'itemInstanceId': i} for i in armor_ids],
        sockets={i: c.WEAPON_SOCKETS for i in weapon_ids},
    )
    inventory.save_snapshot(conn, profile.profile_rows(conn, response))


def test_copies_gone_from_the_profile_are_deleted(conn):
    # With their rows in the component tables.
    c.add_weapon_def(conn, 100)
    c.add_armor_def(conn, 400)
    save(conn, ['w1', 'w2'], ['a1', 'a2'])
    save(conn, ['w2'], ['a1'])
    copies = conn.execute('SELECT itemInstanceId FROM DestinyItemComponent ORDER BY 1')
    assert [r[0] for r in copies] == ['a1', 'w2']
    sockets = conn.execute('SELECT DISTINCT itemInstanceId FROM DestinyItemSocketsComponent')
    assert [r[0] for r in sockets] == ['w2']


def test_a_copys_dim_tag_survives_the_next_snapshot(conn):
    c.add_weapon_def(conn, 100)
    save(conn, ['w1', 'w2'])
    dim.save(conn, {'w1': models.DIMAnnotation('keep', 'god roll')})
    save(conn, ['w1', 'w2'])
    rows = conn.execute('SELECT * FROM item_dim')
    assert [tuple(r) for r in rows] == [('w1', 'keep', 'god roll')]
