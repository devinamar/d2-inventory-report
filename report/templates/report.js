// The report's behaviour: page tabs by URL hash, class, weapon, side and
// wishlist switches, sorting a weapon family's copies, opening weapon
// families, armor sets and Popular's weapons (one by one, or a group at a
// time by its double chevron), the perk grids they open, Popular's filters,
// tooltips and copying DIM queries and ids.

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
route();

// A side's scope: the closest element that names a side (a Popular list, a
// weapons card), PvE outside one.
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
// per side), and for an old Roll Quality wishlist pick the lists naming it. A
// grid row's adds its rank on the side shown, the shown lists naming it and,
// while a trait is focused, its pair with that trait. It sits above its
// element when it fits, else below; a trait's sits beside its column (left of
// Trait 1, right of Trait 2), clear of the pair lines between them.
const tip = document.getElementById('tip');
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
        line.textContent = `Paired with ${p.with} on ${pct(p.cond)} of its rolls: ${pct(p.share)} of all ${SIDE_LABELS[side]} pairs, #${p.rank}`;
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
    } else if (perk.dataset.named) {
        const named = document.createElement('p');
        named.className = 'named';
        named.textContent = 'Named by ' + perk.dataset.named;
        tip.append(named);
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
function countFamilies(page) {
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
addEventListener('scroll', () => { tip.hidden = true; }, { passive: true });

// Perk grids (grids.html.j2): a grid's template is cloned into a Popular
// row or a weapons card the first time it opens. Its rows go in the order of
// the side shown (data-r holds each side's place), its perks named by a list
// the wishlist switch shows get that list's ring (data-l holds the places of
// the lists naming each), and its trait pairs' lines are drawn from its paths
// (each side's figures in data-pve and data-pvp). Hovering or focusing a trait
// focuses it: its partners light up, tinted and lined by how often players
// pair them, and the rest fade. Clicking it, or Enter, pins the focus until
// Esc or another click.

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

// A grid's rows in its side's order.
function sortGrid(grid) {
    const i = Number(sideOf(grid) === 'pvp');
    for (const list of grid.querySelectorAll('.pl')) {
        const rows = [...list.children];
        rows.sort((a, b) => a.dataset.r.split(' ')[i] - b.dataset.r.split(' ')[i]);
        list.append(...rows);
    }
}

// A grid's wishlist rings: each perk named by a list shown is ringed (pick) in
// those lists' colours (l<places>).
function paintGrid(grid) {
    const shown = placeShown(grid.closest('.page'));
    for (const li of grid.querySelectorAll('.pk')) {
        for (const c of [...li.classList]) {
            if (c === 'pick' || /^l\d/.test(c)) {
                li.classList.remove(c);
            }
        }
        let places = (li.dataset.l || '').split(' ').filter(Boolean);
        if (shown) {
            places = places.filter((place) => place === shown);
        }
        if (places.length) {
            li.classList.add('pick', 'l' + places.join('-'));
        }
    }
}

// A pair's figures on a side, from its line's path: its rank, rel, share,
// each trait's share with the other (c1, c2) and the other's rank among its
// partners (n1, n2); null when the side has no votes for it.
function pairOn(path, side) {
    const figures = path.dataset[side];
    if (!figures) {
        return null;
    }
    const [rank, rel, share, c1, c2, n1, n2] = figures.split(' ').map(Number);
    return { path, rank, rel, share, c1, c2, n1, n2 };
}

// How strongly a line shows: steeply fainter as its pair's share drops.
function fade(rel) {
    return 0.12 + 0.88 * rel * rel;
}

// Draw a pair's line from its first trait's row to its second's, in grid
// coordinates (box, the grid's rectangle).
function drawLine(box, from, to, pair, cls, width, opacity, color) {
    const a = from.getBoundingClientRect();
    const b = to.getBoundingClientRect();
    const x1 = a.right - box.left;
    const y1 = a.top + a.height / 2 - box.top;
    const x2 = b.left - box.left;
    const y2 = b.top + b.height / 2 - box.top;
    const mx = (x1 + x2) / 2;
    const p = pair.path;
    p.setAttribute('d', `M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`);
    p.setAttribute('class', cls);
    p.setAttribute('stroke-width', width);
    p.setAttribute('stroke-opacity', opacity.toFixed(2));
    p.style.stroke = color;
    p.style.display = '';
}

// The trait columns in focus: a focused trait's six most run partners light
// up (tinted, with their share of its rolls) and are lined, weighted by how
// often players pick the pair; the other traits fade, and so do the other
// columns. Without a focus, the side's three most picked pairs are lined.
function applyFocus(grid, focus) {
    grid._focus = focus;
    for (const li of grid.querySelectorAll('.pk')) {
        li.classList.remove('focus', 'partner', 'dim');
        li.style.opacity = '';
        li.style.removeProperty('--heat');
        delete li.dataset.f;
        li._pair = null;
        if (li.hasAttribute('aria-pressed')) {
            li.setAttribute('aria-pressed', li === grid._pinned);
        }
    }
    for (const list of grid.querySelectorAll('.pl.soft')) {
        list.classList.remove('soft');
    }
    const svg = grid.querySelector('.links');
    const paths = [...svg.children];
    for (const p of paths) {
        p.style.display = 'none';
    }
    const t1 = grid.querySelector('.pc[data-col="trait1"]');
    const t2 = grid.querySelector('.pc[data-col="trait2"]');
    const box = grid.getBoundingClientRect();
    if (!t1 || !t2 || !box.width) {
        return;
    }
    const side = sideOf(grid);
    const row = (col, key) => col.querySelector(`[data-tip="${key}"]`);
    const pairs = paths.map((p) => pairOn(p, side)).filter(Boolean);
    pairs.sort((x, y) => x.rank - y.rank);
    if (focus) {
        const first = t1.contains(focus);
        const key = focus.dataset.tip;
        const mine = pairs.filter((p) => p.path.dataset[first ? 'a' : 'b'] === key);
        mine.sort((x, y) => (first ? x.n1 - y.n1 : x.n2 - y.n2));
        const partners = mine.slice(0, 6);
        let top = 1;
        if (partners.length) {
            top = partners[0].share;
        }
        focus.classList.add('focus');
        for (const li of [...t1.querySelectorAll('.pk'), ...t2.querySelectorAll('.pk')]) {
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
            let cond = p.c2;
            if (first) {
                cond = p.c1;
            }
            other.classList.replace('dim', 'partner');
            other.style.opacity = (0.3 + 0.7 * (p.share / top) ** 2).toFixed(2);
            other.style.setProperty('--heat', heat(p.rel));
            other.dataset.f = pct(cond);
            other._pair = { with: focus.textContent, cond, share: p.share, rank: p.rank, rel: p.rel };
            const [from, to] = first ? [focus, other] : [other, focus];
            drawLine(box, from, to, p, 'hover', 1 + 5 * p.rel, Math.max(0.25, fade(p.rel)), heat(p.rel));
        }
        for (const list of grid.querySelectorAll('.pc:not([data-col^="trait"]) .pl')) {
            list.classList.add('soft');
        }
    } else {
        for (const p of pairs.slice(0, 3)) {
            const from = row(t1, p.path.dataset.a);
            const to = row(t2, p.path.dataset.b);
            if (from && to) {
                drawLine(box, from, to, p, 'good', 1 + 5 * p.rel, fade(p.rel), heat(p.rel));
            }
        }
    }
    svg.setAttribute('width', box.width);
    svg.setAttribute('height', box.height);
    svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`);
}

// A grid's focus follows the pointer and keyboard over its traits; a click
// or Enter pins it, and Esc, or a click elsewhere in the grid, unpins it.
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
        if (!grid._pinned && li !== grid._focus) {
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

// Open the grid a host names (data-g: a Popular row's body): cloned from its
// template the first time, then sorted for the side, its rings painted and
// its lines drawn. A resized grid redraws its lines.
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
    sortGrid(grid);
    paintGrid(grid);
    applyFocus(grid, grid._pinned || null);
}

// Popular's filters: a row shows when its name holds the search, it is of the
// type chosen, of a slot and an ammo type chosen (any while none is), and in
// the vault while In my vault is pressed. The count is the shown side's.
function filterPopular(page) {
    const search = page.querySelector('.search');
    if (!search) {
        return;
    }
    const q = search.value.trim().toLowerCase();
    const type = page.querySelector('.type-select').value;
    const chosen = (name) => [...page.querySelectorAll(`.switch[data-filter="${name}"] [aria-pressed="true"]`)]
        .map((b) => b.dataset.value)
        .filter(Boolean);
    const slots = chosen('slot');
    const ammo = chosen('ammo');
    const owned = page.querySelector('[data-filter="owned"]').getAttribute('aria-pressed') === 'true';
    let shown = 0;
    let total = 0;
    for (const list of page.querySelectorAll('.pops')) {
        for (const row of list.children) {
            const show = (!q || row.dataset.n.includes(q))
                && (!type || row.dataset.type === type)
                && (!slots.length || slots.includes(row.dataset.slot))
                && (!ammo.length || ammo.includes(row.dataset.ammo))
                && (!owned || row.hasAttribute('data-owned'));
            row.hidden = !show;
            if (!list.hidden) {
                total += 1;
                shown += Number(show);
            }
        }
    }
    page.querySelector('.shown').textContent = `${shown} of ${total} weapons`;
    page.querySelector('.empty').hidden = shown > 0;
}

for (const page of document.querySelectorAll('.page')) {
    filterPopular(page);
}
document.addEventListener('input', (e) => {
    if (e.target.matches('.search, .type-select')) {
        filterPopular(e.target.closest('.page'));
    }
});
document.addEventListener('change', (e) => {
    if (e.target.matches('.type-select')) {
        filterPopular(e.target.closest('.page'));
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
// every section in it and every card in them (weapon families, armor sets)
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
        if (open && target.dataset.g) {
            openGrid(target);
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
// space-separated values, the pressed value of every switch with that key.
// Has wishlist (listed) stands for the list the wishlist switch shows:
// listed-<key>, or listed-* for All lists. The weapon sections are recounted.
function applySwitches(page) {
    const list = page.querySelector('.switch[data-key="wl"] [aria-pressed="true"]');
    const keys = new Set([...page.querySelectorAll('.switch')].map((sw) => sw.dataset.key));
    for (const key of keys) {
        const pressed = page.querySelectorAll(`.switch[data-key="${key}"] [aria-pressed="true"]`);
        const values = [...pressed].map((b) => {
            if (b.dataset.value === 'listed') {
                return 'listed-' + (list ? list.dataset.value : '*');
            }
            return b.dataset.value;
        });
        for (const el of page.querySelectorAll('[data-' + key + ']')) {
            const shows = el.dataset[key].split(' ');
            el.hidden = !values.every((value) => shows.includes(value));
        }
    }
    countFamilies(page);
    for (const grid of page.querySelectorAll('.pg')) {
        paintGrid(grid);
        applyFocus(grid, grid._pinned || null);
    }
    filterPopular(page);
}

// Roll Quality's sorts, one per family across its tables: by score (the
// report's ranking, or its reverse) or by element (A to Z or Z to A, ties by
// instance id). The Wishlist row stays first.
function byId(a, b) {
    const x = a.dataset.id;
    const y = b.dataset.id;
    if (x.length !== y.length) {
        return x.length - y.length;
    }
    if (x < y) {
        return -1;
    }
    if (x > y) {
        return 1;
    }
    return 0;
}
const ORDERS = {
    'score-desc': (a, b) => b.dataset.score - a.dataset.score || a.dataset.n - b.dataset.n,
    'score-asc': (a, b) => a.dataset.score - b.dataset.score || b.dataset.n - a.dataset.n,
    'element-asc': (a, b) => a.dataset.element.localeCompare(b.dataset.element) || byId(a, b),
    'element-desc': (a, b) => b.dataset.element.localeCompare(a.dataset.element) || byId(a, b),
};

// Sort a family's tables by mode (like 'element-asc'), and mark the active
// header: cyan, its arrow up for ascending, and aria-sort.
function sortFamily(body, mode) {
    body.dataset.sort = mode;
    const [key, dir] = mode.split('-');
    for (const table of body.querySelectorAll('table.rolls')) {
        const tbody = table.tBodies[0];
        const rows = [...tbody.rows].filter((r) => !r.classList.contains('wish'));
        rows.sort(ORDERS[mode]);
        tbody.append(...rows);
        for (const th of table.tHead.rows[0].cells) {
            const button = th.querySelector('.sort');
            if (!button) {
                continue;
            }
            const on = button.dataset.sort === key;
            button.classList.toggle('on', on);
            button.classList.toggle('asc', on && dir === 'asc');
            let sort = 'none';
            if (on && dir === 'asc') {
                sort = 'ascending';
            } else if (on) {
                sort = 'descending';
            }
            th.setAttribute('aria-sort', sort);
        }
    }
}

document.addEventListener('click', (e) => {
    // A sort header: the active sort flips direction; the other starts at
    // score's best first, or element's A to Z.
    const sorter = e.target.closest('.sort');
    if (sorter) {
        const body = sorter.closest('.fam-body');
        const current = body.dataset.sort || 'score-desc';
        const key = sorter.dataset.sort;
        let mode = key + '-asc';
        if (key === 'score') {
            mode = 'score-desc';
        }
        if (mode === current && current.endsWith('-asc')) {
            mode = key + '-desc';
        } else if (mode === current) {
            mode = key + '-asc';
        }
        sortFamily(body, mode);
    }

    // A switch: one button pressed at a time, the page's elements shown to
    // match (applySwitches). A multi switch's buttons each toggle beside its
    // All, which clears them; a flip switch's one button flips. Both filter
    // Popular.
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
        filterPopular(button.closest('.page'));
    } else if (button && button.closest('.switch.flip')) {
        button.setAttribute('aria-pressed', button.getAttribute('aria-pressed') !== 'true');
        filterPopular(button.closest('.page'));
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

    // Disclosure buttons (a weapon family's or armor set's name): show or
    // hide the part of the card the button controls.
    const toggle = e.target.closest('.toggle');
    if (toggle) {
        const open = toggle.getAttribute('aria-expanded') !== 'true';
        toggle.setAttribute('aria-expanded', open);
        const target = document.getElementById(toggle.getAttribute('aria-controls'));
        target.hidden = !open;
        if (open && target.dataset.g) {
            openGrid(target);
        }
    }

    // Copy buttons (a DIM query, a copy's id): copy data-q, or show it to
    // copy by hand when the clipboard refuses.
    const copier = e.target.closest('[data-q]');
    if (copier) {
        copier.dataset.label ??= copier.textContent;
        navigator.clipboard.writeText(copier.dataset.q).then(() => {
            copier.textContent = 'Copied';
            setTimeout(() => { copier.textContent = copier.dataset.label; }, 1200);
        }, () => prompt('Copy this', copier.dataset.q));
    }
});
