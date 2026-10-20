# Tests for the preference editor (analyze/prefs/editor.py): its run-time
# checks, and the full priority it shows after the picks.
import models
from analyze import aegis_rankings
from analyze.prefs import editor, terminal


def test_saved_grade_and_rank_survive_a_different_aegis_ranking():
    prefs = {'Ferropotent': models.ArmorPreference('health', grade='D', rank=2)}
    aegis = {
        aegis_rankings.normalize('Ferropotent'): [
            models.AegisBonus('Ferropotent', 2, 'x', rank=26, grade='B')
        ]
    }
    result, changed = editor.ensure_preferences({'Ferropotent'}, set(), [], prefs, aegis)
    assert (result['Ferropotent'].grade, result['Ferropotent'].rank, changed) == ('D', 2, False)


def test_a_set_the_game_recapitalized_is_saved_under_its_new_name():
    # Bungie renamed 'Aion Renewal' to 'AION Renewal' between patches. Nothing
    # is asked, but the run saves the new name.
    prefs = {'Aion Renewal': models.ArmorPreference('health', grade='D', rank=1)}
    result, changed = editor.ensure_preferences({'AION Renewal'}, set(), [], prefs, {})
    assert (list(result), result['AION Renewal'].grade, changed) == (['AION Renewal'], 'D', True)


def test_the_priority_prompt_shows_the_picks_then_the_rest_in_order(monkeypatch, capsys):
    # Keys 6 (Weapons) and 1 (Health), then 7 to stop.
    keys = iter('617')
    monkeypatch.setattr(terminal, 'read_single_key', lambda: next(keys))
    assert editor.prompt_stat_priority('Test Set', '') == ['weapons', 'health', None]
    assert 'Priorities: [Wep] > [Hlt] > Mel > Gre > Sup > Cls' in capsys.readouterr().out
