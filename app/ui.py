import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

INVENTORY_PATH = DATA_DIR / "ui_inventory.csv"
REPORT_PATH = DATA_DIR / "ui_scan_report.json"

# Page configuration
st.set_page_config(
    page_title="Multi-Cloud AI Discovery",
    page_icon="☁️",
    layout="wide",
)

# Simple styling
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("☁️ Multi-Cloud AI Discovery")
st.caption(
    "Discover AI-related cloud resources, inspect evidence, "
    "and identify resources that may require Shadow AI review."
)

# Sidebar controls
st.sidebar.header("Discovery Controls")

scan_mode = st.sidebar.radio(
    "Scan mode",
    options=["Mock demonstration", "Live scan"],
    help="Mock mode uses sample resources. Live AWS mode uses your configured AWS credentials.",
)

aws_profile = "multicloud-discovery"
aws_region = "us-east-1"

if scan_mode == "Live scan":
    aws_profile = st.sidebar.text_input(
        "AWS profile",
        value="multicloud-discovery",
        help="Use your configured read-only AWS profile.",
    )
    aws_region = st.sidebar.text_input(
        "Bedrock scan region",
        value="us-east-1",
    )

gcp_project_id = st.sidebar.text_input(
    "GCP project ID",
    value="multi-cloud-511804",
    help="Project ID to scan using your Google Cloud credentials.",
)

scan_gcp = st.sidebar.checkbox(
    "Include Google Cloud scan",
    value=True,
)

st.sidebar.info(
    "Azure and GCP are reported as unconfigured unless their project/subscription "
    "IDs are supplied to the underlying CLI."
)

run_scan = st.sidebar.button(
    "Run discovery scan",
    type="primary",
    use_container_width=True,
)

if run_scan:
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--mode",
        "mock" if scan_mode == "Mock demonstration" else "aws",
        "--output",
        str(INVENTORY_PATH),
        "--report",
        str(REPORT_PATH),
    ]

    if scan_mode == "Live scan":
        if not aws_profile.strip():
            st.error("Enter your configured AWS profile name.")
            st.stop()

        command.extend(["--profile", aws_profile.strip()])

        if aws_region.strip():
            command.extend(["--region", aws_region.strip()])

    if scan_gcp:
        if not gcp_project_id.strip():
            st.error("Enter a GCP project ID.")
            st.stop()

        command.extend(["--gcp-project-id", gcp_project_id.strip()])

    with st.spinner("Running discovery scan..."):
        try:
            result = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )

            if result.returncode == 0 and INVENTORY_PATH.exists():
                st.session_state["inventory_path"] = str(INVENTORY_PATH)
                st.session_state["report_path"] = (
                    str(REPORT_PATH) if REPORT_PATH.exists() else None
                )
                st.session_state["scan_mode"] = scan_mode
                st.session_state["scan_stdout"] = result.stdout
                st.session_state["scan_stderr"] = result.stderr
                st.session_state["scan_error"] = None
            else:
                st.session_state["scan_error"] = (
                    result.stderr or result.stdout or "The scan failed."
                )

        except subprocess.TimeoutExpired:
            st.session_state["scan_error"] = (
                "The scan exceeded 10 minutes. Check cloud connectivity and permissions."
            )
        except Exception as exc:
            st.session_state["scan_error"] = str(exc)

if st.session_state.get("scan_error"):
    st.error("Discovery scan failed.")
    st.code(st.session_state["scan_error"])

# Load the most recent successful scan
inventory_file = st.session_state.get("inventory_path")
report_file = st.session_state.get("report_path")

