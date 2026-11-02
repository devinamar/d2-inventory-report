# Tests for the report's Popular page (report/templates/popular.html.j2): the
# side switch, the toolbar's filters, and each scored weapon's row, which
# opens its grid.
from tests import conftest as c


def popular_page(conn, folder):
    html, _ = c.write_report(conn, folder)
    return c.report_page(html, 'popular')


def add_scored(conn):
    # Gun (Pantheon), one trait pool of Gun, rank 3 on PvE, Endgame there, its
    # trait column scored; Rifle rank 1 on PvP. The vault holds a Gun.
    c.add_weapon_def(conn, 100, name='Gun', ammoType=2)
    c.add_weapon_def(conn, 200, name='Rifle', ammoType=1)
    c.add_popularity(
        conn,
        'Gun (Pantheon)',
        [100],
        family='Gun',
        rank=3,
        hard_copies=60,
        columns=[c.popularity_column('trait1', [('Rampage', 0.7)], n_eff=40.0)],
    )
    c.add_popularity(conn, 'Rifle', [200], side='pvp')
    c.add_copy(conn, 'a', 100)


def test_the_side_switch_counts_each_sides_weapons_and_the_toolbar_offers_their_kinds(
    conn, tmp_path
):
    add_scored(conn)
    page = popular_page(conn, tmp_path)
    assert (
        '<button type="button" class="side-pve" data-value="pve" aria-pressed="true">'
        'PvE <span class="num">1</span></button>'
    ) in page
    assert '<option>Auto Rifle</option>' in page
    assert (
        '<button type="button" data-value="Kinetic Weapons" aria-pressed="false">Kinetic</button>'
        in page
    )
    assert 'data-value="special" aria-pressed="false"><img src=' in page
    assert '<div class="switch flip" role="group" aria-label="Vault">' in page


def test_a_row_names_its_pool_badges_and_most_picked_and_opens_its_grid(conn, tmp_path):
    add_scored(conn)
    page = popular_page(conn, tmp_path)
    pve = page.split('<div class="pops" data-side="pve">')[1].split('</article>')[0]
    assert (
        '<article class="card pop-row" data-n="gun (pantheon)" data-type="Auto Rifle" '
        'data-slot="Kinetic Weapons" data-ammo="special" data-element="Kinetic" data-owned="">'
    ) in pve
    assert '<span class="pop-rank">#3</span>' in pve
    assert '<span class="fam-title">Gun<img class="ammo"' in pve
    assert '<span class="fam-pool">(Pantheon)</span>' in pve
    assert '<span class="cert pve" tabindex="0" data-tip="e-pve-100">' in pve
    assert '<i class="tp" data-tip="p1001"></i>' in pve
    assert 'class="pop-chip heat-mid" tabindex="0" data-tip="c-pve-100">Medium confidence' in pve
    assert '<div class="pop-body" id="pv-pve-100" data-g="100" hidden></div>' in pve
    assert '<div class="pops" data-side="pvp" hidden>' in page


def test_the_element_filter_offers_the_scored_weapons_elements_and_each_row_names_its(
    conn, tmp_path
):
    # Gun's versions are Arc (the one it's shown as) and Kinetic, as reissues
    # changed some weapons' elements; Rifle is Strand. The filter, after Ammo,
    # offers just those three, All first, in the game's order (Kinetic before
    # Arc) with the manifest's icons. Gun's row names both its elements in that
    # order, under its name, for the filter to match either.
    with conn:
        conn.execute("UPDATE DestinyDamageTypeDefinition SET icon = '/' || lower(name) || '.png'")
    c.add_weapon_def(conn, 100, name='Gun', damage_type=2)
    c.add_weapon_def(conn, 101, name='Gun')
    c.add_weapon_def(conn, 200, name='Rifle', damage_type=7)
    c.add_popularity(conn, 'Gun', [100, 101])
    c.add_popularity(conn, 'Rifle', [200], rank=2)
    c.add_weapon_def(conn, 300, name='Unscored')
    c.add_copy(conn, 'a', 300)  # a report needs a vault
    page = popular_page(conn, tmp_path)

    def icon(name):
        return f'https://www.bungie.net/{name.lower()}.png'

    def button(name):
        return (
            f'<button type="button" data-value="{name}" aria-pressed="false">'
            f'<img src="{icon(name)}" alt="">{name}</button>'
        )

    def badge(name):
        return f'<span class="element"><img src="{icon(name)}" alt="" loading="lazy">{name}</span>'

    assert (
        'aria-label="Ammo" data-filter="ammo"><button type="button" data-value="" '
        'aria-pressed="true">All</button></div>\n'
        '<div class="switch multi" role="group" aria-label="Element" data-filter="element">'
        '<button type="button" data-value="" aria-pressed="true">All</button>'
        + ''.join(button(name) for name in ('Kinetic', 'Arc', 'Strand'))
        + '</div>\n<div class="switch flip" role="group" aria-label="Vault">'
    ) in page
    gun = page.split('data-n="gun"')[1].split('</article>')[0]
    assert gun.startswith(
        ' data-type="Auto Rifle" data-slot="Kinetic Weapons" data-ammo="" '
        'data-element="Kinetic Arc">'
    )
    assert (
        f'</h5>\n<span class="elements">{badge("Kinetic")}{badge("Arc")}</span>\n'
        '<span class="sub2">'
    ) in gun
    assert f'<span class="elements">{badge("Strand")}</span>' in page


def test_a_weapon_you_have_a_card_for_goes_to_it(conn, tmp_path):
    # The vault's Gun is on a Roll Quality card, so its row goes there; no copy
    # of Rifle is, so its row has no button.
    add_scored(conn)
    page = popular_page(conn, tmp_path)
    pve = page.split('<div class="pops" data-side="pve">')[1].split('</article>')[0]
    pvp = page.split('<div class="pops" data-side="pvp"')[1].split('</article>')[0]
    assert (
        '<div class="fam-links"><a class="lgg" href="https://www.light.gg/db/items/100/" '
        'target="_blank" rel="noopener">light.gg</a>'
        '<button type="button" class="goto" data-goto="100">My Copies</button></div>'
    ) in pve
    assert 'class="goto"' not in pvp


def test_without_scores_the_page_says_so(conn, tmp_path):
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'a', 100)
    page = popular_page(conn, tmp_path)
    assert "No scores are stored yet" in page
