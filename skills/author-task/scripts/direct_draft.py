#!/usr/bin/env python3
"""Build upload artifacts and `create_draft.direct` arguments from a local base and test tree.

Requires Python 3.11+ and Git 2.31+. It uses no mo-eval installation, Docker, network or gateway key.
The output is an inspectable request and two local files; it does not submit or upload them.
The server and contained lane remain authoritative for the task's semantics and base failure.

Example:
    python3 direct_draft.py --repo ./checkout --repository owner/name --base HEAD \\
      --instruction instruction.md --criterion 'behavior=What must work.' \\
      --test-command 'sh tests/check.sh' --tests ./test-tree --out ./direct-output \\
      --image 'image@sha256:<64 lowercase hex>'

The `--image` flag is needed when the base commits no `.mo-eval/config.toml`. Output files are
`tests.tar`, `source.bundle` and `direct-draft.json`, written in that order. The request is written
last and is absent after a refusal. This versioned helper follows the server's provisional direct
carrier; use the helper from the same workflow version as the connected server.

`source.bundle` contains all Git history reachable from the chosen base, including deleted files.
Review that history for secrets before upload. This direct-draft protocol has no narrower packaging
option: its self-contained bundle is the source artifact the lane validates.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

MAX_DECLARATION_BYTES = 64 * 1024
MAX_CRITERIA = 32
MAX_CRITERION_TEXT_BYTES = 1024
MAX_TEST_COMMAND_BYTES = 4096
MAX_IMAGE_BYTES = 4096
MAX_COMMAND_BYTES = 4096
MAX_ARTIFACT_BYTES = 4096
MAX_ARTIFACTS = 16
MAX_TESTS_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_SOURCE_BUNDLE_BYTES = 2 * 1024 * 1024 * 1024
BASE_DECLARATION = ".mo-eval/config.toml"
BRANCH_REF = "refs/heads/main"
REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+\Z")
CRITERION_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class Refused(Exception):
    """A local input or artifact cannot become a direct draft request."""


def git(*arguments: str, allowed_failure: bool = False) -> str | None:
    """Run a local Git operation without ambient Git repository variables or lazy fetches.

    Returns:
        Git's UTF-8 stdout, stripped, or `None` for an allowed nonzero exit.

    Raises:
        Refused: Git failed, or its output was not UTF-8.
    """
    environment = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    environment["GIT_NO_LAZY_FETCH"] = "1"
    try:
        completed = subprocess.run(
            ["git", *arguments],
            env=environment,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
    except UnicodeDecodeError as invalid:
        raise Refused(f"Git printed non-UTF-8 text: {invalid}") from invalid
    if completed.returncode:
        if allowed_failure:
            return None
        raise Refused(f"Git could not prepare the base bundle: {completed.stderr.strip()}")
    return completed.stdout.strip()


def required_git(*arguments: str) -> str:
    """Run Git where a result is required.

    Returns:
        Git's stdout.

    Raises:
        Refused: Git failed.
    """
    result = git(*arguments)
    if result is None:
        raise Refused("Git returned no result")
    return result


def checked_repository(repository: str) -> str:
    """Require the repository shape that `create_draft` accepts.

    Returns:
        The repository unchanged.

    Raises:
        Refused: The name cannot key a catalog suite.
    """
    if not REPOSITORY_PATTERN.fullmatch(repository) or repository.split("/", 1)[0].strip(".") == "":
        raise Refused("--repository must be owner/name, with letters, digits, dots, underscores or hyphens")
    return repository


def checked_base(checkout: Path, base_name: str) -> tuple[str, Path]:
    """Resolve a SHA-1 commit and find its checkout's shared object directory.

    Returns:
        The complete base commit and object directory.

    Raises:
        Refused: The checkout or base is not supported by the direct carrier.
    """
    if not checkout.is_dir():
        raise Refused(f"--repo is not a directory: {checkout}")
    worktree = Path(required_git("-C", str(checkout), "rev-parse", "--show-toplevel")).resolve()
    if worktree != checkout:
        raise Refused(f"--repo must be the Git checkout root: {worktree}")
    if required_git("-C", str(checkout), "rev-parse", "--is-shallow-repository") != "false":
        raise Refused("--repo must be a complete, non-shallow Git checkout")
    promisor_config = git(
        "-C",
        str(checkout),
        "config",
        "--get-regexp",
        r"^(extensions\.partialclone|remote\..*\.(promisor|partialclonefilter))$",
        allowed_failure=True,
    )
    if promisor_config is not None:
        raise Refused("--repo must not be a partial or promisor Git checkout")
    common = required_git("-C", str(checkout), "rev-parse", "--path-format=absolute", "--git-common-dir")
    objects = Path(common) / "objects"
    if not objects.is_dir():
        raise Refused(f"Git objects are unavailable: {objects}")
    if any((objects / "pack").glob("*.promisor")):
        raise Refused("--repo must not contain promisor Git packs")
    object_format = required_git("-C", str(checkout), "rev-parse", "--show-object-format")
    if object_format != "sha1":
        raise Refused("the direct request requires a SHA-1 Git repository with 40-character commit IDs")
    base = required_git(
        "-C", str(checkout), "rev-parse", "--verify", "--end-of-options", f"{base_name}^{{commit}}"
    )
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise Refused(f"--base did not resolve to one SHA-1 commit: {base}")
    return base, objects


def pinned_image(image: str) -> bool:
    """Whether an image is the direct carrier's digest-pinned printable name."""
    name, separator, digest = image.partition("@sha256:")
    return (
        bool(separator)
        and bool(name)
        and len(image.encode("utf-8")) <= MAX_IMAGE_BYTES
        and name[0] != "-"
        and all(33 <= ord(character) <= 126 and character != "@" for character in name)
        and SHA256_PATTERN.fullmatch(digest) is not None
    )


