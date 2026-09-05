"""Cross-platform, explicit demo/live launcher. No installer or credential probes.

Run ``python launch.py --check`` to validate the supplied package without
starting a server, opening a browser or creating a learning database.
"""
from __future__ import annotations

import argparse
import configparser
import os
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from importlib import metadata
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIRED_ASSETS = (
    "app.py", "src/config.py", ".streamlit/config.toml",
    "data/fixtures/book_api_responses.json", "data/fixtures/chinese_books.json",
)
DEMO_ONLY_ENV = {
    "APP_MODE": "demo",
    "LLM_PROVIDER": "mock",
    "AWS_PROFILE": "",
    "AWS_DEFAULT_PROFILE": "",
    "AWS_ACCESS_KEY_ID": "",
    "AWS_SECRET_ACCESS_KEY": "",
    "AWS_SESSION_TOKEN": "",
    "BEDROCK_MODEL_ID": "",
    "BEDROCK_LEARNING_MODEL_ID": "",
    "GOOGLE_BOOKS_API_KEY": "",
    "AWS_EC2_METADATA_DISABLED": "true",
    "LANGCHAIN_TRACING_V2": "false",
    "LANGSMITH_TRACING": "false",
}


def port_number(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Port must be a number from 1 to 65535.") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535.")
    return port


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Start Atlas safely in demo or explicitly enabled live mode.")
    result.add_argument("--mode", choices=("demo", "live"), default="demo",
                        help="demo: included examples and local rules (default); live: your own AWS and catalogue access")
    result.add_argument("--port", type=port_number, default=8501)
    result.add_argument("--no-browser", action="store_true", help="Do not open the default browser")
    result.add_argument("--check", action="store_true", help="Check local prerequisites and configuration, then exit")
    return result


def dependency_errors(root: Path = PROJECT_ROOT) -> list[str]:
    """Compare installed direct dependencies with the tested release pins."""
    if sys.version_info < (3, 11):  # noqa: UP036 - this bootstrap runs before dependencies are installed.
        return ["Python 3.11 or later is required. Create the virtual environment with a supported Python."]
    import tomllib

    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ["pyproject.toml is missing or invalid. Extract the complete submission package first."]
    problems = []
    for requirement in project["project"]["dependencies"]:
        match = re.fullmatch(r"([\w.-]+)==([\w.+-]+)", requirement)
        if match is None:
            problems.append(f"Unpinned release dependency: {requirement}")
            continue
        name, expected = match.groups()
        try:
            actual = metadata.version(name)
        except metadata.PackageNotFoundError:
            problems.append(f"Missing package: {name}=={expected}")
        else:
            if actual != expected:
                problems.append(f"{name}: installed {actual}, expected {expected}")
    if problems:
        problems.append("Install into this Python environment: python -m pip install -r requirements.txt (or uv sync --frozen).")
    return problems


