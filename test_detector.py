from src.detectors.ai_signals import detect_ai_signals


resource = {
    "name": "customer-summary-function",
    "description": "Summarizes customer feedback",
    "runtime": "python3.12",
    "environment_variable_names": [
        "OPENAI_API_KEY",
        "LOG_LEVEL",
    ],
    "code_indicators": [
        "from openai import OpenAI",
    ],
}

findings = detect_ai_signals(resource)

for finding in findings:
    print(finding)

assert any(
    finding["provider"] == "OpenAI"
    for finding in findings
), "Expected OpenAI signal was not detected"

print("Detector test passed!")