def one_line_command(command: str) -> bool:
    """Whether a setup or preparation command meets the direct carrier's text rule."""
    return (
        0 < len(command.encode("utf-8")) <= MAX_COMMAND_BYTES
        and 33 <= ord(command[0]) <= 126
        and 33 <= ord(command[-1]) <= 126
        and all(32 <= ord(character) <= 126 for character in command)
    )


def checked_environment(
    checkout: Path,
    base: str,
    repository: str,
    test_command: str,
    image: str | None,
    platform: str | None,
    setup_command: str | None,
) -> dict[str, str] | None:
    """Check explicit runtime inputs against the presence of a base declaration.

    A committed declaration is the lane's authority. This helper avoids reconciling two declarations:
    when one exists, omit `--image`; the lane still checks its full semantics.

    Returns:
        A supplied environment, or `None` for a committed declaration.

    Raises:
        Refused: No runtime was given, or a supplied field fails the carrier's rule.
    """
    if image is None and (platform is not None or setup_command is not None):
        raise Refused("--platform and --setup-command need --image")
    if image is not None:
        if not pinned_image(image):
            raise Refused("--image must be a printable name@sha256:<64 lowercase hex> pinned by digest")
        if platform is not None and platform != "linux/amd64":
            raise Refused("--platform must be linux/amd64, which hosted workers run")
        if setup_command is not None and not one_line_command(setup_command):
            raise Refused("--setup-command must be one line of printable ASCII without surrounding space")

    committed = git("-C", str(checkout), "cat-file", "-e", f"{base}:{BASE_DECLARATION}", allowed_failure=True)
    if committed is None:
        if image is None:
            raise Refused(f"the base has no {BASE_DECLARATION}; supply --image for its runtime")
        supplied = {"image": image, "platform": "linux/amd64"}
        if setup_command is not None:
            supplied["setup_command"] = setup_command
        return supplied

    if image is not None:
        raise Refused(f"the base commits {BASE_DECLARATION}; omit --image and use its declared runtime")
    entry = required_git("-C", str(checkout), "ls-tree", base, "--", BASE_DECLARATION)
    fields = entry.split(maxsplit=1)
    if not fields or fields[0] not in ("100644", "100755"):
        raise Refused(f"the base's {BASE_DECLARATION} must be a regular file")
    kind = required_git("-C", str(checkout), "cat-file", "-t", f"{base}:{BASE_DECLARATION}")
    if kind != "blob":
        raise Refused(f"the base's {BASE_DECLARATION} must be a regular file")
    size = int(required_git("-C", str(checkout), "cat-file", "-s", f"{base}:{BASE_DECLARATION}"))
    if size > MAX_DECLARATION_BYTES:
        raise Refused(f"the base's {BASE_DECLARATION} exceeds {MAX_DECLARATION_BYTES} bytes")
    content = required_git("-C", str(checkout), "show", f"{base}:{BASE_DECLARATION}")
    try:
        declaration = tomllib.loads(content)
    except tomllib.TOMLDecodeError as invalid:
        raise Refused(f"the base's {BASE_DECLARATION} is invalid TOML: {invalid}") from invalid
    if declaration.get("repo") != repository:
        raise Refused(f"the base's {BASE_DECLARATION} must name --repository exactly")
    if declaration.get("test_command") != test_command:
        raise Refused(f"the base's {BASE_DECLARATION} must declare --test-command byte for byte")
    committed_image = declaration.get("worker_image")
    if not isinstance(committed_image, str) or not pinned_image(committed_image):
        raise Refused(f"the base's {BASE_DECLARATION} must name a digest-pinned worker_image")
    if declaration.get("worker_platform", "linux/amd64") != "linux/amd64":
        raise Refused(f"the base's {BASE_DECLARATION} must run on linux/amd64")
    return None


