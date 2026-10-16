# Multi-Cloud AI Discovery and Shadow AI Detection

## Overview

A Python prototype for discovering AI-related cloud resources and
identifying resources that may require an AI governance review.

The prototype combines cloud resource metadata, AI-provider signals,
an approval register, a CSV inventory, and a JSON scan coverage report.

## Current implementation

- AWS Lambda discovery using boto3.
- AWS Bedrock resource discovery for custom models, provisioned
  throughput, guardrails, agents, and knowledge bases.
- Heuristic detection of provider endpoints, SDK/configuration clues,
  and AI-related cloud resources.
- Comparison against an approved AI inventory.
- CSV inventory and JSON scan report.
- Mock mode for offline testing.
- Azure and GCP connector interfaces, not live discovery.

## Requirements

- Python 3.11 or later
- boto3
- python-dotenv

Install dependencies in a virtual environment:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install boto3 python-dotenv

## Run the mock demonstration

    python -m src.main --mode mock

Outputs:

- data/ai_inventory.csv
- data/scan_report.json

The mock dataset contains five simulated resources. These are fixtures,
not findings from a real cloud account.

## Run tests

    python -m tests.test_pipeline
    python -m tests.test_indirect_detection

## Attempt a live AWS scan

Configure an authorized AWS CLI profile or environment credentials
using your organization's approved process.

Then run:

    python -m src.main --mode aws --region ap-south-1

For a named AWS profile:

    python -m src.main --mode aws --region ap-south-1 --profile PROFILE_NAME

The AWS identity needs appropriate read-only permissions for the
discovery operations. Access failures or unsupported operations may
result in incomplete coverage; inspect data/scan_report.json.

## Outputs and interpretation

The CSV records resource metadata, AI signals, evidence categories,
confidence labels, approval status, and review status.

The JSON report records scan mode, connector coverage, counts,
warnings, and known limitations.

A provider endpoint, SDK import, or AI-related resource is a signal;
it does not by itself prove runtime model invocation.

An AI resource absent from the approval register is flagged for review.
It is not automatically proven unauthorized.

## Security

- Do not commit credentials or API keys.
- The Lambda collector records environment-variable names, not values.
- The current prototype does not download Lambda source code.
- Use least-privilege, read-only access for live discovery.

## Known limitations

- Live AWS discovery has not yet been validated against an AWS account.
- Azure and GCP live discovery are not implemented.
- Runtime invocation and usage frequency are not currently measured.
- Indirect integration detection is heuristic and can produce false
  positives or false negatives.
- Owner tags and resource metadata may be missing.
- The approval register is a simplified demo inventory.

## Next steps

1. Validate AWS discovery in an authorized test account.
2. Improve scan coverage and permission reporting.
3. Add stronger, safe evidence collection for indirect integrations.
4. Implement Azure Resource Graph and GCP Cloud Asset Inventory
   discovery.
5. Add runtime usage evidence where authorized logs are available.
6. Expand automated tests and document the required permissions.
