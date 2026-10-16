
from google.cloud import asset_v1
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import GoogleAPICallError, PermissionDenied


AI_RESOURCE_TYPES = {
    "aiplatform.googleapis.com/Endpoint": "Vertex AI Endpoint",
    "aiplatform.googleapis.com/Model": "Vertex AI Model",
    "aiplatform.googleapis.com/CustomJob": "Vertex AI Custom Job",
    "cloudfunctions.googleapis.com/CloudFunction": "Cloud Function",
    "run.googleapis.com/Service": "Cloud Run Service",
}


def discover_gcp_resources(project_id=None):
    """Discover selected GCP resource types using Cloud Asset Inventory."""
    if not project_id:
        return [], "not_configured", [
            "GCP project ID is required for live discovery."
        ]

    resources = []
    warnings = []

    try:
        client = asset_v1.AssetServiceClient()
        scope = f"projects/{project_id}"

        request = asset_v1.SearchAllResourcesRequest(
            scope=scope,
            asset_types=list(AI_RESOURCE_TYPES.keys()),
            page_size=100,
        )

        for asset in client.search_all_resources(request=request):
            resource_type = asset.asset_type
            display_type = AI_RESOURCE_TYPES.get(
                resource_type, resource_type
            )

            labels = dict(asset.labels) if asset.labels else {}
            name_parts = asset.name.rstrip("/").split("/")
            resource_name = name_parts[-1] if name_parts else asset.name

            resources.append({
                "provider": "GCP",
                "account_id": project_id,
                "resource_type": display_type,
                "resource_id": asset.name,
                "name": resource_name,
                "description": "",
                "owner": labels.get("owner", ""),
                "tags": labels,
                "runtime": "",
                "region": asset.location or "",
                "last_modified": "",
                "discovery_mode": "live",
                "resource_role": "ai_service_candidate",
                "service_refs": [resource_type],
            })

        return resources, "connected", warnings

    except DefaultCredentialsError:
        return [], "not_authenticated", [
            "GCP Application Default Credentials are unavailable."
        ]
    except PermissionDenied:
        return [], "permission_denied", [
            "GCP access denied. Check Cloud Asset Viewer permissions."
        ]
    except GoogleAPICallError as exc:
        return [], "error", [
            f"GCP Cloud Asset Inventory API error: {exc}"
        ]
    except Exception as exc:
        return [], "error", [
            f"GCP discovery failed: {type(exc).__name__}: {exc}"
        ]
