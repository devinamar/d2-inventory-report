# Tests for the report templates' filters (report/templating.py).
from report import templating


def test_text_with_icons_draws_known_tokens_and_escapes_the_rest():
    text = '[Arc] final blows <heal> [Light Attack] [PVP: 10%]'
    assert templating.text_with_icons(text, {'[Arc]': 'https://x/arc.png'}) == (
        '<img class="text-icon" src="https://x/arc.png" alt="[Arc]" title="Arc"> final blows '
        '&lt;heal&gt; [Light Attack] [PVP: 10%]'
    )


def test_ring_rule_shares_a_ring_between_its_lists_colours():
    # Two lists take half the ring each, three give the first a half; the
    # fifth list comes round to the first colour.
    assert templating.ring_rule('1-3') == (
        '.l1-3 { --tint: var(--wl1); border-color: var(--wl1) var(--wl1) var(--wl3) var(--wl3); }'
    )
    assert templating.ring_rule('2-3-4') == (
        '.l2-3-4 { --tint: var(--wl2); border-color: var(--wl2) var(--wl2) var(--wl3) var(--wl4); }'
    )
    assert templating.ring_rule('5') == (
        '.l5 { --tint: var(--wl1); border-color: var(--wl1) var(--wl1) var(--wl1) var(--wl1); }'
    )
