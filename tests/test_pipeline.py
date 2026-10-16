
import csv
import tempfile
import unittest
from pathlib import Path

from src.connectors.aws.discovery import (
    get_mock_lambda_functions,
    get_mock_bedrock_resources,
    get_mock_indirect_integration,
)
from src.detectors.ai_signals import detect_ai_signals
from src.detectors.approval_checker import (
    check_approval,
    load_approved_inventory,
)
from src.main import build_inventory
from src.exporters.csv_exporter import export_inventory


class DiscoveryPipelineTests(unittest.TestCase):

    def setUp(self):
        self.resources = (
            get_mock_lambda_functions()
            + get_mock_bedrock_resources()
            + [get_mock_indirect_integration()]
        )

    def test_mock_resource_count(self):
        self.assertEqual(len(self.resources), 5)

    def test_openai_integration_is_detected(self):
        resource = get_mock_indirect_integration()
        findings = detect_ai_signals(resource)

        self.assertTrue(
            any(item["provider"] == "OpenAI" for item in findings)
        )

    def test_approved_bedrock_resource(self):
        approvals = {
            "MOCK-LAMBDA-003": {
                "approval_status": "approved",
                "owner": "Platform Team",
            }
        }

        result = check_approval(
            {
                "resource_id": "MOCK-LAMBDA-003",
                "ai_detected": True,
            },
            approvals,
        )

        self.assertEqual(result["approval_status"], "approved")
        self.assertEqual(result["shadow_ai_status"], "approved")

    def test_unlisted_ai_resource_requires_review(self):
        result = check_approval(
            {
                "resource_id": "MOCK-UNLISTED",
                "ai_detected": True,
            },
            {},
        )

        self.assertEqual(
            result["shadow_ai_status"],
            "potential_shadow_ai_review",
        )

    def test_inventory_csv_has_all_rows(self):
        inventory = build_inventory(self.resources, {})

        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "inventory.csv")
            export_inventory(inventory, path)

            with open(path, newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 5)
        self.assertIn("account_id", rows[0])
        self.assertIn("evidence_scope", rows[0])
        self.assertIn("runtime_invocation_status", rows[0])

    def test_csv_preserves_execution_role_arn(self):
        resource = {
            "provider": "AWS",
            "resource_type": "Lambda",
            "resource_id": "arn:aws:lambda:ap-south-1:123456789012:function:demo",
            "execution_role_arn": (
                "arn:aws:iam::123456789012:role/demo-execution-role"
            ),
            "name": "demo",
            "description": "Test Lambda",
            "discovery_mode": "mock",
        }

        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "inventory.csv")
            export_inventory([resource], path)

            with open(path, newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["execution_role_arn"],
            "arn:aws:iam::123456789012:role/demo-execution-role",
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)

