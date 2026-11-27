"""Unit tests for scripts/export_backlog.py (US-02)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("export_backlog", ROOT / "scripts/export_backlog.py")
export_backlog = importlib.util.module_from_spec(_spec)
sys.modules["export_backlog"] = export_backlog  # dataclasses need the module registered (DEF-001)
_spec.loader.exec_module(export_backlog)

SAMPLE = """# Backlog
## Epics
| E1 | x |

## US-01: First story
**Epic:** E1 Setup **Req IDs:** FR-01, FR-02
**Priority:** Must **Points:** 5 **Sprint:** S0 **Owner:** Alice **Status:** To do

**Story**
As a PO, I want things,
so that value.

**Acceptance criteria**
- AC1: Given a, when b, then c.
- AC2: Given d, when e, then f.

**Tasks**
| Task | Estimate (h) | Status |
| t | 1 | To do |

## US-02: Second story
**Epic:** E2 Build **Req IDs:** FR-03
**Priority:** Could **Points:** 2 **Sprint:** S1 **Owner:** Bob **Status:** Done

**Story**
As a user, I want x, so that y.

**Acceptance criteria**
- AC1: Given g, when h, then i.
"""


def test_parse_fields_splits_inline_pairs() -> None:
    fields = export_backlog.parse_fields("**Priority:** Must **Points:** 5 **Sprint:** S0")
    assert fields == {"Priority": "Must", "Points": "5", "Sprint": "S0"}


def test_parse_backlog_reads_all_story_parts() -> None:
    stories = export_backlog.parse_backlog(SAMPLE)
    assert [s.story_id for s in stories] == ["US-01", "US-02"]
    first = stories[0]
    assert first.fields["Req IDs"] == "FR-01, FR-02"
    assert first.story == "As a PO, I want things, so that value."
    assert first.criteria == ["AC1: Given a, when b, then c.", "AC2: Given d, when e, then f."]
    assert first.row()[4] == 5  # points as int


def test_write_workbook_has_header_filter_and_dropdowns(tmp_path: Path) -> None:
    out = tmp_path / "backlog.xlsx"
    export_backlog.write_workbook(export_backlog.parse_backlog(SAMPLE), out)
    ws = load_workbook(out).active
    assert [c.value for c in ws[1]][:3] == ["ID", "Epic", "User story"]
    assert ws.max_row == 3
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref.startswith("A1:")
    formulas = {dv.formula1 for dv in ws.data_validations.dataValidation}
    assert any("In progress" in f for f in formulas)
    assert any("Must" in f for f in formulas)


def test_real_backlog_every_story_has_acceptance_criteria() -> None:
    stories = export_backlog.parse_backlog(
        (ROOT / "docs/scrum/product_backlog.md").read_text(encoding="utf-8")
    )
    assert len(stories) >= 20
    assert all(s.criteria for s in stories)
    assert all(s.fields.get("Priority") in export_backlog.PRIORITIES for s in stories)


@pytest.mark.parametrize("points", ["1", "2", "3", "5", "8", "13"])
def test_points_are_fibonacci_ints(points: str) -> None:
    story = export_backlog.Story("US-99", "t", fields={"Points": points})
    assert story.row()[4] == int(points)