def checked_artifact_root(root: str) -> bool:
    """Whether a preparation root is a canonical workspace-relative path."""
    components = root.split("/")
    return (
        0 < len(root.encode("utf-8")) <= MAX_ARTIFACT_BYTES
        and all(
            component not in ("", ".", "..", ".git", ".mo-eval", ".mo-eval-suite") for component in components
        )
        and all(33 <= ord(character) <= 126 for character in root)
    )


def checked_preparation(command: str | None, artifacts: list[str]) -> dict[str, Any] | None:
    """Check a supplied preparation's explicit command and retained roots.

    Returns:
        Its request object, or `None` when none was supplied.

    Raises:
        Refused: The command and roots are incomplete or conflict.
    """
    if command is None and not artifacts:
        return None
    if command is None or not artifacts:
        raise Refused("--prepare-command and --prepare-artifact must be given together")
    if not one_line_command(command):
        raise Refused("--prepare-command must be one line of printable ASCII without surrounding space")
    if len(artifacts) > MAX_ARTIFACTS:
        raise Refused(f"at most {MAX_ARTIFACTS} --prepare-artifact roots are accepted")
    if not all(checked_artifact_root(root) for root in artifacts):
        raise Refused("each --prepare-artifact must be a canonical workspace-relative printable path")
    for index, root in enumerate(artifacts):
        if any(
            root == other or root.startswith(f"{other}/") or other.startswith(f"{root}/")
            for other in artifacts[:index]
        ):
            raise Refused(f"--prepare-artifact {root!r} overlaps an earlier root")
    return {"command": command, "artifacts": artifacts}


def checked_instruction(path: Path) -> str:
    """Read an exact UTF-8 instruction within the direct carrier's bound.

    Returns:
        Its text without normalization.

    Raises:
        Refused: It is blank, too large or holds a carriage return.
    """
    content = path.read_bytes()
    if len(content) > MAX_DECLARATION_BYTES:
        raise Refused(f"--instruction exceeds {MAX_DECLARATION_BYTES} bytes")
    try:
        instruction = content.decode("utf-8")
    except UnicodeDecodeError as invalid:
        raise Refused(f"--instruction must be UTF-8: {invalid}") from invalid
    if not instruction.strip() or "\r" in instruction:
        raise Refused("--instruction must be nonblank and contain no carriage return")
    return instruction


def checked_criteria(values: list[str]) -> list[dict[str, str]]:
    """Parse and check ordered `ID=TEXT` criteria.

    Returns:
        The carrier's criterion objects.

    Raises:
        Refused: A criterion is invalid or an id is repeated.
    """
    if not 1 <= len(values) <= MAX_CRITERIA:
        raise Refused(f"give 1 to {MAX_CRITERIA} --criterion ID=TEXT values")
    seen: set[str] = set()
    criteria: list[dict[str, str]] = []
    for value in values:
        identifier, separator, text = value.partition("=")
        if not separator or not CRITERION_ID_PATTERN.fullmatch(identifier):
            raise Refused("each --criterion must begin with a unique id [a-z0-9][a-z0-9-]{0,63}=")
        if identifier in seen:
            raise Refused(f"--criterion id {identifier!r} is repeated")
        if not text or text != text.strip() or len(text.encode("utf-8")) > MAX_CRITERION_TEXT_BYTES:
            raise Refused(
                f"--criterion {identifier!r} needs nonblank text, at most 1024 UTF-8 bytes, "
                "with no surrounding whitespace"
            )
        criteria.append({"id": identifier, "text": text})
        seen.add(identifier)
    return criteria