if inventory_file and Path(inventory_file).exists():
    try:
        inventory = pd.read_csv(inventory_file).fillna("")
    except Exception as exc:
        st.error(f"Could not read the inventory CSV: {exc}")
        st.stop()

    report = {}
    if report_file and Path(report_file).exists():
        try:
            with open(report_file, "r", encoding="utf-8") as file:
                report = json.load(file)
        except (OSError, json.JSONDecodeError):
            report = {}

    st.divider()
    st.subheader("Latest Scan")
    st.caption(
        f"Mode: {st.session_state.get('scan_mode', 'Unknown')} "
        "· Results reflect the most recent successful scan."
    )

    # Calculate dashboard metrics from the inventory
    total_resources = len(inventory)

    if "ai_detected" in inventory.columns:
        ai_mask = (
            inventory["ai_detected"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["true", "1", "yes"])
        )
        ai_resources = int(ai_mask.sum())
    else:
        ai_mask = pd.Series(False, index=inventory.index)
        ai_resources = 0

    if "shadow_ai_status" in inventory.columns:
        shadow_mask = (
            inventory["shadow_ai_status"]
            .astype(str)
            .str.contains("potential_shadow_ai_review", case=False, na=False)
        )
        shadow_count = int(shadow_mask.sum())
    else:
        shadow_mask = pd.Series(False, index=inventory.index)
        shadow_count = 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Resources discovered", total_resources)
    col2.metric("AI-related signals", ai_resources)
    col3.metric("Potential Shadow AI reviews", shadow_count)
    col4.metric(
        "Other resources",
        max(total_resources - ai_resources, 0),
    )

    st.divider()

    # Inventory view
    st.subheader("Resource Inventory")

    filter_options = ["All resources", "AI-related signals", "Potential Shadow AI reviews"]
    selected_filter = st.selectbox("Filter inventory", filter_options)

    displayed = inventory.copy()

    if selected_filter == "AI-related signals":
        displayed = displayed.loc[ai_mask]
    elif selected_filter == "Potential Shadow AI reviews":
        displayed = displayed.loc[shadow_mask]

    preferred_columns = [
        "provider",
        "resource_type",
        "name",
        "region",
        "owner",
        "ai_detected",
        "ai_providers",
        "evidence",
        "confidence",
        "approval_status",
        "shadow_ai_status",
    ]
    visible_columns = [
        column for column in preferred_columns if column in displayed.columns
    ]

    st.dataframe(
        displayed[visible_columns] if visible_columns else displayed,
        use_container_width=True,
        hide_index=True,
    )

    # Resource details
    if not displayed.empty:
        st.subheader("Inspect a Resource")

        name_column = "name" if "name" in displayed.columns else displayed.columns[0]
        resource_names = displayed[name_column].astype(str).tolist()

        selected_name = st.selectbox(
            "Select a resource",
            resource_names,
        )

        selected_rows = displayed.loc[
            displayed[name_column].astype(str) == selected_name
        ]

        if not selected_rows.empty:
            selected_resource = selected_rows.iloc[0].to_dict()
            st.json(
                {
                    key: value
                    for key, value in selected_resource.items()
                    if value != ""
                }
            )

    # Download buttons
    st.subheader("Export Results")

    download_col1, download_col2 = st.columns(2)

    with download_col1:
        st.download_button(
            "⬇️ Download inventory CSV",
            data=inventory.to_csv(index=False).encode("utf-8"),
            file_name="ai_inventory.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with download_col2:
        st.download_button(
            "⬇️ Download scan report JSON",
            data=json.dumps(report, indent=2, ensure_ascii=False),
            file_name="scan_report.json",
            mime="application/json",
            use_container_width=True,
        )

    with st.expander("Scan coverage, warnings and limitations"):
        st.json(report if report else {"message": "No scan report was available."})

    with st.expander("CLI output"):
        st.text(st.session_state.get("scan_stdout", ""))
        if st.session_state.get("scan_stderr"):
            st.text(st.session_state["scan_stderr"])

else:
    st.info("Choose a scan mode in the sidebar and click **Run discovery scan**.")

    st.markdown("### What this dashboard demonstrates")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🔎 Resource discovery**")
        st.write("Collect metadata from supported cloud connectors.")

    with col2:
        st.markdown("**🧠 AI signal detection**")
        st.write("Identify direct AI resources and possible endpoint or configuration references.")

    with col3:
        st.markdown("**🛡️ Shadow AI review**")
        st.write("Flag resources that may need an approval check, with evidence and confidence.")