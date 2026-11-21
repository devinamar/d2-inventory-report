// The report's behaviour: page tabs by URL hash, class, weapon, side and
// wishlist switches, opening weapon cards, armor sets and Popular's weapons
// (one by one, or a group at a time by its double chevron), the perk grids
// they open and the copy a weapon card shows, Popular's filters, tooltips and
// copying DIM queries and ids; and setting the report up again, as the player
// left it, when a newer one is swapped into the page.

// Tabs: show the page the hash names (#weapons shows #page-weapons), the
// Summary when it names none. Page ids differ from the hashes so the browser
// doesn't scroll past the header to them.
function route() {
    let shown = 'summary';
    if (document.getElementById('page-' + location.hash.slice(1))) {
        shown = location.hash.slice(1);
    }
    for (const p of document.querySelectorAll('.page')) {
        p.hidden = p.id !== 'page-' + shown;
    }
    for (const a of document.querySelectorAll('nav a')) {
        if (a.hash === '#' + shown) {
            a.setAttribute('aria-current', 'page');
        } else {
            a.removeAttribute('aria-current');
        }
    }
    window.scrollTo(0, 0);
}
addEventListener('hashchange', route);

// A side's scope: the closest element that names a side (a Popular list, a
// weapon card), PvE outside one.
function sideOf(el) {
    const scope = el.closest('[data-side]');
    if (scope) {
        return scope.dataset.side;
    }
    return 'pve';
}

// A share as the report shows it (templating.pct): a whole percentage from
// 10%, one decimal below, '<0.1%' under that.
function pct(share) {
    if (share >= 0.0995) {
        return Math.floor(share * 100 + 0.5) + '%';
    }
    if (share >= 0.001) {
        return (share * 100).toFixed(1).replace(/\.0$/, '') + '%';
    }
    if (share > 0) {
        return '<0.1%';
    }
    return '0%';
}

// The heat colour of rel, a share against its column's top: red at 0, yellow
// at 0.5, green at 1, as the rows' --h0 to --h10.
function heat(rel) {
    const t = Math.min(1, Math.max(0, rel));
    if (t <= 0.5) {
        return `color-mix(in oklab, var(--heat-lo) ${Math.round((1 - 2 * t) * 100)}%, var(--heat-mid))`;
    }
    return `color-mix(in oklab, var(--heat-mid) ${Math.round((2 - 2 * t) * 100)}%, var(--heat-hi))`;
}

// Tooltips: one fixed element filled from the hovered or focused element's
// tip-<id> block (a perk's by its plug, a weapon's confidence or Endgame badge
// per side, a Preferences badge's set or exotic). A grid row's adds its rank
// on the side shown, the shown lists naming it (or with a roll the copy shown
// completes) and, while a trait is focused, its pair with that trait. It sits
// above its element when it fits, else below; a trait's sits beside its
// column (left of Trait 1, right of Trait 2), clear of the pair lines between
// them.
let tip = document.getElementById('tip');
const SIDE_LABELS = { pve: 'PvE', pvp: 'PvP' };

function gridTip(perk) {
    const side = sideOf(perk);
    const head = document.createElement('div');
    head.className = 'tip-head';
    head.append(tip.querySelector('b'));
    let rank = null;
    if (perk.matches('.tp')) {
        rank = 1;
    } else if ((perk.dataset[side === 'pvp' ? 'b' : 'a'] || '—') !== '—') {
        rank = perk.dataset.r.split(' ')[Number(side === 'pvp')];
    }
    if (rank) {
        const r = document.createElement('span');
        r.className = 'tip-rank';
        r.textContent = '#' + rank;
        head.append(r);
    }
    tip.prepend(head);
    const ring = [...perk.classList].find((c) => /^l\d/.test(c));
    if (ring) {
        const named = document.createElement('p');
        named.className = 'named';
        let lead = 'Named by ';
        if (perk.classList.contains('hit')) {
            lead = 'In a roll this copy completes: ';
        }
        named.append(lead);
        const names = document.querySelectorAll('#wishlists .wl-name');
        ring.slice(1).split('-').forEach((place, i) => {
            if (i) {
                named.append(', ');
            }
            named.append(names[place - 1].cloneNode(true));
        });
        tip.append(named);
    }
    if (perk._pair) {
        const p = perk._pair;
        const line = document.createElement('p');
        line.className = 'tip-pair';
        line.style.color = heat(p.rel);
        line.textContent = `${p.name}: ${pct(p.share)} of all ${SIDE_LABELS[side]} pairs, #${p.rank}`;
        tip.append(line);
    }
}

function showTip(e) {
    const perk = e.target.closest('[data-tip]');
    const source = perk && document.getElementById('tip-' + perk.dataset.tip);
    if (!source) {
        tip.hidden = true;
        return;
    }
    tip.innerHTML = source.innerHTML;
    if (perk.matches('.pk, .tp')) {
        gridTip(perk);
    }
    tip.hidden = false;
    const r = perk.getBoundingClientRect();
    const w = tip.offsetWidth;
    const h = tip.offsetHeight;
    const col = perk.closest('.pc');
    const trait = (col && col.dataset.col) || '';
    let top = r.top - h - 6;
    let left = r.left;
    if (trait === 'trait1' && r.left - w - 12 >= 8) {
        left = r.left - w - 12;
        top = r.top;
    } else if (trait === 'trait2' && r.right + w + 12 <= innerWidth - 8) {
        left = r.right + 12;
        top = r.top;
    } else {
        if (top < 8) {
            top = r.bottom + 6;
        }
        if (trait === 'trait1') {
            left = r.right - w;
        }
    }
    tip.style.top = Math.max(8, Math.min(top, innerHeight - h - 8)) + 'px';
    tip.style.left = Math.max(8, Math.min(left, innerWidth - w - 8)) + 'px';
}

document.addEventListener('mouseover', showTip);
document.addEventListener('focusin', showTip);

