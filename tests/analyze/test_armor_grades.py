# Tests for the armor set grades, read from the armor_grade view's file.
from analyze import armor_grades


def test_grades_are_the_views_rows_best_first_without_unclassified(conn):
    rows = conn.execute(
        "SELECT grade, label, slot_cap FROM armor_grade WHERE grade != '' ORDER BY position"
    ).fetchall()
    assert tuple(armor_grades.Grade(*r) for r in rows) == armor_grades.GRADES
    assert armor_grades.GRADE_ORDER == ('S', 'A', 'B', 'C', 'D', 'E', 'F')


def test_cap_summary_groups_grades_that_share_a_cap():
    assert armor_grades.cap_summary() == 'S 4, A/B 2, C/D/E/F 1'
