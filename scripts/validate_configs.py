#!/usr/bin/env python3
"""Validate calmhome-sensor YAML files, docs, mapping, mock mode, and guardrails."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
YAML_DIR_NAMES = ("config", "esphome", "homeassistant", "dashboards")

EXPECTED_LOGICAL_ENTITY_NAMES = (
    "presence_detected",
    "movement_detected",
    "still_presence_detected",
    "target_distance",
    "fall_detected",
    "door_opened",
    "sensor_online",
)

REQUIRED_ENTITY_NAMES = EXPECTED_LOGICAL_ENTITY_NAMES + (
    "room_state",
    "presence_confirmed",
    "fall_suspected",
    "long_inactivity",
    "last_activity_time",
)

REQUIRED_MOCK_SCENARIOS = (
    "room_empty",
    "presence_detected",
    "movement_detected",
    "still_presence",
    "fall_suspected",
    "long_inactivity",
    "door_opened",
)

REQUIRED_NOTIFICATION_ALIASES = (
    "CalmHome Fall Suspected Notification",
    "CalmHome Long Inactivity Notification",
    "CalmHome Door Opened While Occupied Event",
    "CalmHome Sensor Offline Notification",
    "CalmHome Daily Summary Notification",
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
    Path("docs") / "INSTALL_HOME_ASSISTANT.md",
    Path("docs") / "INSTALL_ESPHOME.md",
    Path("docs") / "SENSOR_PLACEMENT.md",
    Path("docs") / "RUNTIME_TEST_PLAN.md",
)

ENTITY_MAPPING_EXAMPLE_PATH = Path("config") / "entities.example.yaml"
ENTITY_MAPPING_LOCAL_EXAMPLE_PATH = Path("config") / "entities.local.example.yaml"
MOCK_MODE_PACKAGE_PATH = Path("homeassistant") / "packages" / "calmhome_mock.yaml"
CORE_PACKAGE_PATH = Path("homeassistant") / "packages" / "calmhome.yaml"


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
            errors.append(f"YAML parse failed: {path}: {exc}")
    return errors


def find_missing_required_names(files: Iterable[Path]) -> list[str]:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    return [name for name in REQUIRED_ENTITY_NAMES if name not in combined]


def normalize_guardrail_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[\s\-]+", "_", lowered)
    return lowered


def scan_for_forbidden_terms(files: Iterable[Path]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for path in files:
        text = normalize_guardrail_text(path.read_text(encoding="utf-8"))
        for term in FORBIDDEN_FEATURE_TERMS:
            if term in text:
                issues.append(
                    {
                        "file": str(path),
                        "term": term,
                        "message": f"Forbidden sensing/surveillance feature term '{term}' found in deployable YAML.",
                    }
                )
    return issues


def required_doc_files(root: Path = PROJECT_ROOT) -> tuple[Path, ...]:
    return tuple(root / path for path in REQUIRED_DOC_PATHS)


def validate_required_docs(root: Path = PROJECT_ROOT) -> list[str]:
    return [f"Missing required documentation file: {path}" for path in required_doc_files(root) if not path.exists()]


def validate_mapping_file(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"Missing entity mapping example: {path}"]

    data = load_yaml_file(path)
    if not isinstance(data, dict):
        return [f"Entity mapping file must be a YAML mapping: {path}"]

    logical_entities = data.get("logical_entities")
    if not isinstance(logical_entities, dict):
        return [f"Entity mapping file must contain logical_entities mapping: {path}"]

    for name in EXPECTED_LOGICAL_ENTITY_NAMES:
        value = logical_entities.get(name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Entity mapping '{name}' must be a non-empty string in {path}")

    extra = sorted(set(logical_entities) - set(EXPECTED_LOGICAL_ENTITY_NAMES))
    if extra:
        errors.append(f"Entity mapping file has unexpected logical names in {path}: {extra}")

    return errors


def validate_entity_mapping_examples(root: Path = PROJECT_ROOT) -> list[str]:
    return validate_mapping_file(root / ENTITY_MAPPING_EXAMPLE_PATH) + validate_mapping_file(
        root / ENTITY_MAPPING_LOCAL_EXAMPLE_PATH
    )


def validate_mock_mode(root: Path = PROJECT_ROOT) -> list[str]:
    path = root / MOCK_MODE_PACKAGE_PATH
    if not path.exists():
        return [f"Missing Home Assistant mock mode package: {path}"]

    errors: list[str] = []
    data = load_yaml_file(path)
    if not isinstance(data, dict):
        return [f"Mock mode package must be a YAML mapping: {path}"]

    if "calmhome_mock_mode" not in data.get("input_boolean", {}):
        errors.append("Mock mode package must define input_boolean.calmhome_mock_mode")

    scenario = data.get("input_select", {}).get("calmhome_mock_scenario", {})
    options = scenario.get("options", []) if isinstance(scenario, dict) else []
    missing = [option for option in REQUIRED_MOCK_SCENARIOS if option not in options]
    if missing:
        errors.append(f"Mock scenario selector is missing options: {missing}")

    if "calmhome_mock_last_activity_time" not in data.get("input_datetime", {}):
        errors.append("Mock mode package must define input_datetime.calmhome_mock_last_activity_time")

    return errors


def validate_notification_automations(root: Path = PROJECT_ROOT) -> list[str]:
    path = root / CORE_PACKAGE_PATH
    if not path.exists():
        return [f"Missing Home Assistant core package: {path}"]

    data = load_yaml_file(path)
    automations = data.get("automation", []) if isinstance(data, dict) else []
    aliases = {item.get("alias") for item in automations if isinstance(item, dict)}
    missing = [alias for alias in REQUIRED_NOTIFICATION_ALIASES if alias not in aliases]
    return [f"Missing notification automation aliases: {missing}"] if missing else []


def validate_project(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    yaml_files = iter_yaml_files(root)
    deployable_yaml_files = [
        path
        for path in yaml_files
        if any(part in {"config", "esphome", "homeassistant", "dashboards"} for part in path.parts)
    ]

    report = {
        "project_root": str(root),
        "yaml_files": [str(path) for path in yaml_files],
        "yaml_parse_errors": validate_yaml_files(yaml_files),
        "missing_required_names": find_missing_required_names(yaml_files),
        "forbidden_feature_issues": scan_for_forbidden_terms(deployable_yaml_files),
        "missing_docs": validate_required_docs(root),
        "entity_mapping_errors": validate_entity_mapping_examples(root),
        "mock_mode_errors": validate_mock_mode(root),
        "notification_automation_errors": validate_notification_automations(root),
    }
    report["ok"] = not any(
        [
            report["yaml_parse_errors"],
            report["missing_required_names"],
            report["forbidden_feature_issues"],
            report["missing_docs"],
            report["entity_mapping_errors"],
            report["mock_mode_errors"],
            report["notification_automation_errors"],
        ]
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate calmhome-sensor YAML, docs, mapping, mock mode, and privacy guardrails."
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
            for key, label in (
                ("yaml_parse_errors", "YAML parse errors"),
                ("missing_required_names", "Missing required names"),
                ("forbidden_feature_issues", "Forbidden feature issues"),
                ("missing_docs", "Missing docs"),
                ("entity_mapping_errors", "Entity mapping errors"),
                ("mock_mode_errors", "Mock mode errors"),
                ("notification_automation_errors", "Notification automation errors"),
            ):
                if report[key]:
                    print(f"{label}:")
                    for item in report[key]:
                        print(f"  - {item}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
