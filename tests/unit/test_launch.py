import inspect
import socket
import sys
import tomllib
from importlib import metadata
from pathlib import Path
from unittest.mock import Mock

import pytest

import launch


def resources(root: Path) -> None:
    for relative in launch.REQUIRED_ASSETS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture", encoding="utf-8")


def test_default_is_explicit_demo_and_port_is_validated():
    args = launch.parser().parse_args([])
    assert args.mode == "demo" and args.port == 8501
    assert not args.no_browser
    for value in ("0", "65536", "invalid"):
        with pytest.raises(SystemExit):
            launch.parser().parse_args(["--port", value])
    assert launch.parser().parse_args(["--mode", "live", "--port", "8519", "--no-browser"]).no_browser


def test_demo_isolates_data_ignores_existing_live_env_and_does_not_overwrite_it(tmp_path):
    existing = "LLM_PROVIDER=bedrock\nBEDROCK_MODEL_ID=private-model\nDATABASE_PATH=data/existing.db\n"
    env_file = tmp_path / ".env"
    env_file.write_text(existing, encoding="utf-8")
    inherited = {"APP_MODE": "live", "LLM_PROVIDER": "bedrock", "DATABASE_PATH": "sensitive.db",
                 "AWS_ACCESS_KEY_ID": "private-key", "AWS_SECRET_ACCESS_KEY": "private-secret",
                 "BEDROCK_LEARNING_MODEL_ID": "private-learning-model", "GOOGLE_BOOKS_API_KEY": "private-catalogue-key"}
    environment = launch.prepare_environment("demo", tmp_path, inherited)
    assert environment["LLM_PROVIDER"] == "mock" and environment["APP_MODE"] == "demo"
    assert Path(environment["DATABASE_PATH"]) == tmp_path / "data" / "demo.db"
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "BEDROCK_MODEL_ID", "BEDROCK_LEARNING_MODEL_ID", "GOOGLE_BOOKS_API_KEY"):
        assert environment[key] == ""
    assert inherited["AWS_ACCESS_KEY_ID"] == "private-key"
    assert env_file.read_text(encoding="utf-8") == existing
    assert not (tmp_path / "data" / "demo.db").exists()


def test_live_reads_own_config_env_takes_precedence_and_demo_db_is_rejected(tmp_path):
    resources(tmp_path)
    (tmp_path / ".env").write_text("BEDROCK_MODEL_ID=own-model\nAWS_PROFILE=my-profile\nDATABASE_PATH=data/live.db\n", encoding="utf-8")
    environment = launch.prepare_environment("live", tmp_path, {
        "BEDROCK_MODEL_ID": "override-model", "AWS_ACCESS_KEY_ID": "own-key", "AWS_SECRET_ACCESS_KEY": "own-secret",
    })
    assert environment["APP_MODE"] == "live" and environment["LLM_PROVIDER"] == "bedrock"
    assert environment["BEDROCK_MODEL_ID"] == "override-model"
    assert environment["DATABASE_PATH"] == "data/live.db"
    assert not launch.configuration_errors("live", environment, tmp_path)
    environment["DATABASE_PATH"] = "data/demo.db"
    assert any("separate live database" in error for error in launch.configuration_errors("live", environment, tmp_path))


def test_live_missing_model_and_own_credentials_are_actionable_local_errors(tmp_path):
    resources(tmp_path)
    environment = launch.prepare_environment("live", tmp_path, {
        "AWS_CONFIG_FILE": str(tmp_path / "no-config"),
        "AWS_SHARED_CREDENTIALS_FILE": str(tmp_path / "no-credentials"),
    })
    errors = launch.configuration_errors("live", environment, tmp_path)
    assert any("BEDROCK_MODEL_ID" in error for error in errors)
    assert any("AWS configuration" in error for error in errors)


def test_aws_profile_presence_is_inspected_without_exposing_values(tmp_path):
    credentials = tmp_path / "credentials"
    credentials.write_text("[custom]\naws_access_key_id=private-key\naws_secret_access_key=private-secret\n", encoding="utf-8")
    environment = {"AWS_PROFILE": "custom", "AWS_SHARED_CREDENTIALS_FILE": str(credentials),
                   "AWS_CONFIG_FILE": str(tmp_path / "none")}
    assert launch.has_local_aws_configuration(environment)
    environment["AWS_PROFILE"] = "missing"
    assert not launch.has_local_aws_configuration(environment)


def test_missing_or_mismatched_dependencies_give_install_instructions(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies=["streamlit==1.62.0"]\n', encoding="utf-8")
    monkeypatch.setattr(metadata, "version", lambda _name: "1.40.0")
    assert any("expected 1.62.0" in error for error in launch.dependency_errors(tmp_path))
    monkeypatch.setattr(metadata, "version", Mock(side_effect=metadata.PackageNotFoundError()))
    errors = launch.dependency_errors(tmp_path)
    assert any("Missing package" in error for error in errors)
    assert any("requirements.txt" in error for error in errors)


def test_release_pins_and_installed_streamlit_support_the_used_apis():
    import streamlit

    project = tomllib.loads((launch.PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "streamlit==1.62.0" in project["project"]["dependencies"]
    assert "accept_new_options" in inspect.signature(streamlit.multiselect).parameters
    assert "on_dismiss" in inspect.signature(streamlit.dialog).parameters
    requirements = (launch.PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "numpy==2.4.6 ; python_full_version < '3.12'" in requirements
    assert "sys_platform" in requirements  # Keep Windows/macOS/Linux dependency branches.
    assert all("==" in line for line in requirements.splitlines() if line and not line.startswith("#"))


def test_port_conflict_does_not_stop_or_replace_the_existing_service():
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        assert not launch.port_available(occupied.getsockname()[1])


def test_server_uses_same_python_absolute_app_and_loopback_only():
    command = launch.server_command(8519)
    assert command[0] == sys.executable
    assert str(launch.PROJECT_ROOT / "app.py") in command
    assert command[command.index("--server.address") + 1] == "127.0.0.1"
    assert command[command.index("--server.port") + 1] == "8519"


def test_check_never_starts_server_opens_browser_or_prints_credentials(tmp_path, monkeypatch, capsys):
    private = "never-display-this-secret"
    monkeypatch.setattr(launch, "dependency_errors", lambda: [])
    monkeypatch.setattr(launch, "prepare_environment", lambda mode: {"APP_MODE": mode, "AWS_SECRET_ACCESS_KEY": private})
    monkeypatch.setattr(launch, "configuration_errors", lambda *_: [])
    no_process = Mock(side_effect=AssertionError("--check must not start a server"))
    monkeypatch.setattr(launch.subprocess, "Popen", no_process)
    monkeypatch.setattr(launch.webbrowser, "open", no_process)
    assert launch.main(["--mode", "live", "--check"]) == 0
    output = capsys.readouterr()
    assert private not in output.out + output.err
    no_process.assert_not_called()
