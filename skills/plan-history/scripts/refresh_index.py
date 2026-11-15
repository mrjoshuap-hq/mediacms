#!/usr/bin/env python3
"""Refresh .agent/plan-history/INDEX.md and manifest.json from archived plan notes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARCHIVE = REPO_ROOT / ".agent" / "plan-history"

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.S)
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.M)
OVERVIEW_RE = re.compile(r"^overview:\s*(.+?)\s*$", re.M)
DATE_RE = re.compile(r"^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", re.M)
CREATED_RE = re.compile(r"^created:\s*[\"']?(\d{4}-\d{2}-\d{2})", re.M)
BODY_DATE_RE = re.compile(r"^- Date:\s*(\d{4}-\d{2}-\d{2})\s*$", re.M)
HEADING_RE = re.compile(r"^# (?!#)(.+?)\s*$", re.M)
STATUS_RE = re.compile(r"^\s+status:\s*(\w+)\s*$", re.M)
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SHALLOW_WARNING = "warning: shallow git clone; plan dates may be incomplete. Run git fetch --unshallow for full history."


def unquote(value: str) -> str:
    return value.strip().strip('"').strip("'")


def frontmatter(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    return match.group(1) if match else ""


def first_group(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    return unquote(match.group(1))


def load_manifest(archive: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Return (date by filename, updated by filename) from the current catalog."""
    path = archive / "manifest.json"
    dates: dict[str, str] = {}
    updated: dict[str, str] = {}
    if not path.is_file():
        return dates, updated
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dates, updated
    if not isinstance(data, list):
        return dates, updated
    for row in data:
        if not isinstance(row, dict) or not isinstance(row.get("file"), str):
            continue
        filename = row["file"]
        date = row.get("date")
        if isinstance(date, str) and DAY_RE.fullmatch(date):
            dates[filename] = date
        stamp = row.get("updated")
        if isinstance(stamp, str) and stamp.strip():
            updated[filename] = stamp.strip()
    return dates, updated


def git_stdout(archive: Path, *args: str) -> str | None:
    command = ["git", "--no-pager", "-C", str(archive), "-c", "core.quotepath=false", *args]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def repo_root(archive: Path) -> Path | None:
    output = git_stdout(archive, "rev-parse", "--show-toplevel")
    if not output:
        return None
    return Path(output.strip())


def is_shallow(archive: Path) -> bool:
    output = git_stdout(archive, "rev-parse", "--is-shallow-repository")
    return bool(output) and output.strip() == "true"


def entry_name(path_str: str, archive: Path, root: Path) -> str | None:
    text = path_str.strip().strip('"')
    if not text or text == ".":
        return None
    raw = Path(text)
    archive_root = archive.resolve()
    for base in (root, archive):
        candidate = raw if raw.is_absolute() else base / raw
        try:
            relative = candidate.resolve().relative_to(archive_root)
        except ValueError:
            continue
        if len(relative.parts) == 1 and relative.suffix == ".md":
            return relative.name
    return None


def parse_name_status(line: str) -> tuple[str, list[str]]:
    parts = line.split("\t")
    return parts[0][:1], parts[1:]


def collect_history(archive: Path, root: Path) -> tuple[dict[str, str], dict[str, str]]:
    """One log pass: newest author date, and the oldest add (rename-aware)."""
    output = git_stdout(archive, "log", "-M", "--name-status", "--format=%aI", "--", ".")
    if output is None:
        return {}, {}
    latest: dict[str, str] = {}
    added: dict[str, str] = {}
    renamed_from: dict[str, str] = {}
    current: str | None = None
    for line in output.splitlines():
        if not line.strip():
            continue
        if ISO_RE.fullmatch(line.strip()):
            current = line.strip()
            continue
        if current is None:
            continue
        code, paths = parse_name_status(line)
        names = []
        for path in paths:
            name = entry_name(path, archive, root)
            if name:
                names.append(name)
        if code == "R" and len(names) == 2:
            renamed_from.setdefault(names[1], names[0])
        if code == "A":
            for name in names:
                added[name] = current
        for name in names:
            latest.setdefault(name, current)
    first_add: dict[str, str] = {}
    for name in set(latest) | set(added):
        stamp = follow_add(name, added, renamed_from)
        if stamp:
            first_add[name] = stamp
    return latest, first_add


def follow_add(name: str, added: dict[str, str], renamed_from: dict[str, str]) -> str | None:
    seen: set[str] = set()
    current: str | None = name
    while current and current not in seen:
        if current in added:
            return added[current]
        seen.add(current)
        current = renamed_from.get(current)
    return None


