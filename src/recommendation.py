def create_recommendation(
    priority: str,
    category: str,
    title: str,
    reason: str,
) -> dict:
    return {
        "priority": priority,
        "category": category,
        "title": title,
        "reason": reason,
    }
def _get_numeric_value(patient_data: dict, feature_name: str) -> float | None:
    """Return a numeric value for a feature, or None if unavailable."""
    value = patient_data.get(feature_name)

    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def generate_recommendations(
    patient_data: dict,
    risk_level: str,
) -> list[dict]:
    """Generate personalized recommendations."""

    recommendations: list[dict] = []

    def add_recommendation(
        priority: str,
        category: str,
        title: str,
        reason: str,
    ) -> None:

        recommendation = create_recommendation(
            priority,
            category,
            title,
            reason,
        )

        if recommendation not in recommendations:
            recommendations.append(recommendation)

    # -------------------------
    # Overall risk recommendation
    # -------------------------

    risk_level = risk_level.upper()

    if risk_level == "LOW":
        add_recommendation(
            "Low",
            "General",
            "Maintain Healthy Lifestyle",
            "Continue routine exercise, healthy diet, and annual check-ups.",
        )

    elif risk_level == "MEDIUM":
        add_recommendation(
            "Medium",
            "Clinical",
            "Consult Healthcare Provider",
            "Schedule a medical consultation to review cardiovascular risk.",
        )

    elif risk_level == "HIGH":
        add_recommendation(
            "High",
            "Urgent",
            "Consult Cardiologist",
            "Seek prompt cardiology consultation and follow the prescribed treatment plan.",
        )

    # -------------------------
    # Patient features
    # -------------------------

    age = _get_numeric_value(patient_data, "age")
    trestbps = _get_numeric_value(patient_data, "trestbps")
    chol = _get_numeric_value(patient_data, "chol")
    fbs = _get_numeric_value(patient_data, "fbs")
    thalach = _get_numeric_value(patient_data, "thalach")
    oldpeak = _get_numeric_value(patient_data, "oldpeak")

    if age is not None and age > 60:
        add_recommendation(
            "Medium",
            "Screening",
            "Cardiovascular Screening",
            "Age above 60 increases cardiovascular risk. Regular screening is recommended.",
        )

    if trestbps is not None and trestbps > 140:
        add_recommendation(
            "High",
            "Blood Pressure",
            "Monitor Blood Pressure",
            "Blood pressure is elevated. Regular monitoring and lifestyle modification are recommended.",
        )

    if chol is not None and chol > 240:
        add_recommendation(
            "Medium",
            "Diet",
            "Reduce Cholesterol",
            "High cholesterol detected. Adopt a low-fat diet and discuss treatment options with your clinician.",
        )

    if fbs == 1:
        add_recommendation(
            "Medium",
            "Diabetes",
            "Monitor Blood Glucose",
            "Elevated fasting blood sugar may indicate impaired glucose regulation.",
        )

    if thalach is not None and thalach < 100:
        add_recommendation(
            "Medium",
            "Exercise",
            "Fitness Evaluation",
            "A supervised cardiovascular fitness assessment is recommended before starting vigorous exercise.",
        )

    if oldpeak is not None and oldpeak > 2:
        add_recommendation(
            "High",
            "Diagnostic",
            "Stress Test",
            "Exercise-induced ST depression suggests further cardiac evaluation may be appropriate.",
        )

    return recommendations
