from src.connectors.aws.discovery import get_mock_indirect_integration
from src.detectors.ai_signals import detect_ai_signals


def test_external_openai_integration_is_detected():
    resource = get_mock_indirect_integration()
    findings = detect_ai_signals(resource)

    openai_finding = next(
        item for item in findings
        if item["provider"] == "OpenAI"
    )

    assert openai_finding["evidence"] == "provider_endpoint_reference"
    assert openai_finding["confidence"] == "medium"


def test_openai_environment_variable_name_is_detected():
    resource = {
        "resource_type": "Lambda",
        "name": "document-processor",
        "environment_variable_names": ["OPENAI_API_KEY"],
    }

    findings = detect_ai_signals(resource)

    assert any(
        item["provider"] == "OpenAI"
        and item["evidence"] == "configuration_or_code_reference"
        for item in findings
    )


def test_generic_execution_role_does_not_trigger_ai_finding():
    resource = {
        "resource_type": "Lambda",
        "name": "ordinary-function",
        "execution_role_arn": (
            "arn:aws:iam::123456789012:role/lambda-execution-role"
        ),
    }

    findings = detect_ai_signals(resource)

    assert findings == []


def test_bedrock_resource_is_distinguished_from_integration_clue():
    resource = {
        "resource_type": "Bedrock Agent",
        "name": "support-agent",
        "service_references": ["Bedrock Agent"],
    }

    findings = detect_ai_signals(resource)

    bedrock_finding = next(
        item for item in findings
        if item["provider"] == "Amazon Bedrock"
    )

    assert bedrock_finding["evidence"] == "cloud_ai_resource_discovered"
    assert bedrock_finding["confidence"] == "medium"


if __name__ == "__main__":
    test_external_openai_integration_is_detected()
    test_openai_environment_variable_name_is_detected()
    test_generic_execution_role_does_not_trigger_ai_finding()
    test_bedrock_resource_is_distinguished_from_integration_clue()
    print("All indirect integration detection tests passed!")