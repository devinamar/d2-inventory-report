# Tests for the armor preferences' store (analyze/prefs/store.py): lookups by
# name, and the order preferences are saved and loaded in.
import models
from analyze.prefs import store


def test_a_name_is_found_whatever_its_case():
    prefs = {'Aion Renewal': models.ArmorPreference('melee')}
    assert store.ci_get(prefs, 'AION RENEWAL') == ('Aion Renewal', prefs['Aion Renewal'])
    assert store.ci_get(prefs, 'Techsec') == (None, None)


def test_an_exact_name_wins_over_another_case():
    prefs = {
        'bushido': models.ArmorPreference('health'),
        'Bushido': models.ArmorPreference('melee'),
    }
    assert store.ci_get(prefs, 'Bushido') == ('Bushido', prefs['Bushido'])


def test_saved_preferences_load_with_sets_by_grade_and_rank_then_exotics(conn):
    prefs = {
        'Heart': models.ArmorPreference('super_stat', is_exotic=True),
        'Bushido': models.ArmorPreference('melee', None, None, 'A', 1),
    }
    store.save_preferences(conn, prefs)
    assert list(prefs) == ['Bushido', 'Heart']  # sets first, exotics after
    assert store.load_preferences(conn) == prefs

    prefs['Techsec'] = models.ArmorPreference('grenade', 'health', None, 'S', 0)
    store.save_preferences(conn, prefs)
    assert list(store.load_preferences(conn)) == ['Techsec', 'Bushido', 'Heart']
