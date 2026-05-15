#!/usr/bin/env python3
"""Validate calmhome-sensor YAML files and privacy guardrails."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
YAML_DIR_NAMES = ("esphome", "homeassistant", "dashboards")

REQUIRED_ENTITY_NAMES = (
    "presence_detected",
    "movement_detected",
    "still_presence_detected",
    "target_distance",
    "fall_detected",
    "sensor_online",
    "room_state",
    "presence_confirmed",
    "fall_suspected",
    "long_inactivity",
    "last_activity_time",
)

FORBIDDEN_FEATURE_TERMS = (
    "camera",
    "microphone",
    "face_recognition",
    "silhouette",
    "raw_point_cloud_export",
    "router_hack",
    "packet_sniffing",
    "through_wall",
)

REQUIRED_DOC_PATHS = (
    Path("README.md"),
    Path("docs") / "HARDWARE.md",
    Path("docs") / "PRIVACY.md",
)


class CalmHomeYamlLoader(yaml.SafeLoader):
    """PyYAML loader that tolerates Home Assistant tags such as !secret."""


def _construct_unknown_tag(loader: CalmHomeYamlLoader, tag_suffix: str, node: yaml.Node) -> Any:
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None


CalmHomeYamlLoader.add_multi_constructor("!", _construct_unknown_tag)


def iter_yaml_files(root: Path = PROJECT_ROOT) -> list[Path]:
    files: list[Path] = []
    for directory_name in YAML_DIR_NAMES:
        directory = root / directory_name
        if not directory.exists():
            continue
        files.extend(sorted(directory.rglob("*.yaml")))
        files.extend(sorted(directory.rglob("*.yml")))
    return sorted({path.resolve() for path in files})


def load_yaml_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=CalmHomeYamlLoader)


def validate_yaml_files(files: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for path in files:
        try:
            load_yaml_file(path)
        except Exception as exc:  # noqa: BLE001 - report parser context to CLI.
            errors.append(f"{path}: {exc}")
    return errors


def find_missing_required_names(files: Iterable[Path]) -> list[str]:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    return [name for name in REQUIRED_ENTITY_NAMES if name not in combined]


def scan_for_forbidden_terms(files: Iterable[Path]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8").lower()
        for term in FORBIDDEN_FEATURE_TERMS:
            if term in text:
                issues.append({"file": str(path), "term": term})
    return issues


def required_doc_files(root: Path = PROJECT_ROOT) -> tuple[Path, ...]:
    return tuple(root / path for path in REQUIRED_DOC_PATHS)


def validate_required_docs(root: Path = PROJECT_ROOT) -> list[str]:
    return [str(path) for path in required_doc_files(root) if not path.exists()]


def validate_project(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    yaml_files = iter_yaml_files(root)
    missing_docs = validate_required_docs(root)

    report = {
        "project_root": str(root),
        "yaml_files": [str(path) for path in yaml_files],
        "yaml_parse_errors": validate_yaml_files(yaml_files),
        "missing_required_names": find_missing_required_names(yaml_files),
        "forbidden_feature_issues": scan_for_forbidden_terms(yaml_files),
        "missing_docs": missing_docs,
    }
    report["ok"] = not any(
        [
            report["yaml_parse_errors"],
            report["missing_required_names"],
            report["forbidden_feature_issues"],
            report["missing_docs"],
        ]
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate calmhome-sensor YAML and privacy guardrails."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable validation output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = validate_project()

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Project root: {report['project_root']}")
        print(f"YAML files parsed: {len(report['yaml_files'])}")
        if report["ok"]:
            print("Validation passed.")
        else:
            print("Validation failed.")
            for key in (
                "yaml_parse_errors",
                "missing_required_names",
                "forbidden_feature_issues",
                "missing_docs",
            ):
                if report[key]:
                    print(f"{key}: {report[key]}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
