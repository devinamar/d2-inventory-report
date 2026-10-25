# The Jinja environment for the report templates in report/templates/ (the HTML
# page and the Markdown copy), with the filters they share. Templates are
# cached after their first load.
import datetime
import itertools
import operator
import pathlib
import re

import jinja2
import markupsafe

import models
from analyze import armor_pruning, weapon_pruning

TEMPLATE_DIR = pathlib.Path(__file__).parent / 'templates'

# An inline text token such as [Arc] in Bungie's or Clarity's text.
TEXT_TOKEN_RE = re.compile(r'(\[[^\[\]]+\])')


def group(rows, *keys) -> list:
    # Consecutive rows sharing the keys' values, as [(value, [rows])] in row
    # order; one key gives its value, several a tuple.
    return [(k, list(g)) for k, g in itertools.groupby(rows, key=operator.itemgetter(*keys))]


def text_with_icons(text: str, icons: dict) -> markupsafe.Markup:
    # text, HTML-escaped, with each token icons has ('[Arc]': URL) drawn as
    # its icon; other tokens stay as written.
    parts = []
    for piece in TEXT_TOKEN_RE.split(text):
        url = icons.get(piece)
        if url:
            parts.append(
                markupsafe.Markup('<img class="text-icon" src="{}" alt="{}" title="{}">').format(
                    url, piece, piece[1:-1]
                )
            )
        else:
            parts.append(markupsafe.escape(piece))
    return markupsafe.Markup('').join(parts)


def dim_query(rows) -> str:
    # DIM search query for these rows' copies, like "id:123 or id:456".
    return ' or '.join(f'id:{r["instance_id"]}' for r in rows)


def day(iso: str) -> str:
    # An ISO 8601 timestamp's date, like "18 Oct 2026".
    date = datetime.date.fromisoformat(iso[:10])
    return f'{date.day} {date:%b %Y}'


def short(stats: str) -> str:
    # Comma-separated stat keys as short labels, like "Mel·Gre·Cls".
    return '·'.join(models.ARMOR_STAT_SHORT_MAP[s] for s in stats.split(','))


def pct(share) -> str:
    # A share as the report shows it: a whole percentage from 10%, one
    # decimal below (a trailing .0 dropped), '<0.1%' under that; '—' for none.
    if share is None:
        return '—'
    if share >= 0.0995:
        return f'{int(share * 100 + 0.5)}%'
    if share >= 0.001:
        return f'{share * 100:.1f}'.removesuffix('.0') + '%'
    if share > 0:
        return '<0.1%'
    return '0%'


def ring_rule(rings: str) -> str:
    # The CSS rule for class l<rings>, a perk ring in the colours of the lists
    # at those places ('1-3'): a list's colour is the --wl token its place
    # comes round to, four in turn. Each list's colour takes a quarter of the
    # ring (--ring, its four border colours), the first's any quarter left
    # over, and the first's is --tint, the fill's colour.
    colors = [f'var(--wl{(int(place) - 1) % 4 + 1})' for place in rings.split('-')]
    sides = ' '.join(colors[i * len(colors) // 4] for i in range(4))
    return f'.l{rings} {{ --tint: {colors[0]}; --ring: {sides}; }}'


def ring_sets(n: int) -> list:
    # Every set of the list places 1 to n, as a ring class's places ('1',
    # '1-3', ...): a grid's ring can take any of them.
    places = range(1, n + 1)
    return [
        '-'.join(map(str, chosen))
        for k in places
        for chosen in itertools.combinations(places, k)
    ]


ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
    autoescape=jinja2.select_autoescape(['html', 'html.j2']),
    trim_blocks=True,
    lstrip_blocks=True,
)
ENV.filters.update(
    group=group,
    icons=text_with_icons,
    dim=dim_query,
    day=day,
    short=short,
    pct=pct,
    ring_rule=ring_rule,
)
ENV.globals.update(
    ring_sets=ring_sets,
    stat_short=models.ARMOR_STAT_SHORT_MAP,
    armor_reasons=armor_pruning.PRUNE_REASONS,
    weapon_reasons=weapon_pruning.PRUNE_REASONS,
)


def render(template_name: str, **context) -> str:
    # A template rendered with the report data.
    return ENV.get_template(template_name).render(**context)
