from scripts.validate_configs import PROJECT_ROOT, REQUIRED_MOCK_SCENARIOS, load_yaml_file, validate_mock_mode


def test_mock_mode_package_has_required_helpers() -> None:
    data = load_yaml_file(PROJECT_ROOT / "homeassistant/packages/calmhome_mock.yaml")

    assert "calmhome_mock_mode" in data["input_boolean"]
    assert "calmhome_mock_scenario" in data["input_select"]
    assert "calmhome_mock_last_activity_time" in data["input_datetime"]


def test_mock_mode_scenarios_are_available() -> None:
    data = load_yaml_file(PROJECT_ROOT / "homeassistant/packages/calmhome_mock.yaml")
    options = data["input_select"]["calmhome_mock_scenario"]["options"]

    assert set(REQUIRED_MOCK_SCENARIOS).issubset(options)


def test_mock_mode_validates() -> None:
    assert validate_mock_mode(PROJECT_ROOT) == []
