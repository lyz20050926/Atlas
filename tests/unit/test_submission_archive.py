import hashlib
import json
import zipfile

import pytest

from scripts import build_submission
from scripts.build_submission import (
    DATA_FILES,
    ROOT_FILES,
    allowed_file,
    build_archive,
    collect_files,
    payload_digest,
    read_payloads,
    require_release_gate,
    scan_content,
    source_digest,
    verify_archive,
)


def passing_report(digest):
    return {
        "passed": True, "source_sha256": digest,
        "checks": [{"name": name, "passed": True} for name in (
            "ruff", "pytest", "compileall", "secret scan", "dependencies", "deterministic evaluation",
        )],
    }


@pytest.mark.parametrize("name", [
    ".env", ".streamlit/secrets.toml", "data/demo.db", "data/demo.db-wal",
    "outputs/private.json", "scripts/qa_production_state.py", ".venv/src/code.py",
    "src/__pycache__/module.py", "../README.md", "/README.md", "src\\private.py",
])
def test_submission_allowlist_excludes_local_or_unsafe_files(name):
    assert not allowed_file(name)


def test_submission_collects_only_allowed_files(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/module.py").write_text("pass\n")
    (tmp_path / "src/private.json").write_text("{}")
    (tmp_path / "README.md").write_text("Read me")
    (tmp_path / ".env").write_text("not for submission")
    assert {file.relative_to(tmp_path).as_posix() for file in collect_files(tmp_path)} == {
        "src/module.py", "README.md",
    }


@pytest.mark.parametrize("payload", [
    b"SQLite format 3\x00" + b"private data",
    b"AKIA" + b"A" * 16,
    b"AIza" + b"a" * 35,
    b"-----BEGIN " + b"PRIVATE KEY-----",
    b"aws_secret_access_key=" + b"a" * 40,
])
def test_submission_scan_rejects_private_content_without_echoing_it(payload):
    with pytest.raises(ValueError) as error:
        scan_content("README.md", payload)
    assert payload.decode() not in str(error.value)


def write_test_archive(path, content=b"# Atlas", expected_content=None, extra=None,
                       manifest_digest=None, report=None):
    expected = content if expected_content is None else expected_content
    digest = payload_digest({"README.md": expected})
    payloads = {
        "README.md": expected,
        "evaluation_results/preflight_latest.json": json.dumps(
            passing_report(digest) if report is None else report,
        ).encode(),
    }
    manifest = {
        "source_sha256": digest if manifest_digest is None else manifest_digest,
        "files": {name: {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
                  for name, value in payloads.items()},
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in payloads.items():
            archive.writestr(f"Atlas/{name}", content if name == "README.md" else value)
        archive.writestr("Atlas/MANIFEST.json", json.dumps(manifest))
        if extra:
            archive.writestr(extra, b"unexpected")


def test_archive_manifest_matches_every_file(tmp_path):
    path = tmp_path / "valid.zip"
    write_test_archive(path)
    assert verify_archive(path)["verified"]
    write_test_archive(path, content=b"modified", expected_content=b"original")
    with pytest.raises(ValueError, match="integrity"):
        verify_archive(path)


@pytest.mark.parametrize("extra", ["Atlas/../../private", "Other/README.md", "Atlas/extra.txt"])
def test_archive_rejects_unsafe_or_unlisted_entries(tmp_path, extra):
    path = tmp_path / "invalid.zip"
    write_test_archive(path, extra=extra)
    with pytest.raises(ValueError):
        verify_archive(path)


def test_release_gate_must_cover_current_source(tmp_path):
    (tmp_path / "evaluation_results").mkdir()
    source = tmp_path / "app.py"
    source.write_text("pass\n")
    report = passing_report(source_digest(tmp_path))
    target = tmp_path / "evaluation_results/preflight_latest.json"
    target.write_text(json.dumps(report))
    require_release_gate(tmp_path)
    source.write_text("print('changed')\n")
    with pytest.raises(ValueError, match="Source changed"):
        require_release_gate(tmp_path)
    report["source_sha256"] = source_digest(tmp_path)
    report["checks"].pop()
    target.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="complete preflight"):
        require_release_gate(tmp_path)


@pytest.mark.parametrize("relative", [
    "data/evaluation_cases.json", "data/fixtures/chinese_books.json",
    "data/demo_profiles.json", "assets/atlas-mark.svg", "static/nexmind-logo.png",
    "docs/SUBMISSION_GUIDE.md", "README.md", ".env.example", ".gitignore",
])
def test_release_gate_covers_static_data_assets_docs_and_example_configuration(tmp_path, relative):
    source = tmp_path / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"original")
    target = tmp_path / "evaluation_results/preflight_latest.json"
    target.parent.mkdir()
    target.write_text(json.dumps(passing_report(source_digest(tmp_path))))
    require_release_gate(tmp_path)
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Source changed"):
        require_release_gate(tmp_path)


def test_payload_digest_is_order_independent_and_excludes_only_generated_reports():
    payloads = {"src/module.py": b"pass\n", "data/demo_profiles.json": b"[]", "README.md": b"Atlas"}
    expected = payload_digest(payloads)
    assert payload_digest(dict(reversed(list(payloads.items())))) == expected
    assert payload_digest({**payloads, "evaluation_results/preflight_latest.json": b"report"}) == expected
    assert payload_digest({**payloads, "evaluation_results/latest.json": b"result"}) == expected
    assert payload_digest({**payloads, "evaluation_results/live_latest.json": b"historic"}) == expected
    assert payload_digest({**payloads, "data/demo_profiles.json": b"[{}]"}) != expected


def test_archive_verifies_source_fingerprint_as_well_as_individual_file_hashes(tmp_path):
    archive = tmp_path / "mismatch.zip"
    write_test_archive(archive, manifest_digest="0" * 64)
    with pytest.raises(ValueError, match="Manifest source fingerprint"):
        verify_archive(archive)


def test_archive_rejects_rehashed_modified_source_with_stale_preflight(tmp_path):
    archive = tmp_path / "stale.zip"
    old_report = passing_report(payload_digest({"README.md": b"original"}))
    # File hashes and manifest fingerprint match the modified content, but the
    # preflight certifies different bytes. Integrity alone must not hide this.
    write_test_archive(archive, content=b"modified", report=old_report)
    with pytest.raises(ValueError, match="Source changed"):
        verify_archive(archive)


def test_archive_rejects_failed_preflight_even_when_all_hashes_match(tmp_path):
    archive = tmp_path / "failed.zip"
    report = passing_report(payload_digest({"README.md": b"# Atlas"}))
    report["passed"] = False
    write_test_archive(archive, report=report)
    with pytest.raises(ValueError, match="complete preflight"):
        verify_archive(archive)


def test_archive_requires_included_preflight(tmp_path):
    archive = tmp_path / "missing.zip"
    content = b"# Atlas"
    manifest = {
        "source_sha256": payload_digest({"README.md": content}),
        "files": {"README.md": {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}},
    }
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("Atlas/README.md", content)
        package.writestr("Atlas/MANIFEST.json", json.dumps(manifest))
    with pytest.raises(ValueError, match="complete preflight report"):
        verify_archive(archive)


def minimal_release_tree(root):
    for relative in ROOT_FILES | DATA_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture\n")
    target = root / "evaluation_results/preflight_latest.json"
    target.parent.mkdir()
    target.write_text(json.dumps(passing_report(source_digest(root))))


def test_build_uses_one_checked_snapshot_for_manifest_and_archive(tmp_path, monkeypatch):
    root = tmp_path / "project"
    minimal_release_tree(root)
    original = read_payloads(root)
    snapshot_calls = []

    def read_then_change_disk(project):
        snapshot_calls.append(project)
        snapshot = read_payloads(project)
        (project / "app.py").write_bytes(b"changed after snapshot\n")
        return snapshot

    monkeypatch.setattr(build_submission, "read_payloads", read_then_change_disk)
    archive = build_archive(root, tmp_path / "release")
    assert snapshot_calls == [root]
    assert verify_archive(archive)["verified"]
    with zipfile.ZipFile(archive) as package:
        assert package.read("Atlas/app.py") == original["app.py"]
        manifest = json.loads(package.read("Atlas/MANIFEST.json"))
        report = json.loads(package.read("Atlas/evaluation_results/preflight_latest.json"))
        assert manifest["source_sha256"] == report["source_sha256"] == payload_digest(original)


def test_build_rejects_changed_snapshot_before_creating_output(tmp_path):
    root = tmp_path / "project"
    minimal_release_tree(root)
    (root / "data/evaluation_cases.json").write_bytes(b"changed since preflight")
    output = tmp_path / "release"
    with pytest.raises(ValueError, match="Source changed"):
        build_archive(root, output)
    assert not output.exists()
