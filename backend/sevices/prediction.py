from pathlib import Path

import joblib
import pandas as pd


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

MODEL_FILE = BASE_DIR / "models" / "best_model.pkl"
FEATURE_NAMES_FILE = BASE_DIR / "models" / "feature_names.pkl"


REQUIRED_FEATURE_ORDER = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
]


if not MODEL_FILE.exists():
    raise RuntimeError(f"Model not found: {MODEL_FILE}")

if not FEATURE_NAMES_FILE.exists():
    raise RuntimeError(f"Feature names not found: {FEATURE_NAMES_FILE}")


model = joblib.load(MODEL_FILE)
FEATURE_ORDER = joblib.load(FEATURE_NAMES_FILE)


if list(FEATURE_ORDER) != REQUIRED_FEATURE_ORDER:
    raise RuntimeError(
        "Saved feature names do not match the required feature order."
    )


def get_risk_details(probability: float) -> tuple[str, str]:
    """Convert prediction probability into a risk level and early warning."""

    if probability < 0.30:
        return (
            "LOW",
            "No immediate high-risk signal detected. Continue routine health monitoring."
        )

    if probability < 0.70:
        return (
            "MEDIUM",
            "Moderate risk signal detected. Consider medical review and continued monitoring."
        )

    return (
        "HIGH",
        "High risk signal detected. Prompt clinical evaluation is recommended."
    )


def predict_patient(patient_data: dict) -> dict:
    """
    Run heart disease prediction and return prediction details.
    """

    input_data = pd.DataFrame(
        [patient_data],
        columns=REQUIRED_FEATURE_ORDER
    )

    prediction_value = model.predict(input_data)[0]

    probabilities = model.predict_proba(input_data)[0]
    classes = list(model.classes_)

    if 1 not in classes:
        raise ValueError(
            "The saved model does not contain class 1."
        )

    heart_disease_probability = float(
        probabilities[classes.index(1)]
    )

    risk_level, early_warning = get_risk_details(
        heart_disease_probability
    )

    prediction_label = (
        "Heart Disease Present"
        if prediction_value == 1
        else "No Heart Disease"
    )

    return {
        "prediction_value": int(prediction_value),
        "prediction": prediction_label,
        "probability": heart_disease_probability,
        "risk_level": risk_level,
        "early_warning": early_warning,
    }