def dirty_names(archive: Path, root: Path) -> set[str]:
    output = git_stdout(archive, "status", "--porcelain", "--untracked-files=all", "--", ".")
    if output is None:
        return set()
    names: set[str] = set()
    for line in output.splitlines():
        if len(line) < 4:
            continue
        payload = line[3:]
        parts = payload.split(" -> ") if " -> " in payload else [payload]
        for part in parts:
            name = entry_name(part, archive, root)
            if name:
                names.add(name)
    return names


def plan_date(text: str, filename: str, manifest_dates: dict[str, str], first_add: dict[str, str], today: str) -> str:
    header = frontmatter(text)
    for pattern in (DATE_RE, CREATED_RE):
        value = first_group(pattern, header)
        if value:
            return value
    body_date = BODY_DATE_RE.search(text)
    if body_date:
        return body_date.group(1)
    recorded = manifest_dates.get(filename)
    if recorded:
        return recorded
    added = first_add.get(filename)
    if added:
        return added[:10]
    return today


def plan_name(text: str, path: Path) -> str:
    name = first_group(NAME_RE, frontmatter(text))
    if name:
        return name
    heading = HEADING_RE.search(text)
    if heading:
        return heading.group(1).strip()
    return path.stem


def plan_overview(text: str) -> str:
    return first_group(OVERVIEW_RE, frontmatter(text)) or ""


def plan_todos(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for status in STATUS_RE.findall(text):
        counts[status] = counts.get(status, 0) + 1
    return counts


def resolve_updated(
    *,
    filename: str,
    dirty: set[str],
    shallow: bool,
    latest: dict[str, str],
    manifest_updated: dict[str, str],
    date: str,
    now_iso: str,
) -> str:
    if filename in dirty:
        return now_iso
    # A depth-1 history stamps every file with the tip commit. Keep the
    # recorded snapshot so that checkout does not rewrite the catalog.
    recorded = manifest_updated.get(filename)
    if shallow and recorded:
        return recorded
    if filename in latest:
        return latest[filename]
    if recorded:
        return recorded
    return date


def stamp_key(value: str) -> datetime:
    text = value.strip()
    if DAY_RE.fullmatch(text):
        return datetime.fromisoformat(text + "T00:00:00+00:00")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_todos(todos: dict[str, int]) -> str:
    if not todos:
        return "—"
    return ", ".join(f"{k}: {v}" for k, v in sorted(todos.items()))


def escape_cell(value: str, limit: int = 120) -> str:
    text = value.replace("|", "\\|").replace("\n", " ")
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def render_index(plans: list[dict]) -> str:
    latest = plans[0]["updated"] if plans else "—"
    lines = [
        "# MediaCMS plan history",
        "",
        "Archive of plans for this MediaCMS fork: Cursor plans and Architect design notes.",
        "Live plans remain in `~/.cursor/plans/`; this folder is the project snapshot.",
        "",
        f"**Latest snapshot:** {latest}",
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
    return "\n".join(lines)


def refresh(archive: Path) -> None:
    archive.mkdir(parents=True, exist_ok=True)
    manifest_dates, manifest_updated = load_manifest(archive)
    root = repo_root(archive)
    shallow = False
    latest: dict[str, str] = {}
    first_add: dict[str, str] = {}
    dirty: set[str] = set()
    if root is not None:
        shallow = is_shallow(archive)
        if shallow:
            print(SHALLOW_WARNING, file=sys.stderr)
        latest, first_add = collect_history(archive, root)
        dirty = dirty_names(archive, root)

    now = datetime.now().astimezone()
    today = now.strftime("%Y-%m-%d")
    now_iso = now.isoformat(timespec="seconds")
    plans = []
    for path in sorted(p for p in archive.glob("*.md") if p.name != "INDEX.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        date = plan_date(text, path.name, manifest_dates, first_add, today)
        plans.append(
            {
                "file": path.name,
                "date": date,
                "updated": resolve_updated(
                    filename=path.name,
                    dirty=dirty,
                    shallow=shallow,
                    latest=latest,
                    manifest_updated=manifest_updated,
                    date=date,
                    now_iso=now_iso,
                ),
                "name": plan_name(text, path),
                "overview": plan_overview(text),
                "todos": plan_todos(text),
            }
        )
    plans.sort(key=lambda row: row["file"])
    plans.sort(key=lambda row: stamp_key(row["updated"]), reverse=True)

    (archive / "manifest.json").write_text(json.dumps(plans, indent=2) + "\n", encoding="utf-8")
    (archive / "INDEX.md").write_text(render_index(plans), encoding="utf-8")
    print(f"Refreshed {len(plans)} plans in {archive}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Refresh plan-history INDEX.md and manifest.json.")
    parser.add_argument(
        "--archive",
        type=Path,
        default=DEFAULT_ARCHIVE,
        help="Plan archive directory (default: .agent/plan-history).",
    )
    args = parser.parse_args(argv)
    refresh(args.archive)


if __name__ == "__main__":
    main()
