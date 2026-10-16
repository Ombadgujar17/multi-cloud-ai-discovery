from typing import Any

from azure.core.exceptions import AzureError, ClientAuthenticationError
from azure.identity import DefaultAzureCredential, CredentialUnavailableError
from azure.mgmt.resourcegraph import ResourceGraphClient


AI_RESOURCE_QUERY = """
Resources
| where type in~ (
    'microsoft.cognitiveservices/accounts',
    'microsoft.machinelearningservices/workspaces',
    'microsoft.web/sites',
    'microsoft.app/containerapps',
    'microsoft.logic/workflows',
    'microsoft.search/searchservices'
)
| project id, name, type, location, subscriptionId,
          resourceGroup, tags, kind, sku
"""


def discover_azure_resources(
    subscription_id: str | None = None,
) -> tuple[list[dict[str, Any]], str, list[str]]:
    """Discover selected Azure AI services and possible host resources.

    Uses Azure Resource Graph metadata only. It does not inspect application
    source code, retrieve app-setting values, or prove runtime AI invocation.
    """
    if not subscription_id:
        return (
            [],
            "not_configured",
            ["Azure subscription ID is required for live discovery."],
        )

    try:
        credential = DefaultAzureCredential()
        client = ResourceGraphClient(credential=credential)

        response = client.resources(
            query={
                "query": AI_RESOURCE_QUERY,
                "subscriptions": [subscription_id],
                "options": {"resultFormat": "objectArray"},
            }
        )

        resources = []

        for item in response.data:
            resource_type = item.get("type", "")
            tags = item.get("tags") or {}
            kind = item.get("kind", "")

            # An app/site is a possible host, not proof of AI usage.
            is_possible_host = resource_type.lower() in {
                "microsoft.web/sites",
                "microsoft.app/containerapps",
                "microsoft.logic/workflows",
            }

            resources.append({
                "provider": "Azure",
                "account_id": subscription_id,
                "resource_type": resource_type,
                "resource_id": item.get("id", ""),
                "name": item.get("name", ""),
                "description": "",
                "runtime": kind,
                "region": item.get("location", ""),
                "last_modified": "unknown",
                "owner": (
                    tags.get("Owner")
                    or tags.get("owner")
                    or tags.get("Team")
                    or "unknown"
                ),
                "tags": tags,
                "environment_variable_names": [],
                "code_indicators": [],
                "service_references": [
                    "Azure Resource Graph",
                    resource_type,
                ],
                "discovery_mode": "live",
                "resource_role": (
                    "possible_ai_host"
                    if is_possible_host
                    else "ai_service_candidate"
                ),
            })

        return resources, "completed", []

    except CredentialUnavailableError as exc:
        return (
            [],
            "failed",
            [f"Azure credentials unavailable: {exc}"],
        )
    except AzureError as exc:
        return (
            [],
            "failed",
            [f"Azure Resource Graph request failed: {exc}"],
        )
    except Exception as exc:
        return (
            [],
            "failed",
            [f"Unexpected Azure discovery error: {type(exc).__name__}: {exc}"],
        )
