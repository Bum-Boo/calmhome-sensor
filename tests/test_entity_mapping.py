from scripts.validate_configs import (
    EXPECTED_LOGICAL_ENTITY_NAMES,
    PROJECT_ROOT,
    load_yaml_file,
    validate_entity_mapping_examples,
)


def test_entity_mapping_examples_have_required_schema() -> None:
    for relative_path in ("config/entities.example.yaml", "config/entities.local.example.yaml"):
        data = load_yaml_file(PROJECT_ROOT / relative_path)

        assert data["version"] == 1
        assert set(data["logical_entities"]) == set(EXPECTED_LOGICAL_ENTITY_NAMES)
        assert all(isinstance(value, str) and value for value in data["logical_entities"].values())


def test_entity_mapping_examples_validate() -> None:
    assert validate_entity_mapping_examples(PROJECT_ROOT) == []
