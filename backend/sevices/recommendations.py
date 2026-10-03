"""Deterministic educational guidance, independent of prediction and SHAP.

Rules apply only to validated recorded measurements. They are deliberately
conservative: cards prompt report review and discussion, never diagnosis,
treatment, medication, testing, or exercise instructions.
"""
from __future__ import annotations

from typing import Any

RULE_VERSION = "guidance-2026-09-09-v1"


def _card(title: str, explanation: str, next_step: str, rule: str) -> dict[str, str]:
    return {
        "title": title,
        "explanation": explanation,
        "next_step": next_step,
        "rule": rule,
    }


def generate_recommendations(measurements: dict[str, Any]) -> list[dict[str, str]]:
    """Return at most three saved, non-treatment educational guidance cards.

    The order is deterministic. Neither risk band nor SHAP values participate,
    so a contribution's sign never becomes clinical advice.
    """
    cards = [
        _card(
            "Review your report",
            "Bring the recorded measurements and this educational assessment to a healthcare professional.",
            "Discuss any questions about the report in the context of your own health history.",
            "always_review_report",
        )
    ]
    systolic = float(measurements["trestbps"])
    cholesterol = float(measurements["chol"])

    # The form has only the systolic component. It cannot diagnose hypertension.
    if systolic >= 130:
        cards.append(_card(
            "Discuss your blood pressure",
            f"The recorded resting blood pressure was {systolic:g} mm Hg. This is one recorded upper-number measurement, not a diagnosis.",
            "Ask a healthcare professional to review this reading with the rest of your blood-pressure information.",
            "systolic_bp_at_least_130_mm_hg",
        ))

    # Cleveland supplies one serum-cholesterol field, not a full lipid panel.
    if cholesterol >= 200 and len(cards) < 3:
        cards.append(_card(
            "Discuss your cholesterol results",
            f"The recorded serum cholesterol was {cholesterol:g} mg/dL. This assessment does not include a complete lipid-panel interpretation.",
            "Ask a healthcare professional to review the recorded result alongside the full report.",
            "serum_cholesterol_at_least_200_mg_dl",
        ))

    # This binary dataset feature is explicitly not used as a diabetes assessment.
    if measurements.get("fbs") == 1 and len(cards) < 3:
        cards.append(_card(
            "Review the blood sugar entry",
            "The form records that fasting blood sugar was above 120 mg/dL. This dataset flag is not a diabetes assessment.",
            "Confirm the recorded value in the report and discuss questions with a healthcare professional.",
            "dataset_fasting_blood_sugar_flag",
        ))
    return cards
