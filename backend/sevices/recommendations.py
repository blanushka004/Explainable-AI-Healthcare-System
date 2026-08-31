"""Adapt the established root recommendation engine for the API."""

from src.recommendation import generate_recommendations as _generate_recommendations


def generate_recommendations(data: dict, prediction: int, probability: float) -> list[dict]:
    """Return personalized, decision-support recommendations.

    The root ``src`` implementation remains the single recommendation engine;
    this service only converts the API prediction into its risk-level input.
    """

    if probability >= 0.70:
        risk_level = "HIGH"
    elif probability >= 0.30:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # A positive model classification warrants at least a clinical review even
    # when a calibrated probability lies below the early-warning threshold.
    if prediction == 1 and risk_level == "LOW":
        risk_level = "MEDIUM"

    return _generate_recommendations(data, risk_level)
