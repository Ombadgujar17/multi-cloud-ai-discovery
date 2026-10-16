from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError



def discover_lambda_functions(
    region: str,
    profile_name: str | None = None,
) -> list[dict[str, Any]]:
    """Discover Lambda configuration without retrieving secret values."""
    session_args: dict[str, str] = {"region_name": region}

    if profile_name:
        session_args["profile_name"] = profile_name

    session = boto3.Session(**session_args)
    client = session.client("lambda")
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]

    resources: list[dict[str, Any]] = []
    paginator = client.get_paginator("list_functions")

    for page in paginator.paginate():
        for function in page.get("Functions", []):
            function_arn = function["FunctionArn"]
            execution_role_arn = function.get("Role", "")

            # Retrieve only environment-variable names.
            config = client.get_function_configuration(
                FunctionName=function["FunctionName"]
            )
            environment_names = list(
                config.get("Environment", {})
                .get("Variables", {})
                .keys()
            )

            # Tags may identify a business owner or application team.
            try:
                tag_response = client.list_tags(
                    Resource=function_arn
                )
                tags = tag_response.get("Tags", {})
            except (ClientError, BotoCoreError):
                tags = {}

            owner = (
                tags.get("Owner")
                or tags.get("owner")
                or tags.get("Team")
                or tags.get("team")
                or "unknown"
            )

            resources.append({
                "provider": "AWS",
                "account_id": account_id,
                "resource_type": "Lambda",
                "resource_id": function_arn,
                "name": function["FunctionName"],
                "description": function.get("Description", ""),
                "runtime": function.get("Runtime", "unknown"),
                "region": region,
                "last_modified": function.get("LastModified", ""),
                "owner": owner,
                "tags": tags,
                "environment_variable_names": environment_names,
                "code_indicators": [],
                "service_references": [],
                "discovery_mode": "live",
                "execution_role_arn": execution_role_arn,
            })

    return resources


def get_mock_lambda_functions() -> list[dict[str, Any]]:
    """Return clearly labelled sample resources for offline testing."""
    return [
        {
            "provider": "AWS",
            "resource_type": "Lambda",
            "resource_id": "MOCK-LAMBDA-001",
            "name": "customer-summary-function",
            "description": "Summarizes customer feedback",
            "runtime": "python3.12",
            "region": "ap-south-1",
            "last_modified": "unknown",
            "environment_variable_names": ["OPENAI_API_KEY", "LOG_LEVEL"],
            "code_indicators": ["from openai import OpenAI"],
            "service_references": [],
            "discovery_mode": "mock",
        },
        {
            "provider": "AWS",
            "resource_type": "Lambda",
            "resource_id": "MOCK-LAMBDA-002",
            "name": "image-processing-function",
            "description": "Processes uploaded images",
            "runtime": "python3.12",
            "region": "ap-south-1",
            "last_modified": "unknown",
            "environment_variable_names": ["LOG_LEVEL"],
            "code_indicators": [],
            "service_references": [],
            "discovery_mode": "mock",
        },
        {
            "provider": "AWS",
            "resource_type": "Lambda",
            "resource_id": "MOCK-LAMBDA-003",
            "name": "bedrock-document-assistant",
            "description": "Document assistant using Amazon Bedrock",
            "runtime": "python3.12",
            "region": "ap-south-1",
            "last_modified": "unknown",
            "environment_variable_names": [],
            "code_indicators": [],
            "service_references": ["bedrock-runtime"],
            "discovery_mode": "mock",
        },
    ]

def get_mock_bedrock_resources() -> list[dict[str, Any]]:
    """Clearly labelled sample Bedrock resource for offline testing."""
    return [
        {
            "provider": "AWS",
            "resource_type": "Bedrock Agent",
            "resource_id": "MOCK-BEDROCK-AGENT-001",
            "name": "support-assistant-agent",
            "description": "Sample customer-support agent",
            "runtime": "",
            "region": "ap-south-1",
            "last_modified": "unknown",
            "environment_variable_names": [],
            "code_indicators": [],
            "service_references": [
                "Amazon Bedrock",
                "Bedrock Agent",
            ],
            "discovery_mode": "mock",
        }
    ]

def get_mock_indirect_integration() -> dict[str, Any]:
    """Simulated Lambda with evidence of an external AI integration."""
    return {
        "provider": "AWS",
        "resource_type": "Lambda",
        "resource_id": "MOCK-LAMBDA-004",
        "name": "external-ai-summary",
        "description": "Summarizes documents using an external API",
        "runtime": "python3.12",
        "region": "ap-south-1",
        "last_modified": "unknown",
        "environment_variable_names": [
            "OPENAI_API_KEY",
            "LOG_LEVEL",
        ],
        "code_indicators": [
            "from openai import OpenAI",
            "https://api.openai.com/v1",
        ],
        "service_references": [],
        "discovery_mode": "mock",
    }