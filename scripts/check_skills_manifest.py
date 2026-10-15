#!/usr/bin/env python3
"""Verify that the public skill payload exactly matches its export manifest."""

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = {
    "skills/evaluate/SKILL.md",
    "skills/evaluate/references/workflow.md",
    "skills/compare/SKILL.md",
    "skills/compare/references/workflow.md",
    "skills/author-task/SKILL.md",
    "skills/author-task/references/workflow.md",
    "skills/author-task/scripts/direct_draft.py",
    "skills/prepare-repository/SKILL.md",
    "skills/prepare-repository/references/workflow.md",
}


def fail(message: str) -> None:
    raise ValueError(message)


def check_manifest() -> None:
    manifest_path = ROOT / "skills-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        fail("skills-manifest.json must be an object")

    for key in ("package_version", "workflow_version", "source_repository"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            fail(f"{key} must be a non-empty string")
    if manifest["source_repository"] != "momentohq/mfunc-llm-gw":
        fail("source_repository must name the canonical service repository")
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("source_commit", ""))):
        fail("source_commit must be a full lowercase Git commit SHA")
    plugin_version = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8")).get("version")
    claude_version = json.loads(
        (ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    ).get("version")
    if manifest["package_version"] != plugin_version or plugin_version != claude_version:
        fail("package_version differs between export manifest and plugin manifests")

    entries = manifest.get("files")
    if not isinstance(entries, list):
        fail("files must be an array")

    listed: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            fail("each files entry must be an object")
        path = entry.get("path")
        if not isinstance(path, str) or path not in EXPECTED_FILES:
            fail(f"unexpected manifest path: {path!r}")
        if path in listed:
            fail(f"duplicate manifest path: {path}")
        listed.add(path)

        resource_uri = f"skill://mo-eval/{manifest['workflow_version']}/{path.removeprefix('skills/')}"
        if entry.get("resource_uri") != resource_uri:
            fail(f"{path}: resource_uri must match its versioned skill path")
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            fail(f"{path}: sha256 must be 64 lowercase hex characters")
        expected_bytes = entry.get("bytes")
        if type(expected_bytes) is not int or expected_bytes < 0:
            fail(f"{path}: bytes must be a nonnegative integer")

        file_path = ROOT / path
        if file_path.is_symlink() or not file_path.is_file():
            fail(f"{path}: missing or symlinked file")
        payload = file_path.read_bytes()
        if len(payload) != expected_bytes:
            fail(f"{path}: byte count differs from manifest")
        if hashlib.sha256(payload).hexdigest() != expected_hash:
            fail(f"{path}: SHA-256 differs from manifest")

    actual = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "skills").rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if listed != EXPECTED_FILES or actual != EXPECTED_FILES:
        fail(
            "skill file set mismatch: "
            f"manifest missing={sorted(EXPECTED_FILES - listed)}, "
            f"manifest extra={sorted(listed - EXPECTED_FILES)}, "
            f"disk missing={sorted(EXPECTED_FILES - actual)}, "
            f"disk extra={sorted(actual - EXPECTED_FILES)}"
        )

    print(f"Verified {len(EXPECTED_FILES)} skill payload files against skills-manifest.json")


if __name__ == "__main__":
    try:
        check_manifest()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Skill manifest check failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
