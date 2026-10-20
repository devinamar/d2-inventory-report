// The report's behaviour: page tabs by URL hash, class, weapon and wishlist
// switches, sorting a weapon family's copies, opening weapon families and
// armor sets (one by one, or a group at a time by its double chevron), perk
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

// Perk tooltips: one fixed element filled from the perk's tip-<plug hash>
// block, and for a wishlist pick the lists naming it, above the perk when it
// fits, else below.
const tip = document.getElementById('tip');
function showTip(e) {
    const perk = e.target.closest('[data-tip]');
    const source = perk && document.getElementById('tip-' + perk.dataset.tip);
    if (!source) {
        tip.hidden = true;
        return;
    }
    tip.innerHTML = source.innerHTML;
    if (perk.dataset.named) {
        const named = document.createElement('p');
        named.className = 'named';
        named.textContent = 'Named by ' + perk.dataset.named;
        tip.append(named);
    }
    tip.hidden = false;
    const r = perk.getBoundingClientRect();
    const above = r.top - tip.offsetHeight - 6;
    tip.style.left = Math.max(8, Math.min(r.left, innerWidth - tip.offsetWidth - 8)) + 'px';
    if (above >= 8) {
        tip.style.top = above + 'px';
    } else {
        tip.style.top = r.bottom + 6 + 'px';
    }
}

document.addEventListener('mouseover', showTip);

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
        document.getElementById(t.getAttribute('aria-controls')).hidden = !open;
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

    const button = e.target.closest('.switch button');
    if (button) {
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
        document.getElementById(toggle.getAttribute('aria-controls')).hidden = !open;
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
