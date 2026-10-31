from pathlib import Path

from scripts.validate_configs import PROJECT_ROOT, validate_project, validate_template_entities


def test_core_package_template_entities_use_supported_options() -> None:
    assert validate_template_entities(PROJECT_ROOT) == []
    assert validate_project(PROJECT_ROOT)["template_entity_errors"] == []


def test_entity_category_on_template_sensor_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "homeassistant" / "packages" / "calmhome.yaml"
    package.parent.mkdir(parents=True)
    package.write_text(
        "template:\n"
        "  - sensor:\n"
        "      - name: Distance\n"
        "        state: '1'\n"
        "        entity_category: diagnostic\n",
        encoding="utf-8",
    )

    errors = validate_template_entities(tmp_path)

    assert len(errors) == 1
    assert "entity_category" in errors[0]