// Weapon sections: each shows when a weapon in it does and counts those
// showing, as Roll Quality's heading counts them all.
function countCards(page) {
    for (const fold of page.querySelectorAll('details.fold')) {
        const count = fold.querySelector(':scope > summary .count');
        if (!count) {
            continue;
        }
        const n = fold.querySelectorAll('.fam:not([hidden])').length;
        count.textContent = n;
        fold.hidden = n === 0;
    }
    const total = page.querySelector('h2 .count');
    if (total) {
        total.textContent = page.querySelectorAll('.fam:not([hidden])').length;
    }
}
// The weapons page's order toggles (data-sort): by default each card sits in
// its slot's and weapon type's section, in the page's order. Popularity order
// lists each slot's cards in one list (.ranked, by data-slot) by their
// weapon's rank on the side the Popularity switch shows (data-rank holds
// both), those with none last; One list puts every card in one list (.all),
// in the page's order or, with Popularity order, by rank. The sections left
// empty are hidden by the recount. Each card keeps its section and place
// (_home, _n) to go back to.
function sortCards(page) {
    const pressed = (name) => {
        const b = page.querySelector(`button[data-sort="${name}"]`);
        return Boolean(b) && b.getAttribute('aria-pressed') === 'true';
    };
    const ranked = pressed('rank');
    const one = pressed('one');
    if (!ranked && !one && !page._sorted) {
        return;
    }
    const cards = [...page.querySelectorAll('.fam')];
    cards.forEach((card, n) => {
        if (!card._home) {
            card._home = card.parentElement;
            card._n = n;
        }
    });
    const side = page.querySelector('.switch.side:not(.mini) [aria-pressed="true"]').dataset.value;
    const i = Number(side === 'pvp');
    const place = (card) => Number(card.dataset.rank.split(' ')[i]) || Infinity;
    if (ranked) {
        cards.sort((a, b) => place(a) - place(b) || a._n - b._n);
    } else {
        cards.sort((a, b) => a._n - b._n);
    }
    if (one) {
        page.querySelector('.fams.all').append(...cards);
    } else if (ranked) {
        for (const list of page.querySelectorAll('.fams.ranked')) {
            list.append(...cards.filter((card) => card.dataset.slot === list.dataset.slot));
        }
    } else {
        for (const card of cards) {
            card._home.append(card);
        }
    }
    page._sorted = ranked || one;
    countCards(page);
}
addEventListener('scroll', () => { tip.hidden = true; }, { passive: true });

// Perk grids (grids.html.j2): a grid's template is cloned into a Popular
// row or a weapon card the first time it opens. Its rows go in the order of
// the side shown (data-r holds each side's place), its perks named by a list
// the wishlist switch shows get that list's ring (data-l holds the places of
// the lists naming each), and its trait pairs' lines are drawn from its paths
// (each side's figures in data-pve and data-pvp). On a weapon card the grid
// shows the copy picked (the host's data-k): its perks outlined (data-o),
// those in a roll it completes ringed solid (data-h), and its pairs' lines.
// Hovering or focusing a trait focuses it: its partners light up, tinted and
// lined by how often players pair them, and the rest fade. Clicking it, or
// Enter, pins the focus until Esc or another click.

// The list place the wishlist switch shows, as a string, or null for All
// lists (and on a page without the switch).
function placeShown(page) {
    const buttons = [...page.querySelectorAll('.switch[data-key="wl"] button')].slice(1);
    const pressed = buttons.findIndex((b) => b.getAttribute('aria-pressed') === 'true');
    if (pressed < 0) {
        return null;
    }
    return String(pressed + 1);
}

// A list's children (a grid column's rows, a picker's copies) in the order of
// the side shown: data-r holds each side's place.
function sortBySide(list) {
    const i = Number(sideOf(list) === 'pvp');
    const items = [...list.children];
    const place = (el) => Number(el.dataset.r.split(' ')[i]);
    if (items.every((el, n) => n === 0 || place(items[n - 1]) <= place(el))) {
        return;
    }
    items.sort((a, b) => place(a) - place(b));
    list.append(...items);
}

// The places among a space- or dash-separated list (data-l, a hit's places)
// that the wishlist switch shows.
function placesShown(text, shown) {
    return (text || '').split(/[ -]/).filter((place) => place && (!shown || place === shown));
}

// A grid's wishlist rings. With no copy shown, each perk named by a list shown
// is ringed (pick) in those lists' colours (l<places>). With a copy, its perks
// are outlined (owned); one in a roll of a list shown that the copy completes
// is ringed solid (hit) in those lists' colours, and any other perk a list
// shown names is ringed dashed (named). A perk the page's perk search picked
// is outlined (found). A row keeps its classes (_ring) and is only touched
// when they change.
function paintGrid(grid) {
    const page = grid.closest('.page');
    const shown = placeShown(page);
    const found = page._perks || [];
    const k = grid.closest('[data-g]').dataset.k;
    grid.classList.toggle('has-copy', Boolean(k));
    for (const li of grid.querySelectorAll('.pk')) {
        const ring = [];
        let places = placesShown(li.dataset.l, shown);
        let state = 'pick';
        if (k) {
            state = 'named';
            if ((li.dataset.o || '').split(' ').includes(k)) {
                ring.push('owned');
            }
            const hit = (li.dataset.h || '').split(' ').find((h) => h.startsWith(k + ':'));
            const hits = placesShown(hit && hit.split(':')[1], shown);
            if (hits.length) {
                state = 'hit';
                places = hits;
            }
        }
        if (places.length) {
            ring.push(state, 'l' + places.join('-'));
        }
        if (found.includes(li.dataset.tip)) {
            ring.push('found');
        }
        const key = ring.join(' ');
        if ((li._ring || '') === key) {
            continue;
        }
        if (li._ring) {
            li.classList.remove(...li._ring.split(' '));
        }
        li.classList.add(...ring);
        li._ring = key;
    }
}

// A pair's figures on a side, from its line's path: its rank, rel and share,
// each 0 where players weren't seen with it, and its verdict (g, b or m);
// null when the side has no pair scores.
function pairOn(path, side) {
    const figures = path.dataset[side];
    if (!figures) {
        return null;
    }
    const fields = figures.split(' ');
    const [rank, rel, share] = fields.slice(0, 3).map(Number);
    return { path, rank, rel, share, verdict: fields[3] };
}

// How strongly a line shows: steeply fainter as its pair's share drops.
function fade(rel) {
    return 0.12 + 0.88 * rel * rel;
}

// The lines waiting for the next frame, by grid: each a pair's path, the
// rows it joins (from in Trait 1, to in Trait 2) and its look. They are drawn
// together, every rectangle read before any path is written, so the page is
// laid out once a frame rather than once a line.
const queued = new Map();

