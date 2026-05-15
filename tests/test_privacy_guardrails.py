from pathlib import Path

from scripts.validate_configs import (
    PROJECT_ROOT,
    required_doc_files,
    scan_for_forbidden_terms,
    validate_project,
)


def test_config_guardrails_pass_for_repository() -> None:
    report = validate_project(PROJECT_ROOT)
    assert report["forbidden_feature_issues"] == []


def test_forbidden_feature_term_in_yaml_is_rejected(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("sensor:\n  - platform: camera\n", encoding="utf-8")

    issues = scan_for_forbidden_terms([bad_file])

    assert issues == [{"file": str(bad_file), "term": "camera"}]


def test_privacy_docs_state_explicit_absences() -> None:
    privacy_doc = PROJECT_ROOT / "docs" / "PRIVACY.md"
    text = privacy_doc.read_text(encoding="utf-8").lower()

    assert "no camera" in text
    assert "no mic" in text
    assert "no microphone" in text
    assert "no biometric id" in text
    assert "no face recognition" in text
    assert "no silhouettes" in text
    assert "no raw point cloud export" in text


def test_required_docs_exist() -> None:
    for path in required_doc_files(PROJECT_ROOT):
        assert path.exists()
