from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from scripts.build_submission import source_digest
from src.config import PROJECT_ROOT

REPORT_PATH = PROJECT_ROOT / "evaluation_results" / "preflight_latest.json"
SCANNED_SUFFIXES = {
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
IGNORED_PARTS = {".git", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__", "dist"}
SECRET_PATTERNS = {
    "AWS access-key-shaped value": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Google API-key-shaped value": re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"),
    "AWS secret-key assignment": re.compile(
        r"aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+]{40}(?:['\"]|\b)",
        re.IGNORECASE,
    ),
}


def _run(name: str, command: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "name": name,
        "passed": completed.returncode == 0,
        "command": ["python", *command[1:]],
        "return_code": completed.returncode,
        "output_tail": (completed.stdout + completed.stderr)[-4000:].replace(str(PROJECT_ROOT), "."),
    }


def _secret_scan() -> dict[str, object]:
    findings: list[dict[str, object]] = []
    for root, directory_names, file_names in os.walk(PROJECT_ROOT):
        directory_names[:] = [name for name in directory_names if name not in IGNORED_PARTS]
        root_path = Path(root)
        for file_name in file_names:
            path = root_path / file_name
            if path.name == ".env" or path.suffix.lower() not in SCANNED_SUFFIXES:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for label, pattern in SECRET_PATTERNS.items():
                for match in pattern.finditer(content):
                    findings.append(
                        {
                            "kind": label,
                            "file": str(path.relative_to(PROJECT_ROOT)),
                            "line": content.count("\n", 0, match.start()) + 1,
                        }
                    )
    return {
        "name": "secret scan",
        "passed": not findings,
        "scanned_suffixes": sorted(SCANNED_SUFFIXES),
        "findings": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NexMind Atlas release-readiness checks.")
    parser.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="Skip the free deterministic evaluation when iterating locally.",
    )
    args = parser.parse_args()

    checked_source = source_digest()
    checks = [
        _run("ruff", [sys.executable, "-m", "ruff", "check", "."]),
        _run("dependencies", [sys.executable, "-m", "scripts.check_dependencies", "--dev"]),
        _run("pytest", [sys.executable, "-m", "pytest", "-q"]),
        _run(
            "compileall",
            [sys.executable, "-m", "compileall", "-q", "app.py", "launch.py", "src", "scripts", "tests"],
        ),
        _secret_scan(),
    ]
    if not args.skip_evaluation:
        checks.append(
            _run(
                "deterministic evaluation",
                [sys.executable, "-m", "scripts.run_evaluation"],
            )
        )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": all(bool(check["passed"]) for check in checks) and checked_source == source_digest(),
        "source_sha256": checked_source,
        "source_unchanged_during_checks": checked_source == source_digest(),
        "checks": checks,
        "notes": [
            "This command is free and does not call Bedrock.",
            "Run scripts/run_live_evaluation.py --confirm-live-cost separately for live acceptance.",
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for check in checks:
        print(f"{'PASS' if check['passed'] else 'FAIL'}  {check['name']}")
    print(f"Report: {REPORT_PATH}")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
