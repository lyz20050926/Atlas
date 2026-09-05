"""Build and verify a source-only, secret-free hackathon archive.

Run as ``python -m scripts.build_submission --output-dir <new-directory>``.
The allowlist deliberately excludes local databases, .env, credentials,
developer outputs, virtual environments and Git metadata. No files are deleted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "Atlas"
MAX_BYTES = 5_000_000_000
ROOT_FILES = {
    ".env.example", ".gitignore", "README.md", "app.py", "launch.py",
    "start.ps1", "start.sh", "pyproject.toml", "requirements.txt",
    "requirements-dev.txt", "uv.lock", ".streamlit/config.toml",
}
SCRIPT_FILES = {
    "build_submission.py", "preflight.py", "check_dependencies.py", "run_demo.py",
    "run_evaluation.py", "run_live_evaluation.py", "check_aws.py",
    "check_bedrock_connection.py", "check_google_books.py",
}
DATA_FILES = {
    "data/demo_profiles.json", "data/evaluation_cases.json",
    "data/fixtures/book_api_responses.json", "data/fixtures/chinese_books.json",
    "data/fixtures/evaluation_books.json", "data/fixtures/google_books_response.json",
}
REPORT_FILES = {
    "evaluation_results/latest.json", "evaluation_results/live_latest.json",
    "evaluation_results/preflight_latest.json",
}
SECRET_PATTERNS = {
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Google API key": re.compile(rb"\bAIza[A-Za-z0-9_-]{35}\b"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS secret assignment": re.compile(
        rb"aws_secret_access_key\s*[=:]\s*[\x22\x27]?[A-Za-z0-9/+]{40}(?:[\x22\x27]|\b)", re.I),
}


def allowed_file(relative: str) -> bool:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        return False
    if any(part in {"__pycache__", ".git", ".venv", ".pytest_cache", ".ruff_cache"} for part in path.parts):
        return False
    if relative in ROOT_FILES | DATA_FILES | REPORT_FILES:
        return True
    if len(path.parts) < 2:
        return False
    section = path.parts[0]
    if section in {"src", "tests"}:
        return path.suffix == ".py"
    if section == "docs":
        return path.suffix == ".md"
    if section in {"assets", "static"}:
        return path.suffix in {".svg", ".png", ".woff2"}
    return section == "scripts" and len(path.parts) == 2 and path.name in SCRIPT_FILES


def collect_files(root: Path) -> list[Path]:
    roots = [root / name for name in ("src", "tests", "docs", "assets", "static", "scripts")]
    files = {root / name for name in ROOT_FILES | DATA_FILES | REPORT_FILES if (root / name).is_file()}
    for directory in roots:
        if directory.is_symlink():
            raise ValueError(f"Symlink directory is not accepted: {directory.name}")
        if directory.is_dir():
            files.update(path for path in directory.rglob("*") if path.is_file() and allowed_file(path.relative_to(root).as_posix()))
    for path in files:
        if path.is_symlink() or root.resolve() not in path.resolve().parents:
            raise ValueError(f"File escapes project root: {path.name}")
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def payload_digest(payloads: Mapping[str, bytes]) -> str:
    """Fingerprint one immutable input snapshot, excluding generated reports.

    Static data, assets, documentation and example configuration are release
    inputs too. Reports are excluded to avoid a self-referential digest. This
    proves content consistency, not the identity of an archive's author.
    """
    digest = hashlib.sha256()
    for relative, content in sorted(payloads.items()):
        if relative in REPORT_FILES:
            continue
        name = relative.encode("utf-8")
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def read_payloads(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in collect_files(root)}


def source_digest(root: Path = ROOT) -> str:
    """Bind a release gate to all static inputs it checked."""
    return payload_digest(read_payloads(root))


def scan_content(relative: str, content: bytes) -> None:
    if content.startswith(b"SQLite format 3\x00"):
        raise ValueError(f"A local database must not be submitted: {relative}")
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(content):
            # Never print the matched secret.
            raise ValueError(f"Potential {label} in {relative}; archive not created")


def require_payload_release_gate(payloads: Mapping[str, bytes]) -> str:
    """Require the included preflight to cover these exact source bytes."""
    try:
        report = json.loads(payloads["evaluation_results/preflight_latest.json"])
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("A valid complete preflight report is required") from exc
    required = {"ruff", "pytest", "compileall", "secret scan", "dependencies", "deterministic evaluation"}
    passed = {item["name"] for item in report.get("checks", []) if item.get("passed") is True}
    if report.get("passed") is not True or not required <= passed:
        raise ValueError("Run the complete preflight successfully before packaging")
    digest = payload_digest(payloads)
    if report.get("source_sha256") != digest:
        raise ValueError("Source changed after preflight; rerun checks before packaging")
    return digest


def require_release_gate(root: Path) -> None:
    require_payload_release_gate(read_payloads(root))


def verify_archive(archive: Path) -> dict:
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        names = [item.filename for item in entries]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate archive entry")
        if sum(item.file_size for item in entries) > MAX_BYTES:
            raise ValueError("Archive exceeds the 5 GB uncompressed limit")
        for item in entries:
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename or path.parts[0] != PACKAGE:
                raise ValueError("Unsafe archive path")
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("Symlink archive entry")
        manifest = json.loads(package.read(f"{PACKAGE}/MANIFEST.json"))
        expected = {f"{PACKAGE}/{name}" for name in manifest["files"]} | {f"{PACKAGE}/MANIFEST.json"}
        if set(names) != expected:
            raise ValueError("Archive does not match its manifest")
        payloads = {}
        for relative, details in manifest["files"].items():
            if not allowed_file(relative):
                raise ValueError(f"Disallowed file: {relative}")
            content = package.read(f"{PACKAGE}/{relative}")
            scan_content(relative, content)
            if len(content) != details["bytes"] or hashlib.sha256(content).hexdigest() != details["sha256"]:
                raise ValueError(f"Content integrity failure: {relative}")
            payloads[relative] = content
        if manifest.get("source_sha256") != payload_digest(payloads):
            raise ValueError("Manifest source fingerprint does not match archive content")
        require_payload_release_gate(payloads)
    return {"files": len(manifest["files"]), "archive_bytes": archive.stat().st_size, "verified": True}


def build_archive(root: Path, output_dir: Path) -> Path:
    # Read once: gate, manifest and ZIP all consume the same bytes. A later edit
    # on disk cannot replace files in the already checked package snapshot.
    payloads = read_payloads(root)
    checked_digest = require_payload_release_gate(payloads)
    required_files = ROOT_FILES | DATA_FILES
    missing = required_files - payloads.keys()
    if missing:
        raise ValueError(f"Required project resources missing: {sorted(missing)}")
    for name, content in payloads.items():
        scan_content(name, content)
    if sum(map(len, payloads.values())) > MAX_BYTES:
        raise ValueError("Project exceeds the 5 GB submission limit")
    manifest = {
        "format": 1, "project": "NexMind Atlas", "generated_at": datetime.now(UTC).isoformat(),
        "source_sha256": checked_digest,
        "scope": "Code project only. Presentation deck and video are separate deliverables.",
        "files": {name: {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()} for name, content in payloads.items()},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / "Atlas-Code-Submission.zip"
    # Exclusive creation preserves every previously built archive.
    with zipfile.ZipFile(archive, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name, content in payloads.items():
            entry = zipfile.ZipInfo(f"{PACKAGE}/{name}", date_time=(2026, 9, 5, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100755 if name == "start.sh" else 0o100644) << 16
            package.writestr(entry, content)
        package.writestr(f"{PACKAGE}/MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    verify_archive(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with (output_dir / "SHA256SUMS.txt").open("x", encoding="utf-8") as stream:
        stream.write(f"{digest}  {archive.name}\n")
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT.parent / "atlas-submission-2026-09-05")
    parser.add_argument("--verify", type=Path, help="Verify an existing archive without changing it")
    args = parser.parse_args()
    archive = args.verify or build_archive(ROOT, args.output_dir.resolve())
    print(json.dumps(verify_archive(archive), indent=2))
    print(f"Archive: {archive}")


if __name__ == "__main__":
    main()
