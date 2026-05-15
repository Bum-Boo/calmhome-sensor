from scripts.validate_configs import PROJECT_ROOT, iter_yaml_files, load_yaml_file, validate_project


def test_yaml_files_load_successfully() -> None:
    yaml_files = iter_yaml_files(PROJECT_ROOT)

    assert yaml_files
    for path in yaml_files:
        assert load_yaml_file(path) is not None


def test_required_entity_names_are_present() -> None:
    report = validate_project(PROJECT_ROOT)

    assert report["missing_required_names"] == []
    assert report["yaml_parse_errors"] == []
    assert report["missing_docs"] == []
