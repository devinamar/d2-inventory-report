# Tests for parsing The Aegis's "Set Bonuses" sheet (sources/aegis.py). The
# sample is the live export's banner, column names and two of its rows, as
# Google sends them: rows end in \r\n, line breaks inside a cell are \n.
import csv
import io

import pytest

from sources import aegis

SHEET = (
    'INFO,,,,,,,,,ANALYSIS,,\r\n'
    '\U0001f5bc️,#,Set,Season,Bonus,Pcs,Tags,Trigger,Effect,Description,#,Tier\r\n'
    ',,"CODA\nProphecy",29,So Very Thin,4,"ability\nsurvivability",'
    '"Light weapon kills\nDark or kinetic weapon kills\nalternating weapon kills within ?s",'
    '"22?% grenade energy\n22?% melee energy\n40% DR for 5s, refreshable on kill",'
    '"easily the most consistent source of high DR if able to play around swapping '
    'polarities, excellent chunk gains too",5,S\r\n'
    ',9,"Smoke Jumper\nSolo/Fireteam Ops",27,"Ride Together, Die Together",2,survivability,'
    'orb pickup,40% DR decaying for 3s,"excellent pairing with Attrition Orbs / triple arm orb '
    'gen mod setups, a little build-dependent but solid regardless",6,A\r\n'
)
# Smoke Jumper's row as csv reads it: its twelve cells.
ROW = list(csv.reader(io.StringIO(SHEET)))[3]


def changed(cell, value):
    # ROW with one cell changed.
    row = list(ROW)
    row[cell] = value
    return row


def test_ranked_rows_parse_in_sheet_order_after_the_two_header_rows():
    bonuses = aegis.parse_csv(SHEET)
    assert [(b.set_name, b.pieces, b.bonus_name, b.season, b.rank, b.grade) for b in bonuses] == [
        ('CODA', 4, 'So Very Thin', '29', 5, 'S'),
        ('Smoke Jumper', 2, 'Ride Together, Die Together', '27', 6, 'A'),
    ]


def test_the_set_cell_splits_into_set_name_and_source():
    # The source is the cell's second line; a cell without one has none.
    assert [b.source for b in aegis.parse_csv(SHEET)] == ['Prophecy', 'Solo/Fireteam Ops']
    bonus = aegis.parse_row(changed(2, 'Smoke Jumper'))
    assert (bonus.set_name, bonus.source) == ('Smoke Jumper', '')


def test_tags_split_one_per_line_and_multiline_text_is_kept():
    coda = aegis.parse_csv(SHEET)[0]
    assert coda.tags == ('ability', 'survivability')
    assert coda.trigger == (
        'Light weapon kills\nDark or kinetic weapon kills\nalternating weapon kills within ?s'
    )
    assert coda.effect == (
        '22?% grenade energy\n22?% melee energy\n40% DR for 5s, refreshable on kill'
    )
    assert coda.analysis.startswith('easily the most consistent source of high DR')


@pytest.mark.parametrize(
    'row',
    [
        ROW[:11],
        changed(2, ''),
        changed(5, 'two'),
        changed(10, '?'),
        changed(11, 'S+'),
        changed(11, ''),
    ],
    ids=[
        'short row',
        'no set name',
        'pieces not a number',
        'no rank',
        'grade not S to F',
        'no grade',
    ],
)
def test_a_row_is_skipped_unless_complete_and_graded(row):
    assert aegis.parse_row(row) is None


def test_cells_are_trimmed():
    assert aegis.parse_row([f'  {cell} ' for cell in ROW]) == aegis.parse_row(ROW)
