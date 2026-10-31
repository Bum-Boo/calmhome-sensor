import shutil
from pathlib import Path

import pytest

from scripts.validate_configs import (
    CORE_PACKAGE_PATH,
    PROJECT_ROOT,
    load_yaml_file,
    validate_mapping_file,
    validate_project,
)


@pytest.fixture()
def project_copy(tmp_path: Path) -> Path:
    for name in ("config", "esphome", "homeassistant", "dashboards", "docs"):
        shutil.copytree(PROJECT_ROOT / name, tmp_path / name)
    shutil.copy(PROJECT_ROOT / "README.md", tmp_path / "README.md")
    (tmp_path / "config" / "entities.local.yaml").unlink(missing_ok=True)
    return tmp_path


def write_mapping(path: Path, **overrides: str) -> Path:
    data = load_yaml_file(PROJECT_ROOT / "config" / "entities.example.yaml")["logical_entities"]
    data.update(overrides)
    lines = ["version: 1", "logical_entities:"] + [f"  {key}: {value}" for key, value in data.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_repository_copy_validates(project_copy: Path) -> None:
    assert validate_project(project_copy)["ok"] is True


def test_empty_mock_sections_are_reported_not_crashing(project_copy: Path) -> None:
    (project_copy / "homeassistant/packages/calmhome_mock.yaml").write_text(
        "input_boolean:\ninput_select:\ninput_datetime:\n", encoding="utf-8"
    )

    report = validate_project(project_copy)

    assert report["ok"] is False
    assert any("calmhome_mock_mode" in error for error in report["mock_mode_errors"])


def test_empty_automation_section_is_reported_not_crashing(project_copy: Path) -> None:
    core = project_copy / CORE_PACKAGE_PATH
    text = core.read_text(encoding="utf-8")
    core.write_text(text[: text.index("\nautomation:")] + "\nautomation:\n", encoding="utf-8")

    report = validate_project(project_copy)

    assert report["ok"] is False
    assert report["notification_automation_errors"]


def test_unparseable_mapping_file_is_reported_not_crashing(project_copy: Path) -> None:
    (project_copy / "config/entities.example.yaml").write_text("logical_entities: [\n", encoding="utf-8")

    report = validate_project(project_copy)

    assert report["ok"] is False
    assert any("could not be parsed" in error for error in report["entity_mapping_errors"])


def test_malformed_entity_id_is_rejected(tmp_path: Path) -> None:
    path = write_mapping(tmp_path / "entities.yaml", presence_detected="binary_sensor.my presence")

    errors = validate_mapping_file(path)

    assert any("presence_detected" in error and "entity ID" in error for error in errors)


def test_wrong_domain_is_rejected(tmp_path: Path) -> None:
    path = write_mapping(
        tmp_path / "entities.yaml",
        presence_detected="sensor.calmhome_presence_detected",
        target_distance="binary_sensor.calmhome_target_distance",
    )

    errors = validate_mapping_file(path)

    assert any("presence_detected" in error and "binary_sensor" in error for error in errors)
    assert any("target_distance" in error and "sensor." in error for error in errors)


def test_local_mapping_file_is_validated_when_present(project_copy: Path) -> None:
    write_mapping(project_copy / "config/entities.local.yaml", sensor_online="binary_sensor.")

    report = validate_project(project_copy)

    assert report["ok"] is False
    assert any("entities.local.yaml" in error for error in report["entity_mapping_errors"])


def test_valid_local_mapping_file_passes(project_copy: Path) -> None:
    write_mapping(project_copy / "config/entities.local.yaml", presence_detected="binary_sensor.bedroom_radar_presence")

    assert validate_project(project_copy)["ok"] is True


def test_package_mapping_defaults_match_example_mapping() -> None:
    package = load_yaml_file(PROJECT_ROOT / CORE_PACKAGE_PATH)
    example = load_yaml_file(PROJECT_ROOT / "config/entities.example.yaml")["logical_entities"]

    defaults = {
        key.removeprefix("calmhome_entity_"): value["initial"] for key, value in package["input_text"].items()
    }
    assert defaults == example
