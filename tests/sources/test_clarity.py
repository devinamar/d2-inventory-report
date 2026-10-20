# Tests for Clarity's community perk descriptions (sources/clarity.py): its
# version check, and dim.json's entries parsed into Bungie-style text with
# inline icon tokens. The entries are real ones from the live file.
import pytest

from sources import clarity
from tests import conftest as c

# Demoralize's text holds a Void icon, and a spacer between its two lines.
DEMORALIZE = {
    'hash': 1464081238,
    'name': 'Demoralize',
    'descriptions': {
        'en': [
            {
                'linesContent': [
                    {'text': 'Precision Kills apply '},
                    {'classNames': ['void']},
                    {'text': 'Weaken to enemies within 7 meters of the target for ? seconds.'},
                ]
            },
            {'classNames': ['spacer']},
            {'linesContent': [{'text': '1.5? second cooldown between activations.'}]},
        ]
    },
}
DEMORALIZE_TEXT = (
    'Precision Kills apply [Void]Weaken to enemies within 7 meters of the target for ? seconds.\n'
    '1.5? second cooldown between activations.'
)
# An entry Clarity names but hasn't described.
SPECIAL_AMMO_SCOUT = {'hash': 25154119, 'name': 'Special Ammo Scout'}


def test_the_version_text_does_not_depend_on_the_files_layout(monkeypatch):
    # versions.json as GitHub serves it, then laid out another way: the same
    # text, so only a new version downloads dim.json again.
    bodies = iter([b'{\n "descriptions": 2.0625\n}', b'{"descriptions":2.0625}'])
    headers = {'Content-Type': 'text/plain; charset=utf-8'}
    sent = []

    def get(url, timeout):
        sent.append((url, timeout))
        return c.make_response(body=next(bodies), headers=headers)

    monkeypatch.setattr(clarity.requests, 'get', get)
    assert [clarity.fetch_version(), clarity.fetch_version()] == ['{"descriptions": 2.0625}'] * 2
    assert sent == [(clarity.CLARITY_VERSIONS_URL, 10)] * 2


def test_segments_join_into_lines_and_empty_lines_are_dropped():
    assert clarity.parse_description(DEMORALIZE) == DEMORALIZE_TEXT


@pytest.mark.parametrize(
    'icon, token',
    [
        ('void', '[Void]'),
        ('barrier', '[Shield-Piercing]'),
        ('overload', '[Disruption]'),
        ('unstoppable', '[Stagger]'),
        ('heavy', ''),
    ],
)
def test_element_and_champion_icons_become_bungies_tokens(icon, token):
    # Other icons, such as heavy ammo's, leave nothing.
    assert clarity.segment_text({'classNames': [icon]}) == token


def test_a_styled_segment_keeps_its_text():
    # From Ranged Weapon's entry: the only class a segment with text has is bold.
    segment = {'text': 'With Gyro Core Equipped:', 'classNames': ['bold']}
    assert clarity.segment_text(segment) == 'With Gyro Core Equipped:'


def test_descriptions_are_keyed_by_perk_hash_and_entries_without_english_are_dropped():
    # A key that isn't a perk hash is skipped too.
    raw = {'1464081238': DEMORALIZE, '25154119': SPECIAL_AMMO_SCOUT, 'version': {'en': 1}}
    assert clarity.parse_clarity_json(raw) == {1464081238: DEMORALIZE_TEXT}
