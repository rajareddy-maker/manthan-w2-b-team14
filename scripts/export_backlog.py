"""Export docs/scrum/product_backlog.md to docs/scrum/product_backlog.xlsx.

Parses stories written in the team's user-story template (``## US-xx: title`` blocks) and
writes one row per story with a frozen header, auto-filter, wrapped text and dropdowns for
Status and Priority.

Usage:
    python scripts/export_backlog.py [--src PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

LOG = logging.getLogger("export_backlog")

COLUMNS = [
    ("ID", 9),
    ("Epic", 28),
    ("User story", 60),
    ("Acceptance criteria", 80),
    ("Points", 8),
    ("Priority", 10),
    ("Sprint", 8),
    ("Owner", 20),
    ("Status", 13),
    ("Req IDs", 24),
]
STATUSES = ["To do", "In progress", "In review", "Done", "Blocked"]
PRIORITIES = ["Must", "Should", "Could", "Won't"]

STORY_HEADER = re.compile(r"^## (US-\d+):\s*(.+)$")
FIELD = re.compile(r"\*\*(Epic|Req IDs|Priority|Points|Sprint|Owner|Status):\*\*\s*")


@dataclass
class Story:
    """One backlog story parsed from Markdown."""

    story_id: str
    title: str
    fields: dict[str, str] = field(default_factory=dict)
    story: str = ""
    criteria: list[str] = field(default_factory=list)

    def row(self) -> list[object]:
        """Return the spreadsheet row in COLUMNS order."""
        points = self.fields.get("Points", "")
        return [
            self.story_id,
            self.fields.get("Epic", ""),
            f"{self.title}\n{self.story}".strip(),
            "\n".join(self.criteria),
            int(points) if points.isdigit() else points,
            self.fields.get("Priority", ""),
            self.fields.get("Sprint", ""),
            self.fields.get("Owner", ""),
            self.fields.get("Status", ""),
            self.fields.get("Req IDs", ""),
        ]


def parse_fields(line: str) -> dict[str, str]:
    """Parse a line such as ``**Priority:** Must **Points:** 5`` into a dict."""
    parts = FIELD.split(line)
    # parts = ['', 'Priority', 'Must ', 'Points', '5', ...]
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def parse_backlog(text: str) -> list[Story]:
    """Parse all ``## US-xx`` story blocks from backlog Markdown."""
    stories: list[Story] = []
    current: Story | None = None
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        header = STORY_HEADER.match(line)
        if header:
            current = Story(story_id=header.group(1), title=header.group(2).strip())
            stories.append(current)
            section = ""
            continue
        if current is None:
            continue
        if line.startswith("## "):  # a non-story H2 ends the current story
            current = None
            continue
        if FIELD.search(line):
            current.fields.update(parse_fields(line))
        elif line in ("**Story**", "**Acceptance criteria**", "**Tasks**"):
            section = line.strip("*")
        elif section == "Story" and line:
            current.story = f"{current.story} {line}".strip()
        elif section == "Acceptance criteria" and line.startswith("- "):
            current.criteria.append(line[2:])
    return stories


def write_workbook(stories: list[Story], out: Path) -> None:
    """Write stories to an .xlsx file with filters, frozen header and dropdowns."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Product backlog"
    ws.append([name for name, _ in COLUMNS])
    for story in stories:
        ws.append(story.row())

    header_fill = PatternFill("solid", fgColor="1F4E78")
    for idx, (_, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=idx)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        ws.column_dimensions[get_column_letter(idx)].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    last_row = max(ws.max_row, 2)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{last_row}"

    for values, col in ((STATUSES, "I"), (PRIORITIES, "F")):
        dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col}2:{col}{last_row + 200}")

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", type=Path, default=root / "docs/scrum/product_backlog.md")
    parser.add_argument("--out", type=Path, default=root / "docs/scrum/product_backlog.xlsx")
    args = parser.parse_args()

    stories = parse_backlog(args.src.read_text(encoding="utf-8"))
    if not stories:
        raise SystemExit(f"No stories found in {args.src}")
    missing_ac = [s.story_id for s in stories if not s.criteria]
    if missing_ac:
        raise SystemExit(f"Stories without acceptance criteria: {missing_ac}")
    write_workbook(stories, args.out)
    points = sum(s.row()[4] for s in stories if isinstance(s.row()[4], int))
    LOG.info("exported stories=%d points=%d out=%s", len(stories), points, args.out)


if __name__ == "__main__":
    main()
