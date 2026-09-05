"""Read-only dependency consistency check; never installs or calls a service."""
from __future__ import annotations

import argparse
import importlib.metadata as metadata
import platform
import tomllib
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name


def check_dependencies(include_dev: bool = False) -> list[str]:
    config = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    issues = []
    if platform.python_version() not in SpecifierSet(config["project"]["requires-python"]):
        issues.append(f"Unsupported Python {platform.python_version()}")
    pending = [Requirement(item) for item in config["project"]["dependencies"]]
    if include_dev:
        pending.extend(Requirement(item) for item in config["dependency-groups"]["dev"])
    seen = set()
    while pending:
        requirement = pending.pop()
        name = canonicalize_name(requirement.name)
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            issues.append(f"Missing dependency: {name}")
            continue
        if requirement.specifier and not requirement.specifier.contains(dist.version, prereleases=True):
            issues.append(f"Incompatible dependency: {name} {dist.version}; requires {requirement.specifier}")
        identity = (name, tuple(sorted(requirement.extras)))
        if identity in seen:
            continue
        seen.add(identity)
        for raw in dist.requires or []:
            child = Requirement(raw)
            environments = [{**default_environment(), "extra": extra} for extra in {"", *requirement.extras}]
            if child.marker is None or any(child.marker.evaluate(environment) for environment in environments):
                pending.append(child)
    return sorted(set(issues))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
    issues = check_dependencies(args.dev)
    for issue in issues:
        print(issue)
    print("Dependency consistency: " + ("FAIL" if issues else "PASS"))
    raise SystemExit(1 if issues else 0)


if __name__ == "__main__":
    main()
