import csv
from pathlib import Path
from typing import Any


COLUMNS = [
    "provider",
    "account_id",
    "resource_type",
    "resource_id",
    "execution_role_arn",
    "name",
    "description",
    "owner",
    "tags",
    "runtime",
    "region",
    "last_modified",
    "discovery_mode",
    "ai_detected",
    "ai_providers",
    "evidence",
    "evidence_scope",
    "runtime_invocation_status",
    "confidence",
    "approval_status",
    "approval_evidence",
    "shadow_ai_status",
]


def export_inventory(
    rows: list[dict[str, Any]],
    output_path: str = "data/ai_inventory.csv",
) -> str:
    """Export resource and AI-discovery findings to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return str(path)
