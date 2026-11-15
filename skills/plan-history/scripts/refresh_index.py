#!/usr/bin/env python3
"""Refresh .agent/plan-history/INDEX.md and manifest.json from archived *.plan.md files."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = REPO_ROOT / ".agent" / "plan-history"


def parse_plan(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    name_m = re.search(r"^name:\s*(.+)$", text, re.M)
    overview_m = re.search(r"^overview:\s*(.+)$", text, re.M)
    statuses = re.findall(r"^\s+status:\s*(\w+)\s*$", text, re.M)
    todo_counts: dict[str, int] = {}
    for status in statuses:
        todo_counts[status] = todo_counts.get(status, 0) + 1
    return {
        "file": path.name,
        "date": mtime.strftime("%Y-%m-%d"),
        "mtime_iso": mtime.isoformat(timespec="seconds"),
        "name": (name_m.group(1).strip().strip('"') if name_m else path.stem),
        "overview": (overview_m.group(1).strip().strip('"') if overview_m else ""),
        "todos": todo_counts,
    }


def format_todos(todos: dict[str, int]) -> str:
    if not todos:
        return "—"
    return ", ".join(f"{k}: {v}" for k, v in sorted(todos.items()))


def escape_cell(value: str, limit: int = 120) -> str:
    text = value.replace("|", "\\|").replace("\n", " ")
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def main() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    plans = sorted(
        (parse_plan(p) for p in ARCHIVE.glob("*.plan.md")),
        key=lambda row: row["mtime_iso"],
        reverse=True,
    )

    (ARCHIVE / "manifest.json").write_text(json.dumps(plans, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# MediaCMS plan history",
        "",
        "Archive of Cursor plans for this MediaCMS fork.",
        "Live plans remain in `~/.cursor/plans/`; this folder is the project snapshot.",
        "",
        f"**Refreshed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Count:** {len(plans)} plans",
        "",
        "See `manifest.json` for machine-readable metadata. " "Archival workflow: `skills/plan-history/SKILL.md`.",
        "",
        "| Date | Plan | Overview | Todos |",
        "| ---- | ---- | -------- | ----- |",
    ]
    for row in plans:
        lines.append(
            "| {date} | [{name}]({file}) | {overview} | {todos} |".format(
                date=row["date"],
                name=escape_cell(row["name"], limit=80),
                file=row["file"],
                overview=escape_cell(row["overview"]),
                todos=format_todos(row["todos"]),
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Prefer `python3 skills/plan-history/scripts/refresh_index.py` after copying plans.",
            "- Do not commit unless asked.",
            "",
        ]
    )
    (ARCHIVE / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Refreshed {len(plans)} plans in {ARCHIVE}")


if __name__ == "__main__":
    main()
