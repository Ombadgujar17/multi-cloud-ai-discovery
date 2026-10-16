
import re
from typing import Any


AI_PATTERNS = {
    "OpenAI": [
        r"api\.openai\.com",
        r"from\s+openai\s+import",
        r"import\s+openai",
        r"OPENAI_API_KEY",
        r"\bopenai\b",
    ],
    "Amazon Bedrock": [
        r"bedrock-runtime",
        r"bedrock-agent",
        r"bedrock",
    ],
    "Anthropic": [
        r"api\.anthropic\.com",
        r"ANTHROPIC_API_KEY",
        r"anthropic",
    ],
    "Google Gemini": [
        r"generativelanguage\.googleapis\.com",
        r"gemini",
        r"GOOGLE_API_KEY",
    ],
}

ENDPOINT_PATTERNS = {
    "OpenAI": r"api\.openai\.com",
    "Amazon Bedrock": r"bedrock-runtime",
    "Anthropic": r"api\.anthropic\.com",
    "Google Gemini": r"generativelanguage\.googleapis\.com",
}


def detect_ai_signals(
    resource: dict[str, Any],
) -> list[dict[str, str]]:
    """Detect AI resources and potential AI integration clues.

    This function identifies metadata/configuration signals.
    It does not establish actual runtime AI invocation.

    Secret values must never be passed into this function.
    """
    fields = [
        "name",
        "description",
        "resource_type",
        "environment_variable_names",
        "code_indicators",
        "service_references",
    ]

    parts: dict[str, str] = {}

    for field in fields:
        value = resource.get(field, "")

        if isinstance(value, (list, tuple, set)):
            parts[field] = "\n".join(str(item) for item in value)
        elif isinstance(value, dict):
            # Inspect keys only, never possible secret values.
            parts[field] = "\n".join(str(key) for key in value.keys())
        else:
            parts[field] = str(value or "")

    # Read explicit provider labels as additional evidence.
    tags = resource.get("tags", {})
    ai_provider_label = ""

    if isinstance(tags, dict):
        ai_provider_label = str(
            tags.get("ai-provider", "")
        ).strip()

    all_text = "\n".join(parts.values())
    findings: list[dict[str, str]] = []

    for provider, patterns in AI_PATTERNS.items():
        matched = [
            pattern
            for pattern in patterns
            if re.search(pattern, all_text, re.IGNORECASE)
        ]

        # An explicit ai-provider label is also a detection signal.
        label_matches_provider = (
            ai_provider_label.casefold() == provider.casefold()
        )

        if not matched and not label_matches_provider:
            continue

        resource_type = parts["resource_type"].lower()
        service_refs = parts["service_references"].lower()

        is_direct_bedrock_resource = (
            provider == "Amazon Bedrock"
            and (
                resource_type.startswith("bedrock ")
                or any(
                    marker in service_refs
                    for marker in [
                        "bedrock agent",
                        "bedrock knowledge base",
                        "bedrock guardrail",
                        "bedrock custom model",
                        "bedrock provisioned throughput",
                    ]
                )
            )
        )

        endpoint_pattern = ENDPOINT_PATTERNS.get(provider, "")
        endpoint_found = bool(
            endpoint_pattern
            and re.search(
                endpoint_pattern,
                all_text,
                re.IGNORECASE,
            )
        )

        if label_matches_provider:
            evidence = "ai_provider_label"
            confidence = "low"
        elif is_direct_bedrock_resource:
            evidence = "cloud_ai_resource_discovered"
            confidence = "medium"
        elif endpoint_found:
            evidence = "provider_endpoint_reference"
            confidence = "medium"
        else:
            evidence = "configuration_or_code_reference"
            confidence = "low"

        findings.append(
            {
                "provider": provider,
                "evidence": evidence,
                "confidence": confidence,
                "matched_signal_count": str(
                    len(matched) + int(label_matches_provider)
                ),
            }
        )

    return findings
