# Saves the player's weapon and armor copies as the profile reports them, one
# table per component, and traces one weapon for --debug-weapon. A copy's
# DestinyItemComponent row is updated in place, because DIM tags and notes
# point at it; its other rows are replaced, and copies gone are deleted.


def save_snapshot(conn, rows) -> None:
    # Save the copies in profile.ProfileRows in one transaction.
    with conn:
        conn.executemany(
            "INSERT INTO DestinyItemComponent (itemInstanceId, itemHash, state) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(itemInstanceId) DO UPDATE SET "
            "  itemHash = excluded.itemHash, state = excluded.state",
            rows.items,
        )
        keep = [r[0] for r in rows.items]
        conn.execute(
            "DELETE FROM DestinyItemComponent "
            f"WHERE itemInstanceId NOT IN ({','.join('?' * len(keep))})",
            keep,
        )
        for table, table_rows in (
            ('DestinyItemInstanceComponent', rows.instances),
            ('DestinyItemStatsComponent', rows.stats),
            ('DestinyItemSocketsComponent', rows.sockets),
            ('DestinyItemReusablePlugsComponent', rows.reusable_plugs),
            ('DestinyItemPlugObjectivesComponent', rows.plug_objectives),
        ):
            conn.execute(f"DELETE FROM {table}")
            if table_rows:
                marks = ', '.join('?' * len(table_rows[0]))
                conn.executemany(f"INSERT INTO {table} VALUES ({marks})", table_rows)


def trace_weapon(conn, name: str) -> None:
    # Print each stored copy of the weapons whose name contains name, with its
    # tier: the plug in every socket and, for perk sockets, the perks the copy
    # can equip (v_weapon_roll).
    copies = conn.execute(
        "SELECT i.itemInstanceId, i.itemHash, d.name, d.tierType FROM DestinyItemComponent i "
        "JOIN DestinyInventoryItemDefinition d ON d.hash = i.itemHash AND d.itemType = 3 "
        "WHERE d.name LIKE ? ORDER BY i.itemInstanceId",
        (f'%{name}%',),
    ).fetchall()
    print(f"\n  DEBUG: {len(copies)} stored copies match '{name}'")
    for c in copies:
        print(
            f"\n  {c['name']} (instance {c['itemInstanceId']}, hash {c['itemHash']}, "
            f"tier {c['tierType']})"
        )
        perks_by_socket = {}
        for r in conn.execute(
            "SELECT socket_idx, perk FROM v_weapon_roll WHERE instance_id = ? "
            "ORDER BY socket_idx, position",
            (c['itemInstanceId'],),
        ):
            perks_by_socket.setdefault(r['socket_idx'], []).append(r['perk'])
        for s in conn.execute(
            "SELECT so.key AS socketIndex, p.name, p.plugCategoryIdentifier, p.kind "
            "FROM DestinyItemSocketsComponent s "
            "CROSS JOIN json_each(s.sockets) so "
            "LEFT JOIN v_plug p ON p.hash = so.value ->> 'plugHash' "
            "WHERE s.itemInstanceId = ? ORDER BY so.key",
            (c['itemInstanceId'],),
        ):
            line = (
                f"    socket {s['socketIndex']:>2}: {s['name'] or '(empty)'} "
                f"[{s['plugCategoryIdentifier'] or ''}]"
            )
            if s['socketIndex'] in perks_by_socket:
                line += f" {s['kind']}: {', '.join(perks_by_socket[s['socketIndex']])}"
            print(line)
