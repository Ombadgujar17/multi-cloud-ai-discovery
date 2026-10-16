# ☁️ Multi-Cloud AI Discovery & Shadow AI Detection

An enterprise discovery crawler and governance auditing engine for identifying **Artificial Intelligence (AI) assets** and detecting **Shadow AI** across AWS, Azure, and Google Cloud Platform (GCP).

It discovers direct cloud AI services (Amazon Bedrock, Google Vertex AI, Azure Cognitive Services) and indirect AI integrations in serverless/compute hosts (AWS Lambda, Cloud Run, Azure App Services), cross-referencing findings against an approved register to flag unapproved or unlisted AI usage.

---

## ⚡ Key Highlights

- **Multi-Cloud Connectors**: Scans AWS (multi-region Lambda + Bedrock), Azure (Resource Graph KQL), and GCP (Cloud Asset Inventory).
- **Dual-Detection Engine**: Detects native cloud AI resources as well as indirect integrations (API key names like `OPENAI_API_KEY`, SDK imports, endpoint references).
- **Zero-Trust Security**: Operates strictly read-only and inspects metadata/variable *names* only—**secret values and tokens are never read or stored**.
- **Shadow AI Governance**: Automatically flags unapproved/unlisted AI resources as `potential_shadow_ai_review`.
- **Dual Interfaces**: Interactive Streamlit Web Dashboard + Scriptable CLI.

---

## 🚀 Quickstart & Setup

### 1. Installation

```bash
# Clone and enter directory
git clone https://github.com/Ombadgujar17/multi-cloud-ai-discovery.git
cd multi-cloud-ai-discovery

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🖥 How to Run

### Option A: Streamlit Web Dashboard (Recommended)

Run the interactive dashboard to trigger scans, view KPI cards, filter by risk, inspect resource details, and export reports:

```bash
streamlit run app/ui.py
```
*Access the UI at `http://localhost:8501`.*

---

### Option B: Command-Line Interface (CLI)

#### 1. Safe Mock Mode (No cloud credentials required)
Uses simulated resources to test the entire discovery and governance pipeline offline:

```bash
python -m src.main --mode mock
```

#### 2. Live AWS Scan
Performs multi-region discovery across all active AWS regions:

```bash
# Using default environment credentials
python -m src.main --mode aws --region us-east-1

# Using a named AWS CLI profile
python -m src.main --mode aws --region us-east-1 --profile <AWS_PROFILE>
```

#### 3. Live Multi-Cloud Scan (AWS + GCP / Azure)
```bash
# AWS + Google Cloud Platform
python -m src.main --mode aws --region us-east-1 --gcp-project-id <GCP_PROJECT_ID>

# AWS + Microsoft Azure
python -m src.main --mode aws --region us-east-1 --azure-subscription-id <AZURE_SUBSCRIPTION_ID>
```

---

## 🧪 Running Tests

All tests run 100% offline with zero cloud credentials needed:

```bash
# Run full test suite (unittest)
python -m unittest discover tests

# Run indirect detection unit tests
python -m tests.test_indirect_detection

# Run standalone detector smoke test
python test_detector.py
```

---

## 📊 Output Files

Every scan writes two output files:

- **`data/ai_inventory.csv`**: Comprehensive 22-column audit inventory (cloud provider, resource ID, owner, tags, detected AI providers, evidence type, confidence, approval status, shadow AI review flag).
- **`data/scan_report.json`**: Scan health report containing timestamps, connector coverage (scanned/failed regions), resource counts, warnings, and disclosures.

---

## 📂 Project Structure

```
multi-cloud-ai-discovery/
├── app/
│   └── ui.py                   # Streamlit interactive web dashboard
├── data/
│   ├── approved_ai_inventory.csv # Approved enterprise baseline register
│   ├── ai_inventory.csv        # Output CSV inventory
│   └── scan_report.json        # Output scan coverage report
├── src/
│   ├── main.py                 # CLI entrypoint & orchestrator pipeline
│   ├── connectors/
│   │   ├── aws/                # AWS Lambda & Bedrock discovery
│   │   ├── azure/              # Azure Resource Graph KQL discovery
│   │   └── gcp/                # GCP Cloud Asset Inventory discovery
│   ├── detectors/
│   │   ├── ai_signals.py       # Heuristic pattern & endpoint detection
│   │   └── approval_checker.py # Inventory reconciliation & Shadow AI classifier
│   └── exporters/
│       └── csv_exporter.py     # 22-column CSV inventory exporter
├── tests/
│   ├── test_indirect_detection.py # Unit tests for indirect signals
│   └── test_pipeline.py        # Integration tests
└── requirements.txt            # Dependencies
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
