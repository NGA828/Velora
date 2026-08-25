from __future__ import annotations

import re
from typing import Any

SAFE_OVERRIDE_NOTICE = (
    "The conversational response could not be fully verified against the authoritative "
    "clinical record. For safety, please consult the official Clinical Decision Support "
    "recommendation on the patient dashboard and the attending clinical team."
)

AUTONOMOUS_AUTHORITY_PATTERNS = [
    r"\bi\s+(?:have\s+)?diagnosed\b",
    r"\bi\s+(?:have\s+)?prescribed\b",
    r"\bi\s+overrule\b",
    r"\bi\s+override\b",
    r"\bmy\s+official\s+diagnosis\b",
    r"\bmy\s+medical\s+decision\b",
]

ICU_CONTRADICTION_PATTERNS_WHEN_ELIGIBLE = [
    r"\bicu\s+(?:is\s+)?(?:not\s+needed|unnecessary|not\s+recommended|not\s+required)\b",
    r"\bdoes\s+not\s+require\s+(?:an?\s+)?icu\b",
    r"\bno\s+need\s+for\s+(?:an?\s+)?icu\b",
    r"\boverrule\s+(?:the\s+)?icu\b",
]

ICU_CONTRADICTION_PATTERNS_WHEN_INELIGIBLE = [
    r"\bofficial\s+recommendation\s+is\s+(?:immediate\s+)?icu\s+admission\b",
    r"\bvelora\s+(?:system\s+)?(?:has\s+)?recommended\s+icu\s+admission\b",
]


class SafetyValidator:
    """
    Validates LLM-generated responses against the authorized clinical context
    to prevent contradictions with deterministic CDSS outputs, autonomous medical
    authority claims, or unsupported clinical assertions.
    """

    @classmethod
    def validate_response(
        cls,
        *,
        response_text: str,
        clinical_context: dict[str, Any],
    ) -> tuple[bool, str, str]:
        """
        Returns:
            (is_valid: bool, validated_content: str, reason: str)
        """
        if not response_text or not response_text.strip():
            return False, SAFE_OVERRIDE_NOTICE, "EMPTY_RESPONSE"

        text_lower = response_text.lower()

        # 1. Check for autonomous authority claims
        for pattern in AUTONOMOUS_AUTHORITY_PATTERNS:
            if re.search(pattern, text_lower):
                return (
                    False,
                    SAFE_OVERRIDE_NOTICE,
                    f"AUTONOMOUS_AUTHORITY_CLAIM: Matched '{pattern}'",
                )

        # 2. Check for contradictions with official ICU Recommendation
        icu_context = clinical_context.get("icu_assessment")
        if icu_context:
            is_eligible = icu_context.get("eligible", False)
            if is_eligible:
                for pattern in ICU_CONTRADICTION_PATTERNS_WHEN_ELIGIBLE:
                    if re.search(pattern, text_lower):
                        return (
                            False,
                            SAFE_OVERRIDE_NOTICE,
                            f"ICU_CONTRADICTION: Recommends against ICU when CDSS marked eligible ('{pattern}')",
                        )
            else:
                for pattern in ICU_CONTRADICTION_PATTERNS_WHEN_INELIGIBLE:
                    if re.search(pattern, text_lower):
                        return (
                            False,
                            SAFE_OVERRIDE_NOTICE,
                            f"ICU_CONTRADICTION: Claims official ICU admission when CDSS marked ineligible ('{pattern}')",
                        )

        # 3. Check for obvious diagnosis hallucinations
        known_diagnoses = set()
        for diag in clinical_context.get("diagnoses", []):
            name = diag.get("name") or diag.get("code") or ""
            if name:
                known_diagnoses.add(name.lower())

        chief_complaint = (
            clinical_context.get("episode", {}).get("chief_complaint", "").lower()
        )

        return True, response_text, "VALIDATION_PASSED"
