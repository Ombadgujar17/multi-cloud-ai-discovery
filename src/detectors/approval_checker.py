
import csv
from pathlib import Path
from typing import Any


def load_approved_inventory(
    path: str = "data/approved_ai_inventory.csv",
) -> dict[str, dict[str, str]]:
    """Load approved-resource records indexed by resource ID."""
    file_path = Path(path)

    if not file_path.exists():
        return {}

    with file_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        rows = csv.DictReader(file)
        return {
            row["resource_id"]: row
            for row in rows
            if row.get("resource_id")
        }


def check_approval(
    resource: dict[str, Any],
    approved_inventory: dict[str, dict[str, str]],
) -> dict[str, str]:
    """Compare a detected resource against approval records.

    Explicit unapproved labels trigger a review classification.
    This classification does not prove actual AI usage.
    """
    if not resource.get("ai_detected"):
        return {
            "approval_status": "not_applicable",
            "shadow_ai_status": "no_ai_signal_detected",
            "owner": resource.get("owner") or "unknown",
            "approval_evidence": "no_ai_signal_detected",
        }

    resource_id = resource.get("resource_id", "")
    record = approved_inventory.get(resource_id)

    # Inspect explicit resource labels before the register lookup.
    tags = resource.get("tags", {})

    if isinstance(tags, dict):
        declared_approval = str(
            tags.get("ai-approval", "")
        ).strip().lower()

        if declared_approval in {
            "unapproved",
            "unapproved-demo",
            "denied",
            "revoked",
        }:
            return {
                "approval_status": "denied",
                "shadow_ai_status": (
                    "potential_unapproved_usage_review"
                ),
                "owner": resource.get("owner") or "unknown",
                "approval_evidence": (
                    "resource_label_declares_unapproved"
                ),
            }

    if not record:
        return {
            "approval_status": "not_listed",
            "shadow_ai_status": "potential_shadow_ai_review",
            "owner": resource.get("owner") or "unknown",
            "approval_evidence": "no_matching_approval_record",
        }

    status = record.get(
        "approval_status",
        "unknown",
    ).strip().lower()

    if status == "approved":
        shadow_status = "approved"
    elif status in {"denied", "revoked"}:
        shadow_status = "potential_unapproved_usage_review"
    else:
        shadow_status = "approval_status_unknown"

    return {
        "approval_status": status,
        "shadow_ai_status": shadow_status,
        "owner": record.get("owner") or resource.get("owner") or "unknown",
        "approval_evidence": "matching_inventory_record",
    }
