from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def discover_bedrock_resources(
    region: str,
    profile_name: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Discover configured Bedrock resources using read-only APIs."""
    session_args: dict[str, str] = {"region_name": region}

    if profile_name:
        session_args["profile_name"] = profile_name

    session = boto3.Session(**session_args)
    bedrock = session.client("bedrock")
    bedrock_agent = session.client("bedrock-agent")

    resources: list[dict[str, Any]] = []
    warnings: list[str] = []

    operations = [
        (
            bedrock,
            "list_custom_models",
            "modelSummaries",
            "Bedrock Custom Model",
            "modelName",
            "modelArn",
        ),
        (
            bedrock,
            "list_provisioned_model_throughputs",
            "provisionedModelSummaries",
            "Bedrock Provisioned Throughput",
            "provisionedModelName",
            "provisionedModelArn",
        ),
        (
            bedrock,
            "list_guardrails",
            "guardrails",
            "Bedrock Guardrail",
            "name",
            "id",
        ),
        (
            bedrock_agent,
            "list_agents",
            "agentSummaries",
            "Bedrock Agent",
            "agentName",
            "agentId",
        ),
        (
            bedrock_agent,
            "list_knowledge_bases",
            "knowledgeBaseSummaries",
            "Bedrock Knowledge Base",
            "name",
            "knowledgeBaseId",
        ),
    ]

    for client, operation, response_key, resource_type, name_key, id_key in operations:
        try:
            paginator = client.get_paginator(operation)

            for page in paginator.paginate():
                for item in page.get(response_key, []):
                    resource_id = item.get(id_key, "")
                    name = item.get(name_key, resource_id)

                    resources.append({
                        "provider": "AWS",
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "name": name,
                        "description": item.get("description", ""),
                        "runtime": "",
                        "region": region,
                        "last_modified": str(
                            item.get("lastModifiedTime", "")
                        ),
                        "account_id": "",
                        "owner": "unknown",
                        "tags": {},
                        "environment_variable_names": [],
                        "code_indicators": [],
                        "service_references": [
                            "Amazon Bedrock",
                            resource_type,
                        ],
                        "discovery_mode": "live",
                    })

        except (ClientError, BotoCoreError) as exc:
            warnings.append(
                f"{operation} failed: {type(exc).__name__}: {exc}"
            )
        except (AttributeError, ValueError) as exc:
            warnings.append(
                f"{operation} is unavailable: {type(exc).__name__}: {exc}"
            )

    return resources, warnings