def prepare_environment(mode: str, root: Path = PROJECT_ROOT,
                        inherited: dict[str, str] | None = None) -> dict[str, str]:
    """Build a child environment; never create/overwrite .env or modify os.environ."""
    current = dict(os.environ if inherited is None else inherited)
    if mode == "demo":
        current.update(DEMO_ONLY_ENV)
        # Demo cannot select or overwrite an existing live workspace through .env.
        current["DATABASE_PATH"] = str(root / "data" / "demo.db")
    elif mode == "live":
        from dotenv import dotenv_values

        local_values = {key: value for key, value in dotenv_values(root / ".env").items() if value is not None}
        current = {**local_values, **current, "APP_MODE": "live", "LLM_PROVIDER": "bedrock"}
        if not current.get("DATABASE_PATH", "").strip():
            current["DATABASE_PATH"] = str(root / "data" / "nexmind_atlas.db")
    else:
        raise ValueError("Unknown mode: choose demo or live.")
    current["PYTHONUTF8"] = "1"
    current["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    return current


def has_local_aws_configuration(environment: dict[str, str]) -> bool:
    """Only inspect configuration presence. Never request credentials or tokens."""
    if environment.get("AWS_ACCESS_KEY_ID") and environment.get("AWS_SECRET_ACCESS_KEY"):
        return True
    if any(environment.get(key) for key in (
        "AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    )):
        return True
    profile = environment.get("AWS_PROFILE") or environment.get("AWS_DEFAULT_PROFILE") or "default"
    credentials_file = Path(environment.get("AWS_SHARED_CREDENTIALS_FILE") or Path.home() / ".aws" / "credentials")
    config_file = Path(environment.get("AWS_CONFIG_FILE") or Path.home() / ".aws" / "config")
    for path, section in ((credentials_file, profile), (config_file, "default" if profile == "default" else f"profile {profile}")):
        settings = configparser.RawConfigParser()
        try:
            settings.read(path, encoding="utf-8")
        except (OSError, configparser.Error):
            continue
        if settings.has_section(section) and any(settings.has_option(section, key) for key in (
            "aws_access_key_id", "credential_process", "sso_session", "sso_start_url", "role_arn",
        )):
            return True
    return False


def configuration_errors(mode: str, environment: dict[str, str], root: Path = PROJECT_ROOT) -> list[str]:
    errors = [f"Missing package resource: {relative}" for relative in REQUIRED_ASSETS if not (root / relative).is_file()]
    if mode == "live":
        model = environment.get("BEDROCK_MODEL_ID", "").strip()
        if not model or model.casefold().startswith(("your_", "replace_", "example")):
            errors.append("Live mode needs your BEDROCK_MODEL_ID (model or inference-profile ID) in .env or the environment.")
        if not has_local_aws_configuration(environment):
            errors.append("No local AWS configuration found. Configure your own AWS profile/SSO or AWS credential environment variables before live mode.")
        path = Path(environment["DATABASE_PATH"])
        resolved = (path if path.is_absolute() else root / path).resolve()
        if resolved == (root / "data" / "demo.db").resolve():
            errors.append("Live DATABASE_PATH cannot be data/demo.db. Choose a separate live database to keep example and live records apart.")
    return errors


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        try:
            candidate.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def server_command(port: int, root: Path = PROJECT_ROOT) -> list[str]:
    return [sys.executable, "-m", "streamlit", "run", str(root / "app.py"),
            "--server.port", str(port), "--server.address", "127.0.0.1",
            "--server.headless", "true", "--server.fileWatcherType", "none",
            "--browser.gatherUsageStats", "false"]


def open_when_ready(url: str, process: subprocess.Popen) -> None:
    """Open only a local URL, after the server responds; never require a browser."""
    for _ in range(90):
        if process.poll() is not None:
            return
        try:
            with urlopen(f"{url}/_stcore/health", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except (OSError, URLError):
            pass
        time.sleep(1)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    errors = dependency_errors()
    if errors:
        for error in errors:
            print(f"[Atlas] {error}", file=sys.stderr)
        return 2
    environment = prepare_environment(args.mode)
    errors = configuration_errors(args.mode, environment)
    if errors:
        for error in errors:
            print(f"[Atlas] {error}", file=sys.stderr)
        return 2
    print(f"[Atlas] Mode: {args.mode}", flush=True)
    if args.mode == "demo":
        print("[Atlas] Included book examples and local rules. No AWS/model/catalogue API calls; this is not a live AI quality evaluation.", flush=True)
        print("[Atlas] Learning records: data/demo.db. Book-cover images may still load from external image hosts.", flush=True)
    else:
        print("[Atlas] Live mode uses your own AWS account and external catalogue services; usage may incur charges.", flush=True)
        print("[Atlas] Credentials, model access and quotas are checked by AWS only when a feature is used, not by this launcher.", flush=True)
    if args.check:
        print("[Atlas] Local checks passed. No server, browser, API request or database was started.", flush=True)
        return 0
    if not port_available(args.port):
        print(f"[Atlas] Port {args.port} is already in use. Choose another port with --port, or stop your existing Atlas server.", file=sys.stderr)
        return 2
    url = f"http://localhost:{args.port}"
    print(f"[Atlas] Open {url}  |  Stop with Ctrl+C", flush=True)
    process = subprocess.Popen(server_command(args.port), cwd=PROJECT_ROOT, env=environment)
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url, process), daemon=True).start()
    try:
        return process.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