def checked_test_command(command: str) -> str:
    """Require a test command the direct carrier can retain exactly.

    Returns:
        The command unchanged.

    Raises:
        Refused: It would be changed or refused by the server.
    """
    if (
        not command
        or command != command.strip()
        or "\0" in command
        or len(command.encode("utf-8")) > MAX_TEST_COMMAND_BYTES
    ):
        raise Refused(
            f"--test-command must be nonblank, at most {MAX_TEST_COMMAND_BYTES} UTF-8 bytes, "
            "with no surrounding whitespace or NUL"
        )
    return command


def tests_entries(tests: Path) -> list[tuple[Path, os.stat_result]]:
    """List regular files and directories without following links.

    Returns:
        Entries sorted by their workspace-relative path.

    Raises:
        Refused: The tree holds a link, special file, metadata or no test file.
    """
    if not stat.S_ISDIR(tests.lstat().st_mode):
        raise Refused(f"--tests must be a real directory, not a symbolic link: {tests}")
    entries: list[tuple[Path, os.stat_result]] = []
    file_count = 0
    payload_bytes = 0
    for entry in sorted(tests.rglob("*"), key=lambda child: child.relative_to(tests).as_posix()):
        if entry.name == ".DS_Store" or entry.name.startswith("._"):
            raise Refused(f"{entry.relative_to(tests)} is macOS metadata, not a test")
        status = entry.lstat()
        if stat.S_ISREG(status.st_mode):
            file_count += 1
            payload_bytes += status.st_size
            if payload_bytes > MAX_TESTS_ARCHIVE_BYTES:
                raise Refused(f"test files exceed the {MAX_TESTS_ARCHIVE_BYTES}-byte upload limit")
        elif not stat.S_ISDIR(status.st_mode):
            raise Refused(
                f"{entry.relative_to(tests)} is a symbolic link or special file; tests must be regular files"
            )
        entries.append((entry, status))
    if file_count == 0:
        raise Refused("--tests must contain at least one regular file")
    return entries


class BoundedArchiveWriter(io.BufferedWriter):
    """Stop an archive write before it can cross the upload byte limit."""

    def __init__(self, raw: io.FileIO, limit: int) -> None:
        super().__init__(raw)
        self.limit = limit

    def write(self, data: Any) -> int:
        """Write bytes only while the complete tar still fits the upload limit."""
        if self.tell() + len(data) > self.limit:
            raise Refused(f"tests.tar exceeds the {self.limit}-byte upload limit")
        return super().write(data)


def write_tests_archive(tests: Path, destination: Path) -> None:
    """Write a deterministic plain tar preserving only paths, bytes and executable bits.

    Raises:
        Refused: The test tree is unsafe or the archive exceeds its bound.
    """
    entries = tests_entries(tests)
    with (
        BoundedArchiveWriter(io.FileIO(destination, "xb"), MAX_TESTS_ARCHIVE_BYTES) as raw,
        tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT, encoding="utf-8") as archive,
    ):
        for entry, status in entries:
            member = tarfile.TarInfo(entry.relative_to(tests).as_posix())
            if stat.S_ISDIR(status.st_mode):
                member.type = tarfile.DIRTYPE
                member.mode = 0o755
                archive.addfile(member)
                continue
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(entry, flags)
            with os.fdopen(descriptor, "rb") as content:
                opened = os.fstat(content.fileno())
                if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
                    status.st_dev,
                    status.st_ino,
                ):
                    raise Refused(f"{entry.relative_to(tests)} changed into a non-file while archiving")
                member.mode = 0o755 if opened.st_mode & 0o111 else 0o644
                member.size = opened.st_size
                archive.addfile(member, content)


def write_source_bundle(objects: Path, base: str, destination: Path, temporary: Path) -> None:
    """Bundle the base's complete history under one ref without changing the checkout.

    An empty repository verifies it, so a bundle depending on checkout-only prerequisites is refused.

    Raises:
        Refused: Git cannot create a one-head self-contained bundle within the upload limit.
    """
    source = temporary / "source.git"
    verifier = temporary / "empty.git"
    required_git("init", "--quiet", "--bare", "--object-format=sha1", str(source))
    alternates = source / "objects/info/alternates"
    alternates.write_text(f"{objects}\n", encoding="utf-8")
    required_git("--git-dir", str(source), "update-ref", BRANCH_REF, base)
    required_git("--git-dir", str(source), "bundle", "create", str(destination), BRANCH_REF)
    if destination.stat().st_size > MAX_SOURCE_BUNDLE_BYTES:
        raise Refused(f"source.bundle exceeds the {MAX_SOURCE_BUNDLE_BYTES}-byte upload limit")
    required_git("init", "--quiet", "--bare", str(verifier))
    required_git("--git-dir", str(verifier), "bundle", "verify", str(destination))
    heads = required_git("--git-dir", str(verifier), "bundle", "list-heads", str(destination)).splitlines()
    if heads != [f"{base} {BRANCH_REF}"]:
        raise Refused(f"source.bundle has heads {heads!r}, expected only {base} {BRANCH_REF}")


