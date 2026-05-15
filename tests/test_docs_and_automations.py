from scripts.validate_configs import (
    PROJECT_ROOT,
    REQUIRED_NOTIFICATION_ALIASES,
    load_yaml_file,
    validate_notification_automations,
    validate_required_docs,
)


def test_required_documentation_files_exist() -> None:
    assert validate_required_docs(PROJECT_ROOT) == []


def test_notification_automation_names_exist() -> None:
    data = load_yaml_file(PROJECT_ROOT / "homeassistant/packages/calmhome.yaml")
    aliases = {automation["alias"] for automation in data["automation"]}

    assert set(REQUIRED_NOTIFICATION_ALIASES).issubset(aliases)
    assert validate_notification_automations(PROJECT_ROOT) == []


def test_runtime_test_plan_contains_manual_cases() -> None:
    text = (PROJECT_ROOT / "docs/RUNTIME_TEST_PLAN.md").read_text(encoding="utf-8").lower()

    for phrase in (
        "normal entry",
        "room empty",
        "seated still presence",
        "walking movement",
        "simulated fall event",
        "long inactivity",
        "door opened while occupied",
        "sensor offline",
    ):
        assert phrase in text
