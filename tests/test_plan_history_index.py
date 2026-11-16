"""Acceptance tests for the plan-history catalog. No Django required."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "plan-history" / "scripts"))
import refresh_index as ri  # noqa: E402

# The CI test image has no git binary; skip the git-backed cases there.
requires_git = unittest.skipUnless(shutil.which("git"), "git is not installed")


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


def _archive(repo: Path) -> Path:
    archive = repo / ".agent" / "plan-history"
    archive.mkdir(parents=True)
    (archive / "INDEX.md").write_text("# x\n", encoding="utf-8")
    return archive


@requires_git
def test_dirty_refresh_is_stable_on_the_second_run():
    work = Path(tempfile.mkdtemp(prefix="ph-dirty-"))
    try:
        _init(work)
        archive = _archive(work)
        (archive / "note.md").write_text("# Dirty note\n\nbody\n", encoding="utf-8")
        _commit(work, "add", "2026-01-01T10:00:00-05:00")
        (archive / "note.md").write_text("# Dirty note\n\nedited\n", encoding="utf-8")
        ri.main(["--archive", str(archive)])
        first = (archive / "manifest.json").read_bytes()
        time.sleep(2)
        ri.main(["--archive", str(archive)])
        assert (archive / "manifest.json").read_bytes() == first
    finally:
        shutil.rmtree(work, ignore_errors=True)


@requires_git
def test_fresh_clone_keeps_the_recorded_updated():
    work = Path(tempfile.mkdtemp(prefix="ph-clone-src-"))
    clone = Path(tempfile.mkdtemp(prefix="ph-clone-"))
    try:
        _init(work)
        archive = _archive(work)
        (archive / "note.md").write_text("# Note\n\nuncommitted\n", encoding="utf-8")
        ri.main(["--archive", str(archive)])
        held = _rows(archive)["note.md"]["updated"]
        _commit(work, "catalog", "2026-03-03T08:00:00-05:00")
        subprocess.run(["git", "clone", f"file://{work}", str(clone)], check=True, capture_output=True)
        carchive = clone / ".agent" / "plan-history"
        before = (carchive / "manifest.json").read_bytes()
        ri.main(["--archive", str(carchive)])
        assert (carchive / "manifest.json").read_bytes() == before
        assert _rows(carchive)["note.md"]["updated"] == held
        assert held != "2026-03-03T08:00:00-05:00"
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(clone, ignore_errors=True)


@requires_git
def test_edit_changes_only_updated_and_hash():
    work = Path(tempfile.mkdtemp(prefix="ph-edit-"))
    try:
        _init(work)
        archive = _archive(work)
        note = archive / "note.md"
        note.write_text("# Same note\n\nversion one\n", encoding="utf-8")
        _commit(work, "add", "2024-04-04T12:00:00-05:00")
        ri.main(["--archive", str(archive)])
        _commit(work, "catalog", "2024-04-04T13:00:00-05:00")
        before = _rows(archive)["note.md"]
        note.write_text("# Same note\n\nversion two\n", encoding="utf-8")
        ri.main(["--archive", str(archive)])
        after = _rows(archive)["note.md"]
        changed = [key for key in before if before[key] != after[key]]
        assert changed == ["updated", "content_sha256"]
        assert after["date"] == before["date"]
        mid = (archive / "manifest.json").read_bytes()
        ri.main(["--archive", str(archive)])
        assert (archive / "manifest.json").read_bytes() == mid
    finally:
        shutil.rmtree(work, ignore_errors=True)


@requires_git
def test_legacy_catalog_only_gains_hashes():
    work = Path(tempfile.mkdtemp(prefix="ph-legacy-"))
    try:
        _init(work)
        archive = _archive(work)
        (archive / "note.md").write_text("# Legacy\n\nbody\n", encoding="utf-8")
        _commit(work, "add", "2024-04-04T12:00:00-05:00")
        catalog = json.dumps(
            [
                {
                    "file": "note.md",
                    "date": "2018-08-08",
                    "updated": "2018-08-08T01:02:03-05:00",
                    "name": "Legacy",
                    "overview": "",
                    "todos": {},
                }
            ],
            indent=2,
        )
        (archive / "manifest.json").write_text(catalog + "\n", encoding="utf-8")
        ri.main(["--archive", str(archive)])
        row = _rows(archive)["note.md"]
        assert row["date"] == "2018-08-08"
        assert row["updated"] == "2018-08-08T01:02:03-05:00"
        assert len(row["content_sha256"]) == 64
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_crlf_bytes_hash_the_same_as_lf():
    text = "# Note\n\nbody\n"
    lf = Path(tempfile.mkdtemp(prefix="ph-lf-")) / "note.md"
    crlf = Path(tempfile.mkdtemp(prefix="ph-crlf-")) / "note.md"
    try:
        lf.write_text(text, encoding="utf-8")
        crlf.write_bytes(text.encode("utf-8").replace(b"\n", b"\r\n"))
        assert ri.content_sha256(lf) == ri.content_sha256(crlf)
    finally:
        shutil.rmtree(lf.parent, ignore_errors=True)
        shutil.rmtree(crlf.parent, ignore_errors=True)


if __name__ == "__main__":
    test_dirty_refresh_is_stable_on_the_second_run()
    test_fresh_clone_keeps_the_recorded_updated()
    test_edit_changes_only_updated_and_hash()
    test_legacy_catalog_only_gains_hashes()
    test_crlf_bytes_hash_the_same_as_lf()
    print("ok")