def descriptor(path: Path) -> dict[str, int | str]:
    """Describe exactly the bytes the operator will upload."""
    with path.open("rb") as content:
        digest = hashlib.file_digest(content, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": digest}


def prepare(arguments: argparse.Namespace) -> str:
    """Build artifacts and write the request after every local check passes.

    Returns:
        A short summary of what was written.

    Raises:
        Refused: An input or artifact cannot be submitted as a direct draft.
    """
    checkout = Path(arguments.repo).resolve(strict=True)
    tests = Path(arguments.tests).absolute()
    instruction_path = Path(arguments.instruction)
    output = Path(arguments.out).absolute()
    if output.resolve().is_relative_to(checkout) or output.resolve().is_relative_to(tests.resolve()):
        raise Refused("--out must be outside the checkout and tests tree, leaving both unchanged")
    repository = checked_repository(arguments.repository)
    command = checked_test_command(arguments.test_command)
    criteria = checked_criteria(arguments.criterion)
    instruction = checked_instruction(instruction_path)
    base, objects = checked_base(checkout, arguments.base)
    environment = checked_environment(
        checkout, base, repository, command, arguments.image, arguments.platform, arguments.setup_command
    )
    preparation = checked_preparation(arguments.prepare_command, arguments.prepare_artifact)
    tests_entries(tests)
    if output.exists() or output.is_symlink():
        raise Refused(f"--out already exists: {output}; choose a new directory")
    output.mkdir(parents=True)
    write_tests_archive(tests, output / "tests.tar")
    with tempfile.TemporaryDirectory(prefix=".direct-draft-", dir=output) as workspace:
        write_source_bundle(objects, base, output / "source.bundle", Path(workspace))
    direct: dict[str, Any] = {
        "base": base,
        "instruction": instruction,
        "criteria": criteria,
        "test_command": command,
        "source_bundle": descriptor(output / "source.bundle"),
        "tests_archive": descriptor(output / "tests.tar"),
    }
    if environment is not None:
        direct["environment"] = environment
    if preparation is not None:
        direct["preparation"] = preparation
    request = {"repository": repository, "direct": direct}
    request_pending = output / ".direct-draft.json.tmp"
    request_pending.write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    request_pending.replace(output / "direct-draft.json")
    return "\n".join(
        (
            f"base {base}",
            f"source.bundle {output / 'source.bundle'}",
            f"tests.tar {output / 'tests.tar'}",
            f"request {output / 'direct-draft.json'}",
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Parse public inputs, prepare the artifacts, and return 0 or refusal status 2."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", action="version", version="mo-eval direct-draft helper v1")
    parser.add_argument("--repo", required=True, help="the checkout holding the immutable base")
    parser.add_argument("--repository", required=True, help="catalog repository owner/name")
    parser.add_argument("--base", required=True, help="the base commit or a local ref resolving to it")
    parser.add_argument("--instruction", required=True, help="UTF-8 file holding the exact instruction")
    parser.add_argument(
        "--criterion", action="append", default=[], metavar="ID=TEXT", help="repeat for each behavior"
    )
    parser.add_argument("--test-command", required=True, help="command running the archived tests")
    parser.add_argument("--tests", required=True, help="tree of tests at their workspace-relative paths")
    parser.add_argument("--out", required=True, help="new directory outside the checkout and tests")
    parser.add_argument("--image", help="digest-pinned worker image if the base commits no config")
    parser.add_argument("--platform", help="supplied runtime platform; only linux/amd64")
    parser.add_argument("--setup-command", help="optional supplied runtime setup command")
    parser.add_argument("--prepare-command", help="explicit contained dependency preparation command")
    parser.add_argument(
        "--prepare-artifact",
        action="append",
        default=[],
        metavar="ROOT",
        help="repeat for each retained preparation root",
    )
    arguments = parser.parse_args(argv)
    try:
        summary = prepare(arguments)
    except (Refused, OSError, UnicodeError) as refused:
        print(f"Refused: {refused}", file=sys.stderr)
        return 2
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
