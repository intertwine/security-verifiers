from sv_env_config_verification.e2_config_auditing.schema import parse_model_output


def test_parse_model_output_valid() -> None:
    model_json = {
        "violations": [{"id": "a", "severity": "low"}],
        "patch": "",
        "confidence": 0.5,
    }
    violations, patch, conf = parse_model_output(model_json)
    assert violations[0].id == "a"
    assert patch == ""
    assert conf == 0.5
