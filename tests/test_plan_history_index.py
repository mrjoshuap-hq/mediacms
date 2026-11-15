"""Regression tests for plan-history catalog dates. No Django required."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "plan-history" / "scripts"))
import refresh_index as ri  # noqa: E402


def _git(repo: Path, *args: str, env: dict | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=merged, capture_output=True)


def _init(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")


def _commit(repo: Path, message: str, author_date: str) -> None:
    _git(repo, "add", "-A")
    _git(
        repo,
        "commit",
        "-m",
        message,
        env={"GIT_AUTHOR_DATE": author_date, "GIT_COMMITTER_DATE": author_date},
    )


def _rows(archive: Path) -> dict:
    return {row["file"]: row for row in json.loads((archive / "manifest.json").read_text(encoding="utf-8"))}


def test_shallow_clone_does_not_store_boundary_updated():
    """A clean note whose hash differs must not keep the shallow boundary time."""
    work = Path(tempfile.mkdtemp(prefix="ph-shallow-"))
    try:
        _init(work)
        archive = work / ".agent" / "plan-history"
        archive.mkdir(parents=True)
        note = archive / "note.md"
        note.write_text("# January note\n\noriginal\n", encoding="utf-8")
        (archive / "INDEX.md").write_text("# x\n", encoding="utf-8")
        _commit(work, "add note", "2026-01-03T10:00:00-05:00")
        ri.main(["--archive", str(archive)])
        _commit(work, "catalog", "2026-01-03T11:00:00-05:00")
        note.write_text("# January note\n\nchanged on jan 3\n", encoding="utf-8")
        _commit(work, "change note", "2026-01-03T15:00:00-05:00")
        (work / "other.txt").write_text("unrelated\n", encoding="utf-8")
        _commit(work, "unrelated", "2026-01-04T09:00:00-05:00")

        shallow = Path(tempfile.mkdtemp(prefix="ph-shallow-clone-"))
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", f"file://{work}", str(shallow)],
                check=True,
                capture_output=True,
            )
            sarchive = shallow / ".agent" / "plan-history"
            before = (sarchive / "manifest.json").read_bytes()
            before_index = (sarchive / "INDEX.md").read_bytes()
            try:
                ri.main(["--archive", str(sarchive)])
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("shallow refresh should refuse a git updated time")
            assert (sarchive / "manifest.json").read_bytes() == before
            assert (sarchive / "INDEX.md").read_bytes() == before_index
            assert _rows(sarchive)["note.md"]["updated"] == "2026-01-03T10:00:00-05:00"
        finally:
            shutil.rmtree(shallow, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_reused_filename_uses_the_new_add_date():
    """Deleting a note and reusing its name must not keep the old add date."""
    work = Path(tempfile.mkdtemp(prefix="ph-reuse-"))
    try:
        _init(work)
        archive = work / ".agent" / "plan-history"
        archive.mkdir(parents=True)
        (archive / "INDEX.md").write_text("# x\n", encoding="utf-8")
        (archive / "note.md").write_text("# Old note\n\nold body\n", encoding="utf-8")
        _commit(work, "add old", "2024-04-04T12:00:00-05:00")
        _git(work, "rm", ".agent/plan-history/note.md")
        _commit(work, "delete old", "2025-05-05T12:00:00-05:00")
        (archive / "note.md").write_text("# New note\n\nnew body from 2026\n", encoding="utf-8")
        _commit(work, "readd", "2026-06-06T12:00:00-05:00")

        ri.main(["--archive", str(archive)])
        row = _rows(archive)["note.md"]
        assert row["date"] == "2026-06-06"
        assert row["updated"].startswith("2026-06-06T12:00:00")
        assert row["name"] == "New note"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_merge_resolution_uses_the_merge_timestamp():
    """A resolution different from both parents is the note's updated time."""
    work = Path(tempfile.mkdtemp(prefix="ph-merge-"))
    try:
        _init(work)
        archive = work / ".agent" / "plan-history"
        archive.mkdir(parents=True)
        (archive / "INDEX.md").write_text("# x\n", encoding="utf-8")
        note = archive / "note.md"
        note.write_text("# Note\n\nbase\n", encoding="utf-8")
        _commit(work, "base", "2026-02-01T10:00:00-05:00")
        ri.main(["--archive", str(archive)])
        _commit(work, "catalog", "2026-02-01T11:00:00-05:00")
        _git(work, "branch", "left")
        _git(work, "checkout", "left")
        note.write_text("# Note\n\nleft side change\n", encoding="utf-8")
        _commit(work, "left", "2026-02-02T10:00:00-05:00")
        _git(work, "checkout", "master")
        note.write_text("# Note\n\nright side change\n", encoding="utf-8")
        _commit(work, "right", "2026-02-03T10:00:00-05:00")
        merged = subprocess.run(["git", "-C", str(work), "merge", "left", "--no-commit"], capture_output=True)
        assert merged.returncode != 0
        note.write_text("# Note\n\nresolved neither parent\n", encoding="utf-8")
        _commit(work, "merge resolved", "2026-02-04T10:00:00-05:00")
        ri.main(["--archive", str(archive)])
        row = _rows(archive)["note.md"]
        assert row["date"] == "2026-02-01"
        assert row["updated"] == "2026-02-04T10:00:00-05:00"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_catalog_date_does_not_survive_a_new_lifetime():
    """An existing catalog row must not date the next note that reuses the filename."""
    work = Path(tempfile.mkdtemp(prefix="ph-catalog-reuse-"))
    try:
        _init(work)
        archive = work / ".agent" / "plan-history"
        archive.mkdir(parents=True)
        (archive / "INDEX.md").write_text("# x\n", encoding="utf-8")
        (archive / "note.md").write_text("# Old note\n\nold body\n", encoding="utf-8")
        _commit(work, "add", "2024-04-04T12:00:00-05:00")
        ri.main(["--archive", str(archive)])
        _commit(work, "catalog", "2024-04-04T13:00:00-05:00")
        assert _rows(archive)["note.md"]["date"] == "2024-04-04"
        _git(work, "rm", ".agent/plan-history/note.md")
        _commit(work, "delete", "2025-05-05T12:00:00-05:00")
        (archive / "note.md").write_text("# New note\n\nbrand new 2026\n", encoding="utf-8")
        _commit(work, "reuse", "2026-06-06T12:00:00-05:00")
        ri.main(["--archive", str(archive)])
        row = _rows(archive)["note.md"]
        assert row["date"] == "2026-06-06"
        assert row["name"] == "New note"
        assert row["updated"].startswith("2026-06-06T12:00:00")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_ordinary_edit_keeps_the_catalog_date():
    work = Path(tempfile.mkdtemp(prefix="ph-edit-"))
    try:
        _init(work)
        archive = work / ".agent" / "plan-history"
        archive.mkdir(parents=True)
        (archive / "INDEX.md").write_text("# x\n", encoding="utf-8")
        note = archive / "note.md"
        note.write_text("# Same note\n\nversion one\n", encoding="utf-8")
        _commit(work, "add", "2024-04-04T12:00:00-05:00")
        ri.main(["--archive", str(archive)])
        _commit(work, "catalog", "2024-04-04T13:00:00-05:00")
        note.write_text("# Same note\n\nversion two\n", encoding="utf-8")
        _commit(work, "edit", "2026-06-06T12:00:00-05:00")
        ri.main(["--archive", str(archive)])
        row = _rows(archive)["note.md"]
        assert row["date"] == "2024-04-04"
        assert row["updated"] == "2026-06-06T12:00:00-05:00"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_rename_then_reusing_the_old_name_keeps_both_lifetimes():
    """The renamed note keeps 2024; a new note at the old name is dated 2026."""
    work = Path(tempfile.mkdtemp(prefix="ph-rename-reuse-"))
    try:
        _init(work)
        archive = work / ".agent" / "plan-history"
        archive.mkdir(parents=True)
        (archive / "INDEX.md").write_text("# x\n", encoding="utf-8")
        (archive / "old.md").write_text("# Renamed note\n\noriginal\n", encoding="utf-8")
        _commit(work, "add", "2024-04-04T12:00:00-05:00")
        _git(work, "mv", ".agent/plan-history/old.md", ".agent/plan-history/new.md")
        _commit(work, "rename", "2025-05-05T12:00:00-05:00")
        (archive / "old.md").write_text("# Replacement note\n\nadded in 2026\n", encoding="utf-8")
        _commit(work, "reuse old name", "2026-06-06T12:00:00-05:00")
        ri.main(["--archive", str(archive)])
        rows = _rows(archive)
        assert rows["new.md"]["date"] == "2024-04-04"
        assert rows["new.md"]["name"] == "Renamed note"
        assert rows["old.md"]["date"] == "2026-06-06"
        assert rows["old.md"]["name"] == "Replacement note"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_rename_keeps_the_original_add_date():
    work = Path(tempfile.mkdtemp(prefix="ph-rename-"))
    try:
        _init(work)
        archive = work / ".agent" / "plan-history"
        archive.mkdir(parents=True)
        (archive / "INDEX.md").write_text("# x\n", encoding="utf-8")
        (archive / "old.md").write_text("# Renamed note\n\nbody\n", encoding="utf-8")
        _commit(work, "add", "2024-04-04T12:00:00-05:00")
        _git(work, "mv", ".agent/plan-history/old.md", ".agent/plan-history/new.md")
        _commit(work, "rename", "2025-05-05T12:00:00-05:00")
        ri.main(["--archive", str(archive)])
        row = _rows(archive)["new.md"]
        assert row["date"] == "2024-04-04"
        assert "old.md" not in _rows(archive)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    test_shallow_clone_does_not_store_boundary_updated()
    test_reused_filename_uses_the_new_add_date()
    test_rename_then_reusing_the_old_name_keeps_both_lifetimes()
    test_rename_keeps_the_original_add_date()
    test_merge_resolution_uses_the_merge_timestamp()
    test_catalog_date_does_not_survive_a_new_lifetime()
    test_ordinary_edit_keeps_the_catalog_date()
    print("ok")