// Draw the queued lines in their grids' coordinates; a grid closed since
// (no width) draws none.
function drawQueued() {
    const jobs = [...queued].map(([grid, lines]) => ({
        grid,
        box: grid.getBoundingClientRect(),
        lines: lines.map((line) => ({
            ...line,
            a: line.from.getBoundingClientRect(),
            b: line.to.getBoundingClientRect(),
        })),
    }));
    queued.clear();
    for (const { grid, box, lines } of jobs) {
        if (!box.width) {
            continue;
        }
        for (const { path, a, b, cls, width, opacity, color } of lines) {
            const x1 = a.right - box.left;
            const y1 = a.top + a.height / 2 - box.top;
            const x2 = b.left - box.left;
            const y2 = b.top + b.height / 2 - box.top;
            const mx = (x1 + x2) / 2;
            path.setAttribute('d', `M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`);
            path.setAttribute('class', cls);
            path.setAttribute('stroke-width', width);
            path.setAttribute('stroke-opacity', opacity.toFixed(2));
            path.style.stroke = color;
            path.style.display = '';
        }
        const svg = grid.querySelector('.links');
        svg.setAttribute('width', box.width);
        svg.setAttribute('height', box.height);
        svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`);
    }
}

// Queue a grid's lines for the next frame, replacing any queued before.
function queueLines(grid, lines) {
    if (!queued.size) {
        requestAnimationFrame(drawQueued);
    }
    queued.set(grid, lines);
}

// The trait columns in focus: a focused trait's six most run partners light
// up (tinted, showing the pair's share of all the weapon's pairs in bold) and
// are lined, weighted by how often players pick the pair; the other traits fade, and so do the other
// columns. Without a focus, the side's three most picked pairs are lined, or
// with a copy shown, the pairs it can make that are desired (in a roll of a
// list shown, or the pair's verdict) or undesirable (in a trash roll of a list
// shown, or the verdict), a trash pair in red, and dashed, the two most picked
// pairs it can't make.
function applyFocus(grid, focus) {
    grid._focus = focus;
    if (grid._lit) {
        for (const li of grid._lit) {
            li.classList.remove('focus', 'partner', 'dim');
            li.style.removeProperty('--heat');
            delete li.dataset.f;
            li._pair = null;
        }
        for (const list of grid.querySelectorAll('.pl.soft')) {
            list.classList.remove('soft');
        }
        grid._lit = null;
    }
    if ((grid._pressed || null) !== (grid._pinned || null)) {
        if (grid._pressed) {
            grid._pressed.setAttribute('aria-pressed', 'false');
        }
        if (grid._pinned) {
            grid._pinned.setAttribute('aria-pressed', 'true');
        }
        grid._pressed = grid._pinned;
    }
    const svg = grid.querySelector('.links');
    const paths = [...svg.children];
    for (const p of paths) {
        if (p.style.display !== 'none') {
            p.style.display = 'none';
        }
    }
    const t1 = grid.querySelector('.pc[data-col="trait1"]');
    const t2 = grid.querySelector('.pc[data-col="trait2"]');
    if (!t1 || !t2) {
        return;
    }
    const lines = [];
    const side = sideOf(grid);
    const row = (col, key) => col.querySelector(`[data-tip="${key}"]`);
    const pairs = paths.map((p) => pairOn(p, side)).filter((p) => p && p.rank);
    pairs.sort((x, y) => x.rank - y.rank);
    const k = grid.closest('[data-g]').dataset.k;
    if (focus) {
        const first = t1.contains(focus);
        const key = focus.dataset.tip;
        const partners = pairs.filter((p) => p.path.dataset[first ? 'a' : 'b'] === key).slice(0, 6);
        focus.classList.add('focus');
        grid._lit = [...t1.querySelectorAll('.pk'), ...t2.querySelectorAll('.pk')];
        for (const li of grid._lit) {
            if (li !== focus) {
                li.classList.add('dim');
            }
        }
        for (const p of partners) {
            let other = row(t1, p.path.dataset.a);
            if (first) {
                other = row(t2, p.path.dataset.b);
            }
            if (!other) {
                continue;
            }
            const [from, to] = first ? [focus, other] : [other, focus];
            other.classList.replace('dim', 'partner');
            other.style.setProperty('--heat', heat(p.rel));
            other.dataset.f = pct(p.share);
            other._pair = { name: from.textContent + ' + ' + to.textContent, share: p.share, rank: p.rank, rel: p.rel };
            const opacity = Math.max(0.25, fade(p.rel));
            lines.push({ path: p.path, from, to, cls: 'hover', width: 1 + 5 * p.rel, opacity, color: heat(p.rel) });
        }
        for (const list of grid.querySelectorAll('.pc:not([data-col^="trait"]) .pl')) {
            list.classList.add('soft');
        }
    } else if (k) {
        const shown = placeShown(grid.closest('.page'));
        const made = paths.filter((path) => (path.dataset.c || '').split(' ').includes(k));
        for (const path of made) {
            const p = pairOn(path, side) || { path, rel: 0, verdict: null };
            const trash = placesShown(path.dataset.t, shown).length > 0;
            const wanted = !trash && placesShown(path.dataset.w, shown).length > 0;
            let cls = null;
            if (trash || (!wanted && p.verdict === 'b')) {
                cls = 'bad';
            } else if (wanted || p.verdict === 'g') {
                cls = 'good';
            }
            const from = row(t1, path.dataset.a);
            const to = row(t2, path.dataset.b);
            if (!cls || !from || !to) {
                continue;
            }
            let opacity = Math.max(cls === 'bad' ? 0.4 : 0.3, fade(p.rel));
            if (wanted) {
                opacity = 1;
            }
            let color = heat(p.rel);
            if (trash) {
                color = 'var(--bad)';
            }
            lines.push({ path, from, to, cls, width: 2.5, opacity, color });
        }
        for (const p of pairs.filter((x) => !made.includes(x.path)).slice(0, 2)) {
            const from = row(t1, p.path.dataset.a);
            const to = row(t2, p.path.dataset.b);
            if (from && to) {
                const opacity = 0.7 * fade(p.rel);
                lines.push({ path: p.path, from, to, cls: 'top', width: 1.5, opacity, color: heat(p.rel) });
            }
        }
    } else {
        for (const p of pairs.slice(0, 3)) {
            const from = row(t1, p.path.dataset.a);
            const to = row(t2, p.path.dataset.b);
            if (from && to) {
                const width = 1 + 5 * p.rel;
                lines.push({ path: p.path, from, to, cls: 'good', width, opacity: fade(p.rel), color: heat(p.rel) });
            }
        }
    }
    queueLines(grid, lines);
}

// A grid's focus follows the pointer and keyboard over its traits, held while
// the pointer crosses the space between them and dropped when it leaves the
// grid; a click or Enter pins it, and Esc, or a click elsewhere in the grid,
// unpins it.
function traitRow(target) {
    const li = target.closest('.pk');
    if (li && li.closest('.pc[data-col^="trait"]')) {
        return li;
    }
    return null;
}

function bindGrid(grid) {
    // Pin li, or unpin it when it is the trait already pinned.
    const pin = (li) => {
        if (grid._pinned === li) {
            grid._pinned = null;
        } else {
            grid._pinned = li;
        }
        applyFocus(grid, grid._pinned);
    };
    grid.addEventListener('mouseover', (e) => {
        const li = traitRow(e.target);
        if (!grid._pinned && li && li !== grid._focus) {
            applyFocus(grid, li);
        }
    });
    grid.addEventListener('mouseleave', () => {
        if (!grid._pinned) {
            applyFocus(grid, null);
        }
    });
    grid.addEventListener('focusin', (e) => {
        if (!grid._pinned) {
            applyFocus(grid, traitRow(e.target));
        }
    });
    grid.addEventListener('focusout', (e) => {
        if (!grid._pinned && !grid.contains(e.relatedTarget)) {
            applyFocus(grid, null);
        }
    });
    grid.addEventListener('click', (e) => {
        const li = traitRow(e.target);
        if (li) {
            pin(li);
        } else if (grid._pinned) {
            pin(grid._pinned);
        }
    });
    grid.addEventListener('keydown', (e) => {
        const li = traitRow(e.target);
        if (e.key === 'Escape' && grid._pinned) {
            pin(grid._pinned);
        } else if (li && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            pin(li);
        }
    });
}

// Check copy k in a weapon card's picker, and name it on the grid host.
function checkCopy(card, k) {
    for (const entry of card.querySelectorAll('.pr')) {
        entry.querySelector('.pr-select').setAttribute('aria-checked', entry.dataset.k === k);
    }
    card.querySelector('[data-g]').dataset.k = k;
}

// Show copy k on a weapon card: checked, and the grid, once open, painted and
// lined for it.
function pickCopy(card, k) {
    checkCopy(card, k);
    const grid = card.querySelector('.pg');
    if (grid) {
        paintGrid(grid);
        applyFocus(grid, grid._pinned || null);
    }
}

// Perk search: each grid's perks, read from its template the first time a
// search needs them (perks): the ones the weapon can roll (every row but own,
// a perk only a copy has), the copies with each (data-o, their places on the
// card), and each perk's name (its tooltip's) and kind (its column's label,
// without the trait column's number).
let perkIndex = null;

function perks() {
    if (perkIndex) {
        return perkIndex;
    }
    const grids = new Map();
    const kinds = new Map();
    for (const t of document.querySelectorAll('template[id^="g"]')) {
        const rolls = new Set();
        const owners = new Map();
        for (const col of t.content.querySelectorAll('.pc')) {
            const kind = col.querySelector('.pc-label').textContent.replace(/ \d+$/, '');
            for (const li of col.querySelectorAll('.pk')) {
                const key = li.dataset.tip;
                if (!li.classList.contains('own')) {
                    rolls.add(key);
                }
                if (li.dataset.o) {
                    owners.set(key, li.dataset.o.split(' '));
                }
                if (!kinds.has(key)) {
                    kinds.set(key, kind);
                }
            }
        }
        grids.set(t.id.slice(1), { rolls, owners });
    }
    const names = new Map();
    for (const key of kinds.keys()) {
        names.set(key, document.getElementById('tip-' + key).querySelector('b').textContent);
    }
    perkIndex = { grids, kinds, names };
    return perkIndex;
}

// The places (data-k) of a weapon card's copies with every perk keys names,
// in the picker's order; all of them when keys is empty.
function copiesWith(card, keys) {
    const ks = [...card.querySelectorAll('.pr')].map((entry) => entry.dataset.k);
    if (!keys.length) {
        return ks;
    }
    const grid = perks().grids.get(card.querySelector('[data-g]').dataset.g);
    if (!grid) {
        return [];
    }
    return ks.filter((k) => keys.every((key) => (grid.owners.get(key) || []).includes(k)));
}

// Whether a Popular row's weapon can roll every perk keys names.
function rollsAll(row, keys) {
    if (!keys.length) {
        return true;
    }
    const grid = perks().grids.get(row.querySelector('[data-g]').dataset.g);
    return Boolean(grid) && keys.every((key) => grid.rolls.has(key));
}

// Grid hosts are watched as they come near the window (within 1000px): a host
// marked stale (a switch changed while it was away, or Expand all opened its
// card) opens then, so off-screen grids cost nothing until they're seen.
const watcher = new IntersectionObserver((entries) => {
    for (const e of entries) {
        e.target._near = e.isIntersecting;
        if (e.isIntersecting && e.target._stale) {
            openGrid(e.target);
        }
    }
}, { rootMargin: '1000px 0px' });

// Open the grid a host names (data-g: a Popular row's body, a weapon card's
// main column): cloned from its template the first time, then sorted for the
// side, its rings painted and its lines drawn. A weapon card's picker is
// sorted for the side too, and shows its first copy with the perks the page's
// perk search picked (its first copy without a search) until another is
// picked. A resized grid redraws its lines.
const resizer = new ResizeObserver((entries) => {
    for (const e of entries) {
        applyFocus(e.target, e.target._focus || null);
    }
});

function openGrid(host) {
    let grid = host.querySelector('.pg');
    if (!grid) {
        host.prepend(document.getElementById('g' + host.dataset.g).content.cloneNode(true));
        grid = host.querySelector('.pg');
        for (const li of grid.querySelectorAll('.pk')) {
            li.tabIndex = 0;
        }
        for (const li of grid.querySelectorAll('.pc[data-col^="trait"] .pk')) {
            li.setAttribute('role', 'button');
            li.setAttribute('aria-pressed', 'false');
        }
        bindGrid(grid);
        resizer.observe(grid);
    }
    host._stale = false;
    watcher.observe(host);
    const card = host.closest('.fam');
    if (card) {
        const picker = card.querySelector('.picker');
        sortBySide(picker);
        if (!host.dataset.k) {
            const k = copiesWith(card, card.closest('.page')._perks || [])[0];
            checkCopy(card, k || picker.firstElementChild.dataset.k);
        }
    }
    for (const list of grid.querySelectorAll('.pl')) {
        sortBySide(list);
    }
    paintGrid(grid);
    applyFocus(grid, grid._pinned || null);
}

// Open or refresh a grid host's grid now when it's near the window, else when
// it comes near.
function refresh(host) {
    if (host._near) {
        openGrid(host);
    } else {
        host._stale = true;
        watcher.observe(host);
    }
}

// The grid host of a card part a toggle opens: the part itself (a Popular
// row's body), or the one inside it (a weapon card's body); null for others.
function gridHost(target) {
    if (target.dataset.g) {
        return target;
    }
    return target.querySelector('[data-g]');
}

// Show a weapon card on a side: its switch pressed, and once its grid is open,
// its picker and grid in that side's order, lines and colours.
function setSide(card, side) {
    card.dataset.side = side;
    for (const b of card.querySelectorAll('.switch.side button')) {
        b.setAttribute('aria-pressed', b.dataset.value === side);
    }
    const grid = card.querySelector('.pg');
    if (grid) {
        refresh(grid.closest('[data-g]'));
    }
}

// The toolbar's filters (m.filters, on Popular and the weapons page): a
// Popular row or a weapon card shows when its name holds the search, it is of
// the type chosen, of a slot, an ammo type and an element chosen (any while
// none is; a weapon in several elements, of any of them), every pressed toggle
// holds (In my vault on Popular; Dupes, more than one copy, and Has wishlist,
// rolls in the list the wishlist switch shows or in any for All lists, on the
// weapons page), and it has every perk the perk search picked (a Popular
// weapon can roll them all, a card has a copy with them all). Each keeps
// whether the filters but the perks show it (_others), which the perk search
// counts from. The count is of Popular's side shown, or of the cards, whose
// sections are recounted.
function filterItems(page) {
    const search = page.querySelector('.toolbar .search');
    if (!search) {
        return;
    }
    const q = search.value.trim().toLowerCase();
    const type = page.querySelector('.type-select').value;
    const chosen = (name) => [...page.querySelectorAll(`.switch[data-filter="${name}"] [aria-pressed="true"]`)]
        .map((b) => b.dataset.value)
        .filter(Boolean);
    const pressed = (name) => {
        const b = page.querySelector(`button[data-filter="${name}"]`);
        return Boolean(b) && b.getAttribute('aria-pressed') === 'true';
    };
    const slots = chosen('slot');
    const ammo = chosen('ammo');
    const elements = chosen('element');
    const owned = pressed('owned');
    const dupes = pressed('dupes');
    const listed = pressed('listed');
    const list = page.querySelector('.switch[data-key="wl"] [aria-pressed="true"]');
    let wishlist = '*';
    if (list) {
        wishlist = list.dataset.value;
    }
    const keys = page._perks || [];
    let shown = 0;
    let total = 0;
    for (const item of page.querySelectorAll('.pop-row, .fam')) {
        const lists = (item.dataset.listed || '').split(' ').filter(Boolean);
        item._others = (!q || item.dataset.n.includes(q))
            && (!type || item.dataset.type === type)
            && (!slots.length || slots.includes(item.dataset.slot))
            && (!ammo.length || ammo.includes(item.dataset.ammo))
            && (!elements.length || item.dataset.element.split(' ').some((e) => elements.includes(e)))
            && (!owned || item.hasAttribute('data-owned'))
            && (!dupes || item.hasAttribute('data-dupes'))
            && (!listed || (wishlist === '*' && lists.length > 0) || lists.includes(wishlist));
        let show = item._others;
        if (show && keys.length) {
            if (item.classList.contains('fam')) {
                show = copiesWith(item, keys).length > 0;
            } else {
                show = rollsAll(item, keys);
            }
        }
        item.hidden = !show;
        if (!item.closest('.pops[hidden]')) {
            total += 1;
            shown += Number(show);
        }
    }
    page.querySelector('.shown').textContent = `${shown} of ${total} weapons`;
    page.querySelector('p.empty').hidden = shown > 0;
    countCards(page);
}

document.addEventListener('input', (e) => {
    if (e.target.matches('.search, .type-select')) {
        filterItems(e.target.closest('.page'));
    }
});
document.addEventListener('change', (e) => {
    if (e.target.matches('.type-select')) {
        filterItems(e.target.closest('.page'));
    }
});

// A double chevron's state: turned down (and its label Collapse all) while
// its section is rolled down.
function setRolled(button, open) {
    let label = 'Expand all';
    if (open) {
        label = 'Collapse all';
    }
    button.setAttribute('aria-expanded', open);
    button.setAttribute('aria-label', label);
    button.title = label;
}

// A group rolled down or up (a weapon section, or a class's armor sets): it,
// every section in it and every card in them (weapon cards, armor sets)
// opened or closed, their double chevrons turned to match.
function roll(group, open) {
    for (const d of [group, ...group.querySelectorAll('details')]) {
        if (d.tagName === 'DETAILS') {
            d.open = open;
        }
    }
    for (const t of group.querySelectorAll('.toggle')) {
        t.setAttribute('aria-expanded', open);
        const target = document.getElementById(t.getAttribute('aria-controls'));
        target.hidden = !open;
        const host = gridHost(target);
        if (open && host) {
            refresh(host);
        }
    }
    for (const b of group.querySelectorAll('.expand')) {
        setRolled(b, open);
    }
}

// A section closed by its own chevron: its double chevrons turn back, so the
// next one rolls it all down again.
document.addEventListener('toggle', (e) => {
    if (e.target.matches('details.fold') && !e.target.open) {
        for (const b of e.target.querySelectorAll('.expand')) {
            setRolled(b, false);
        }
    }
}, true);

// Switches: a page's elements show when their data-<key> names, among its
// space-separated values, the pressed value of every switch with that key: an
// armor page's class, Popular's side, the wishlist lines in the weapon cards'
// pickers. The grids open repaint, and the toolbar's filters run again (Has
// wishlist follows the wishlist switch).
function applySwitches(page) {
    const keys = new Set([...page.querySelectorAll('.switch[data-key]')].map((sw) => sw.dataset.key));
    for (const key of keys) {
        const pressed = [...page.querySelectorAll(`.switch[data-key="${key}"]`)]
            .map((sw) => [...sw.querySelectorAll('[aria-pressed="true"]')].map((b) => b.dataset.value));
        for (const el of page.querySelectorAll('[data-' + key + ']')) {
            const shows = el.dataset[key].split(' ');
            el.hidden = !pressed.every((values) => values.some((v) => shows.includes(v)));
        }
    }
    for (const grid of page.querySelectorAll('.pg')) {
        refresh(grid.closest('[data-g]'));
    }
    filterItems(page);
}

// Perk search (m.perk_search): the box suggests the perks the page searches
// whose names hold what is typed, a copy's on the weapons page and any a
// weapon can roll on Popular, each with its kind and how many of the weapons
// the other filters show it would leave. Picking one (Enter or a click) makes
// it a chip; a chip's x, or Backspace in the empty box, takes one off. The page
// shows the weapons with every perk picked (_perks), a weapon card opening on
// its first copy with them and its grid outlining them.

// The perks a page's search offers: the ones a copy of yours has on the
// weapons page, the ones a weapon can roll on Popular.
function perksOffered(page) {
    if (!page._offered) {
        const { grids } = perks();
        page._offered = new Set();
        for (const host of page.querySelectorAll('[data-g]')) {
            const grid = grids.get(host.dataset.g);
            if (!grid) {
                continue;
            }
            let keys = grid.rolls;
            if (host.closest('.fam')) {
                keys = grid.owners.keys();
            }
            for (const key of keys) {
                page._offered.add(key);
            }
        }
    }
    return page._offered;
}

// A counter of the weapons the page's other filters show that would show with
// every perk the keys it's given name: the cards with a copy with them all, or
// the Popular rows of the side shown whose weapon can roll them all.
function perkCounter(page) {
    const { grids } = perks();
    const cards = [...page.querySelectorAll('.fam')].filter((card) => card._others !== false);
    if (page.querySelector('.fam')) {
        const copies = cards.map((card) => ({
            ks: [...card.querySelectorAll('.pr')].map((entry) => entry.dataset.k),
            owners: (grids.get(card.querySelector('[data-g]').dataset.g) || { owners: new Map() }).owners,
        }));
        return (keys) => copies.filter(({ ks, owners }) => (
            ks.some((k) => keys.every((key) => (owners.get(key) || []).includes(k)))
        )).length;
    }
    const rolls = [...page.querySelectorAll('.pops:not([hidden]) > .pop-row')]
        .filter((row) => row._others !== false)
        .map((row) => (grids.get(row.querySelector('[data-g]').dataset.g) || { rolls: new Set() }).rolls);
    return (keys) => rolls.filter((set) => keys.every((key) => set.has(key))).length;
}

// A suggestion: the perk's name, the typed part marked, its kind and its count.
function perkOption(page, found, n, typed) {
    const { kinds } = perks();
    const li = document.createElement('li');
    li.id = page.id + '-perk-' + n;
    li.setAttribute('role', 'option');
    li.dataset.n = n;
    const name = document.createElement('span');
    const mark = document.createElement('mark');
    mark.textContent = found.name.slice(found.at, found.at + typed);
    name.append(found.name.slice(0, found.at), mark, found.name.slice(found.at + typed));
    const kind = document.createElement('span');
    kind.className = 'kind';
    kind.textContent = kinds.get(found.key);
    const count = document.createElement('span');
    count.className = 'count';
    if (!found.n) {
        li.classList.add('none');
        count.textContent = 'none with these';
    } else if (page.querySelector('.fam')) {
        count.textContent = found.n + ' of yours';
    } else {
        count.textContent = `${found.n} weapon${found.n === 1 ? '' : 's'}`;
    }
    li.append(name, kind, count);
    return li;
}

// Mark suggestion n the one Enter picks.
function activate(page, n) {
    page._active = n;
    for (const li of page.querySelectorAll('.perk-suggest [role="option"]')) {
        li.setAttribute('aria-selected', li.dataset.n === String(n));
    }
    page.querySelector('.perk-input').setAttribute('aria-activedescendant', page.id + '-perk-' + n);
}

function hideSuggest(page) {
    page.querySelector('.perk-suggest').hidden = true;
    const input = page.querySelector('.perk-input');
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
}

// Suggest the perks for what is typed: those starting with it first, then
// those with a word starting with it, each group by how many weapons it would
// leave, then by name; eight at most.
function suggestPerks(page) {
    const input = page.querySelector('.perk-input');
    const list = page.querySelector('.perk-suggest');
    const typed = input.value.trim();
    if (!typed) {
        hideSuggest(page);
        return;
    }
    const q = typed.toLowerCase();
    const { names } = perks();
    const picked = page._perks || [];
    const count = perkCounter(page);
    const found = [];
    for (const key of perksOffered(page)) {
        const name = names.get(key);
        const at = name.toLowerCase().indexOf(q);
        if (at < 0 || picked.includes(key)) {
            continue;
        }
        let score = 2;
        if (at === 0) {
            score = 0;
        } else if (/[\s-]/.test(name[at - 1])) {
            score = 1;
        }
        found.push({ key, name, at, score, n: count([...picked, key]) });
    }
    found.sort((a, b) => a.score - b.score || b.n - a.n || a.name.localeCompare(b.name));
    page._found = found.slice(0, 8);
    list.replaceChildren(...page._found.map((f, n) => perkOption(page, f, n, q.length)));
    if (!page._found.length) {
        const li = document.createElement('li');
        li.className = 'empty';
        let where = 'a weapon can roll';
        if (page.querySelector('.fam')) {
            where = 'on your copies';
        }
        li.textContent = `No perk ${where} matches "${typed}".`;
        list.append(li);
    }
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    if (page._found.length) {
        activate(page, 0);
    }
}

// A page's picked perks as chips in its box, before the text it takes.
function renderPerks(page) {
    const { names, kinds } = perks();
    const input = page.querySelector('.perk-input');
    for (const chip of page.querySelectorAll('.perk-chip')) {
        chip.remove();
    }
    for (const key of page._perks) {
        const chip = document.createElement('span');
        chip.className = 'perk-chip';
        const kind = document.createElement('span');
        kind.className = 'kind';
        kind.textContent = kinds.get(key);
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.dataset.key = key;
        remove.setAttribute('aria-label', 'Remove ' + names.get(key));
        remove.textContent = '\u00d7';
        chip.append(names.get(key), kind, remove);
        input.before(chip);
    }
    input.placeholder = 'Search perks';
    if (page._perks.length) {
        input.placeholder = 'Add a perk';
    }
}

// Set a page's picked perks and show the weapons with them all: on the
// weapons page each copy with them says so and an open card showing a copy
// without them shows the first with them; the toolbar's filters run again and
// the open grids repaint.
function setPerks(page, keys) {
    page._perks = keys;
    renderPerks(page);
    const cards = page.querySelectorAll('.fam');
    for (const card of cards) {
        const ks = copiesWith(card, keys);
        for (const entry of card.querySelectorAll('.pr')) {
            entry.querySelector('.has-perks').hidden = !keys.length || !ks.includes(entry.dataset.k);
        }
        const host = card.querySelector('[data-g]');
        if (keys.length && ks.length && host.dataset.k && !ks.includes(host.dataset.k)) {
            checkCopy(card, ks[0]);
        }
    }
    filterItems(page);
    for (const grid of page.querySelectorAll('.pg')) {
        refresh(grid.closest('[data-g]'));
    }
}

function pickPerk(page, n) {
    const input = page.querySelector('.perk-input');
    setPerks(page, [...(page._perks || []), page._found[n].key]);
    input.value = '';
    hideSuggest(page);
    input.focus();
}

document.addEventListener('input', (e) => {
    if (e.target.matches('.perk-input')) {
        suggestPerks(e.target.closest('.page'));
    }
});
document.addEventListener('focusin', (e) => {
    if (e.target.matches('.perk-input')) {
        suggestPerks(e.target.closest('.page'));
    }
});
document.addEventListener('focusout', (e) => {
    if (e.target.matches('.perk-input')) {
        hideSuggest(e.target.closest('.page'));
    }
});
document.addEventListener('keydown', (e) => {
    if (!e.target.matches('.perk-input')) {
        return;
    }
    const page = e.target.closest('.page');
    const open = !page.querySelector('.perk-suggest').hidden && page._found && page._found.length;
    if (e.key === 'ArrowDown' && open) {
        e.preventDefault();
        activate(page, (page._active + 1) % page._found.length);
    } else if (e.key === 'ArrowUp' && open) {
        e.preventDefault();
        activate(page, (page._active - 1 + page._found.length) % page._found.length);
    } else if (e.key === 'Enter' && open) {
        e.preventDefault();
        pickPerk(page, page._active);
    } else if (e.key === 'Escape') {
        hideSuggest(page);
    } else if (e.key === 'Backspace' && !e.target.value && page._perks && page._perks.length) {
        setPerks(page, page._perks.slice(0, -1));
    }
});
// A suggestion picks on mousedown, before the box loses focus; a click in the
// box focuses it, and a chip's x takes its perk off.
document.addEventListener('mousedown', (e) => {
    const option = e.target.closest('.perk-suggest [role="option"]');
    if (option) {
        e.preventDefault();
        pickPerk(option.closest('.page'), Number(option.dataset.n));
    }
});
document.addEventListener('click', (e) => {
    const field = e.target.closest('.perk-field');
    if (!field) {
        return;
    }
    const page = field.closest('.page');
    const remove = e.target.closest('.perk-chip button');
    if (remove) {
        setPerks(page, page._perks.filter((key) => key !== remove.dataset.key));
    }
    field.querySelector('.perk-input').focus();
});

// Clear a page's toolbar filters: the searches and the type, the multi
// switches back to All and the filter toggles off (setPerks runs them).
function clearFilters(page) {
    page.querySelector('.toolbar .search').value = '';
    page.querySelector('.type-select').value = '';
    for (const sw of page.querySelectorAll('.toolbar .switch.multi')) {
        for (const b of sw.children) {
            b.setAttribute('aria-pressed', b === sw.firstElementChild);
        }
    }
    for (const b of page.querySelectorAll('.toolbar button[data-filter]')) {
        b.setAttribute('aria-pressed', 'false');
    }
    setPerks(page, []);
}

// My Copies: a weapons page card by its grid's id (a flagged copy's
// keeper's, a Popular weapon's), on the side given, with copy k picked when
// given. The weapons page shows first when another does (its own history
// entry, so Back returns), the toolbar's filters clear when they hide the
// card, its sections and the card open, and it scrolls into view, flashed.
function goToCard(grid, k, side) {
    const card = document.getElementById('fam-' + grid).closest('.fam');
    const page = card.closest('.page');
    if (page.hidden) {
        history.pushState(null, '', '#' + page.id.slice('page-'.length));
        route();
    }
    if (card.hidden) {
        clearFilters(page);
    }
    for (let d = card.closest('details'); d; d = d.parentElement.closest('details')) {
        d.open = true;
    }
    if (side) {
        setSide(card, side);
    }
    const toggle = card.querySelector('.toggle');
    if (toggle.getAttribute('aria-expanded') !== 'true') {
        toggle.click();
    }
    if (k) {
        pickCopy(card, k);
    }
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    card.classList.remove('flash');
    void card.offsetWidth;
    card.classList.add('flash');
}

document.addEventListener('click', (e) => {
    // A switch: one button pressed at a time, the page's elements shown to
    // match (applySwitches). A multi switch's buttons each toggle beside its
    // All, which clears them, and a flip switch's buttons each flip: both run
    // the toolbar's filters (filterItems), but the weapons page's order
    // toggles (data-sort) order the cards (sortCards). A side switch sets the
    // side of its weapon card, or of every card for the page's Popularity
    // switch, which orders the cards again.
    const button = e.target.closest('.switch button');
    if (button && button.closest('.switch.multi')) {
        const all = button.parentElement.children[0];
        if (button === all) {
            for (const b of button.parentElement.children) {
                b.setAttribute('aria-pressed', b === all);
            }
        } else {
            button.setAttribute('aria-pressed', button.getAttribute('aria-pressed') !== 'true');
            const any = [...button.parentElement.children].some((b) => b !== all && b.getAttribute('aria-pressed') === 'true');
            all.setAttribute('aria-pressed', !any);
        }
        filterItems(button.closest('.page'));
    } else if (button && button.closest('.switch.flip')) {
        button.setAttribute('aria-pressed', button.getAttribute('aria-pressed') !== 'true');
        if (button.dataset.sort) {
            sortCards(button.closest('.page'));
        } else {
            filterItems(button.closest('.page'));
        }
    } else if (button && button.closest('.switch.side')) {
        for (const b of button.parentElement.children) {
            b.setAttribute('aria-pressed', b === button);
        }
        let cards = [button.closest('.fam')];
        if (!cards[0]) {
            cards = button.closest('.page').querySelectorAll('.fam');
            sortCards(button.closest('.page'));
        }
        for (const card of cards) {
            setSide(card, button.dataset.value);
        }
    } else if (button) {
        for (const b of button.parentElement.children) {
            b.setAttribute('aria-pressed', b === button);
        }
        applySwitches(button.closest('.page'));
    }

    // A double chevron rolls its whole group down or up: the weapon section
    // it leads (not just its own fold), or the class's armor sets.
    const expand = e.target.closest('.expand');
    if (expand) {
        e.preventDefault();
        roll(expand.closest('details, .cls'), expand.getAttribute('aria-expanded') !== 'true');
    }

    // Disclosure buttons (a weapon card's, armor set's or Popular weapon's
    // name): show or hide the part of the card the button controls.
    const toggle = e.target.closest('.toggle');
    if (toggle) {
        const open = toggle.getAttribute('aria-expanded') !== 'true';
        toggle.setAttribute('aria-expanded', open);
        const target = document.getElementById(toggle.getAttribute('aria-controls'));
        target.hidden = !open;
        const host = gridHost(target);
        if (open && host) {
            openGrid(host);
        }
    }

    // My Copies: a flagged copy's opens its keeper's card, a Popular
    // weapon's its card, on the side of the list it's in.
    const goto = e.target.closest('.goto');
    if (goto) {
        const list = goto.closest('.pops');
        let side = null;
        if (list) {
            side = list.dataset.side;
        }
        goToCard(goto.dataset.goto, goto.dataset.k, side);
    }

    // A weapon card's picker entry shows its copy.
    const entry = e.target.closest('.pr-select');
    if (entry) {
        pickCopy(entry.closest('.fam'), entry.parentElement.dataset.k);
    }

    // Copy buttons (a DIM query: id:<n> for one copy, or several joined by
    // or): copy data-q, or show it to copy by hand when the clipboard refuses.
    // A text button says Copied for a moment; an icon button (one copy's)
    // turns green.
    const copier = e.target.closest('[data-q]');
    if (copier) {
        copier.dataset.label ??= copier.textContent;
        navigator.clipboard.writeText(copier.dataset.q).then(() => {
            if (copier.dataset.label) {
                copier.textContent = 'Copied';
            }
            copier.classList.add('copied');
            setTimeout(() => {
                if (copier.dataset.label) {
                    copier.textContent = copier.dataset.label;
                }
                copier.classList.remove('copied');
            }, 1200);
        }, () => prompt('Copy this', copier.dataset.q));
    }
});

// Setting the report up: when it loads, and again when the static site (which
// builds this report in the browser) swaps a newer one into the page as the
// player's inventory changes, updating in place as DIM does. reportState
// notes what the player has set on each page: its pressed switches, the
// toolbar's search, type, perks and half-typed perk, its folds, the cards,
// armor sets and Popular weapons open (and which had their grid out), and
// each weapon card's side and copy shown, by the copy's id, since its place on
// the card moves as copies come and go; then the field being typed in, and
// the card at the top of the window. setupReport shows the page the address
// names and runs the toolbar's filters, and given that state puts it back,
// the same card where it was in the window.

// A switch button's value: its data-value, or a flip's data-filter or
// data-sort.
function buttonKey(b) {
    return b.dataset.value ?? b.dataset.filter ?? b.dataset.sort;
}

// The fields a page's state notes.
const FIELDS = ['.toolbar .search', '.type-select', '.perk-input'];

// The card at the top of the window, just under the header (a weapon card,
// armor set or Popular weapon): its disclosure's target and how far down the
// window it starts; and the scroll offset, for when there's none or it's gone.
function topItem() {
    const y = document.querySelector('.top').getBoundingClientRect().bottom + 1;
    const el = document.elementFromPoint(innerWidth / 2, y);
    const item = el && el.closest('.card');
    const toggle = item && item.querySelector('.toggle');
    if (!toggle) {
        return { y: scrollY };
    }
    return { id: toggle.getAttribute('aria-controls'), top: item.getBoundingClientRect().top, y: scrollY };
}

function reportState() {
    const pages = {};
    for (const page of document.querySelectorAll('.page')) {
        const switches = {};
        for (const sw of page.querySelectorAll('.switch:not(.mini)')) {
            switches[sw.getAttribute('aria-label')] = [...sw.querySelectorAll('[aria-pressed="true"]')].map(buttonKey);
        }
        const fields = {};
        for (const selector of FIELDS) {
            const field = page.querySelector(selector);
            if (field) {
                fields[selector] = field.value;
            }
        }
        const open = {};
        const grids = [];
        for (const t of page.querySelectorAll('.toggle')) {
            const id = t.getAttribute('aria-controls');
            open[id] = t.getAttribute('aria-expanded') === 'true';
            const host = gridHost(document.getElementById(id));
            if (host && host.querySelector('.pg')) {
                grids.push(id);
            }
        }
        const cards = {};
        for (const card of page.querySelectorAll('.fam')) {
            const host = card.querySelector('[data-g]');
            const entry = card.querySelector(`.pr[data-k="${host.dataset.k}"]`);
            let copy = null;
            if (entry) {
                copy = entry.querySelector('.pr-id').textContent;
            }
            cards[host.dataset.g] = { side: card.dataset.side, copy };
        }
        pages[page.id] = {
            switches,
            fields,
            perks: page._perks || [],
            folds: [...page.querySelectorAll('details')].map((d) => d.open),
            rolled: [...page.querySelectorAll('.expand')].map((b) => b.getAttribute('aria-expanded') === 'true'),
            open,
            grids,
            cards,
        };
    }
    let focus = null;
    const active = document.activeElement;
    const page = active && active.closest('.page');
    const selector = page && FIELDS.find((s) => active.matches(s));
    if (selector) {
        focus = { page: page.id, selector, start: active.selectionStart, end: active.selectionEnd };
    }
    return { pages, focus, top: topItem() };
}

// Put a page's noted state back on the new report's HTML. A value the new
// report no longer offers (an element none of the copies comes in any more)
// leaves its switch on its first button, All, and a card, armor set or fold
// the old report didn't have keeps the new report's default. A grid that was
// out is cloned again at once, so the page is as tall as it was; one of a
// card opened but never brought near the window opens when it comes near.
function restorePage(page, saved) {
    for (const sw of page.querySelectorAll('.switch:not(.mini)')) {
        const pressed = saved.switches[sw.getAttribute('aria-label')];
        if (!pressed) {
            continue;
        }
        const buttons = [...sw.querySelectorAll('button')];
        for (const b of buttons) {
            b.setAttribute('aria-pressed', pressed.includes(buttonKey(b)));
        }
        if (!sw.matches('.flip') && !buttons.some((b) => b.getAttribute('aria-pressed') === 'true')) {
            buttons[0].setAttribute('aria-pressed', 'true');
        }
    }
    for (const [selector, value] of Object.entries(saved.fields)) {
        const field = page.querySelector(selector);
        if (field) {
            field.value = value;
        }
    }
    const folds = page.querySelectorAll('details');
    if (folds.length === saved.folds.length) {
        folds.forEach((d, i) => {
            d.open = saved.folds[i];
        });
    }
    const rolled = page.querySelectorAll('.expand');
    if (rolled.length === saved.rolled.length) {
        rolled.forEach((b, i) => setRolled(b, saved.rolled[i]));
    }
    for (const card of page.querySelectorAll('.fam')) {
        const host = card.querySelector('[data-g]');
        const was = saved.cards[host.dataset.g];
        if (!was) {
            continue;
        }
        setSide(card, was.side);
        const entry = [...card.querySelectorAll('.pr')].find((e) => e.querySelector('.pr-id').textContent === was.copy);
        if (entry) {
            checkCopy(card, entry.dataset.k);
        }
    }
    if (saved.perks.length) {
        const { names } = perks();
        page._perks = saved.perks.filter((key) => names.has(key));
    }
    const grids = new Set(saved.grids);
    for (const t of page.querySelectorAll('.toggle')) {
        const id = t.getAttribute('aria-controls');
        if (!(id in saved.open)) {
            continue;
        }
        const open = saved.open[id];
        t.setAttribute('aria-expanded', open);
        const target = document.getElementById(id);
        target.hidden = !open;
        const host = gridHost(target);
        if (open && host && grids.has(id)) {
            openGrid(host);
        } else if (open && host) {
            refresh(host);
        }
    }
    if (page._perks) {
        setPerks(page, page._perks);
    }
    applySwitches(page);
    sortCards(page);
}

function setupReport(state) {
    tip = document.getElementById('tip');
    perkIndex = null;
    queued.clear();
    watcher.disconnect();
    resizer.disconnect();
    route();
    for (const page of document.querySelectorAll('.page')) {
        const saved = state && state.pages[page.id];
        if (saved) {
            restorePage(page, saved);
        } else {
            filterItems(page);
        }
    }
    if (!state) {
        return;
    }
    const page = state.focus && document.getElementById(state.focus.page);
    const field = page && page.querySelector(state.focus.selector);
    if (field) {
        field.focus({ preventScroll: true });
        if (field.setSelectionRange && state.focus.start !== null) {
            field.setSelectionRange(state.focus.start, state.focus.end);
        }
    }
    const target = state.top.id && document.getElementById(state.top.id);
    const item = target && target.closest('.card');
    if (item && item.getClientRects().length) {
        scrollTo(0, item.getBoundingClientRect().top + scrollY - state.top.top);
    } else {
        scrollTo(0, state.top.y);
    }
}

setupReport();
