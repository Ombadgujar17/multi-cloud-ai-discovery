import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import boto3

from src.connectors.aws.discovery import (
    discover_lambda_functions,
    get_mock_lambda_functions,
    get_mock_bedrock_resources,
    get_mock_indirect_integration,
)
from src.connectors.azure.discovery import discover_azure_resources
from src.connectors.gcp.discovery import discover_gcp_resources

from botocore.exceptions import BotoCoreError, ClientError

from src.connectors.aws.discovery import (
    discover_lambda_functions,
    get_mock_lambda_functions,
    get_mock_bedrock_resources,
)
from src.connectors.aws.bedrock_discovery import (
    discover_bedrock_resources,
)
from src.detectors.ai_signals import detect_ai_signals
from src.detectors.approval_checker import (
    check_approval,
    load_approved_inventory,
)
from src.exporters.csv_exporter import export_inventory


def build_inventory(
    resources: list[dict[str, Any]],
    approved_inventory: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    inventory = []

    for resource in resources:
        findings = detect_ai_signals(resource)
        providers = sorted({f["provider"] for f in findings})
        evidence = sorted({f["evidence"] for f in findings})

        confidence = (
            "medium"
            if any(f["confidence"] == "medium" for f in findings)
            else "low" if findings else "none"
        )

        row = {
            **{
                key: resource.get(key, "")
                for key in [
                    "provider",
                    "account_id",
                    "owner",
                    "tags",
                    "resource_type",
                    "resource_id",
                    "name",
                    "description",
                    "runtime",
                    "region",
                    "last_modified",
                    "discovery_mode",
                ]
            },
            "ai_detected": bool(findings),
            "ai_providers": "; ".join(providers),
            "evidence": "; ".join(evidence),
            "evidence_scope": (
                "resource_discovery"
                if "cloud_ai_resource_discovered" in evidence
                else "provider_endpoint_reference"
                if "provider_endpoint_reference" in evidence
                else "configuration_or_code_reference"
                if "configuration_or_code_reference" in evidence
                else "no_signal_detected"
            ),
            "runtime_invocation_status": "not_checked",
            "confidence": confidence,
        }

        row.update(check_approval(row, approved_inventory))
        inventory.append(row)

    return inventory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-cloud AI discovery crawler"
    )
    parser.add_argument(
        "--mode", choices=["mock", "aws"], default="mock"
    )
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--profile", default=None)
    parser.add_argument(
        "--output", default="data/ai_inventory.csv"
    )
    parser.add_argument(
        "--approvals",
        default="data/approved_ai_inventory.csv",
    )
    parser.add_argument(
        "--report", default="data/scan_report.json"
    )

    parser.add_argument(
    "--azure-subscription-id",
    default=None,
    help="Optional Azure subscription ID for live discovery",
    )

    parser.add_argument(
    "--gcp-project-id",
    default=None,
    help="Optional GCP project ID for live discovery",
    )
    args = parser.parse_args()

    warnings: list[str] = []
    connector_status: dict[str, str] = {}

    if args.mode == "mock":
        resources = (
        get_mock_lambda_functions()
        + get_mock_bedrock_resources()
        + [get_mock_indirect_integration()]
        )
        connector_status = {
            "aws_lambda": "simulated",
            "aws_bedrock": "simulated",
            "azure": "not_scanned",
            "gcp": "not_scanned",
        }
    else:
        resources = []

        try:
            session_args = {}
            if args.profile:
                session_args["profile_name"] = args.profile

            aws_session = boto3.Session(**session_args)
            ec2_client = aws_session.client("ec2", region_name=args.region)

            available_regions = [
                item["RegionName"]
                for item in ec2_client.describe_regions(
                    AllRegions=False
                ).get("Regions", [])
            ]

            scanned_regions = []
            failed_regions = []

            for region in available_regions:
                try:
                    lambda_resources = discover_lambda_functions(
                        region=region,
                        profile_name=args.profile,
                    )
                    resources.extend(lambda_resources)
                    scanned_regions.append(region)
                except Exception as exc:
                    failed_regions.append(region)
                    warnings.append(
                        f"AWS Lambda discovery failed in {region}: "
                        f"{type(exc).__name__}: {exc}"
                    )

            connector_status["aws_lambda"] = (
                "partial" if failed_regions
                else "completed"
            )
            connector_status["aws_lambda_regions_scanned"] = scanned_regions
            connector_status["aws_lambda_regions_failed"] = failed_regions

        except Exception as exc:
            connector_status["aws_lambda"] = "failed"
            warnings.append(
                f"AWS Lambda region discovery failed: "
                f"{type(exc).__name__}: {exc}"
            )

        try:
            bedrock_resources, bedrock_warnings = (
                discover_bedrock_resources(
                    region=args.region,
                    profile_name=args.profile,
                )
            )
            resources.extend(bedrock_resources)
            warnings.extend(bedrock_warnings)

            connector_status["aws_bedrock"] = (
                "partial" if bedrock_warnings else "completed"
            )
        except Exception as exc:
            connector_status["aws_bedrock"] = "failed"
            warnings.append(
                f"AWS Bedrock discovery failed: "
                f"{type(exc).__name__}: {exc}"
            )

        if args.azure_subscription_id:
            azure_resources, azure_status, azure_warnings = (
                discover_azure_resources(args.azure_subscription_id)
            )
            resources.extend(azure_resources)
            connector_status["azure"] = azure_status
            warnings.extend(azure_warnings)
        else:
            connector_status["azure"] = "not_configured"

        if args.gcp_project_id:
            gcp_resources, gcp_status, gcp_warnings = (
                discover_gcp_resources(args.gcp_project_id)
            )
            resources.extend(gcp_resources)
            connector_status["gcp"] = gcp_status
            warnings.extend(gcp_warnings)
        else:
            connector_status["gcp"] = "not_configured"

    approvals = load_approved_inventory(args.approvals)
    inventory = build_inventory(resources, approvals)
    output_path = export_inventory(inventory, args.output)

    report = {
        "scan_timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "mode": args.mode,
        "region": args.region,
        "coverage": connector_status,
        "resources_discovered": len(resources),
        "resources_with_ai_signals": sum(
            row["ai_detected"] for row in inventory
        ),
        "potential_shadow_ai_reviews": sum(
            row["shadow_ai_status"]
            == "potential_shadow_ai_review"
            for row in inventory
        ),
        "warnings": warnings,
        "inventory_csv": output_path,
        "limitations": [
            "AI signals do not prove runtime model invocation.",
            "An absent approval record does not prove unauthorized usage.",
            "Azure and GCP are not scanned by this version.",
            "Mock mode contains simulated resources, not live findings.",
        ],
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"Resources discovered: {len(resources)}")
    print(
        "Resources with AI signals:",
        report["resources_with_ai_signals"],
    )
    print(
        "Potential Shadow AI reviews:",
        report["potential_shadow_ai_reviews"],
    )
    print(f"CSV written to: {output_path}")
    print(f"Scan report written to: {report_path}")
    print(f"Discovery mode: {args.mode}")

    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warning in warnings:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()
