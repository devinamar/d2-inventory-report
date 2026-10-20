# Report phase: reads the stored inventory and analysis results
# (report/load.py) and writes them as one HTML page and a Markdown copy for an
# LLM to review, both from report/templates/.
import re

from report import load, templating


def write(conn, output_dir, player: str) -> None:
    # Write d2_report_<name>.md and .html for the Bungie Name player
    # ("Name#1234"; the file name leaves out the #code). Nothing is written
    # when the db holds no inventory: a new db, or one rebuilt for a schema
    # change.
    print("\nGenerating reports...")
    data = load.load(conn)
    if not data['totals']['weapons'] and not data['totals']['armor']:
        print("  No inventory stored: run a full report first.")
        return
    name, _, code = player.partition('#')
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    for label, template, suffix in (
        ('Markdown', 'report.md.j2', 'md'),
        ('HTML', 'page.html.j2', 'html'),
    ):
        path = output_dir / f'd2_report_{safe_name}.{suffix}'
        path.write_text(
            templating.render(template, player=name, code=code, **data), encoding='utf-8'
        )
        print(f"  {label}: {path}")
