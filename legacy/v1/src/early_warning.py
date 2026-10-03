"""Interactive early-warning output for the saved heart-disease model.

This program reports a model prediction and a separate probability-based risk
level. It is a decision-support prototype, not a medical diagnosis.
"""

from pathlib import Path

import joblib
import pandas as pd


# Project paths are built relative to this file, so the script can be run from
# any folder on the computer.
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_FILE = BASE_DIR / "models" / "best_model.pkl"
DATA_FILE = BASE_DIR / "data" / "heart_disease.csv"

# These are the feature names and the order used when the model was trained.
EXPECTED_FEATURES = [
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

# Clear prompts make the command-line input easier to understand.
INPUT_PROMPTS = {
    "age": "Age: ",
    "sex": "Sex (1 = Male, 0 = Female): ",
    "cp": "Chest Pain Type: ",
    "trestbps": "Resting Blood Pressure: ",
    "chol": "Cholesterol: ",
    "fbs": "Fasting Blood Sugar > 120 mg/dl (1 = Yes, 0 = No): ",
    "restecg": "Resting ECG Results: ",
    "thalach": "Maximum Heart Rate Achieved: ",
    "exang": "Exercise-Induced Angina (1 = Yes, 0 = No): ",
    "oldpeak": "ST Depression (Oldpeak): ",
    "slope": "Slope of Peak Exercise ST Segment: ",
    "ca": "Number of Major Vessels: ",
    "thal": "Thalassemia: ",
}


def get_number(prompt: str) -> float:
    """Keep asking until the user enters a numeric value."""
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Please enter a numeric value.")


def get_risk_level(probability: float) -> tuple[str, str]:
    """Return the required risk level and its early-warning message."""
    if probability < 0.30:
        return (
            "LOW",
            "No immediate high-risk signal detected. Continue routine health monitoring.",
        )
    if probability < 0.70:
        return (
            "MEDIUM",
            "Moderate risk signal detected. Consider medical review and continued monitoring.",
        )
    return (
        "HIGH",
        "High risk signal detected. Prompt clinical evaluation is recommended.",
    )


def main() -> None:
    """Collect patient values, run the model, and print the warning summary."""
    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"Saved model not found: {MODEL_FILE}")
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Cleaned dataset not found: {DATA_FILE}")

    # Read only the column names from the cleaned dataset. This prevents a
    # patient-input DataFrame from accidentally using an incorrect order.
    dataset_columns = pd.read_csv(DATA_FILE, nrows=0).columns.tolist()
    if "target" not in dataset_columns:
        raise ValueError("The cleaned dataset must contain a 'target' column.")

    dataset_features = [column for column in dataset_columns if column != "target"]
    if dataset_features != EXPECTED_FEATURES:
        raise ValueError(
            "The cleaned dataset feature columns do not match the expected training order."
        )

    model = joblib.load(MODEL_FILE)
    if not hasattr(model, "predict_proba"):
        raise TypeError("The saved model must support predict_proba.")

    print("=" * 60)
    print("HEART DISEASE EARLY-WARNING DECISION SUPPORT")
    print("=" * 60)
    print("\nEnter patient information:")

    # Collect every required value in the exact feature order from the dataset.
    patient_values = {
        feature: get_number(INPUT_PROMPTS[feature]) for feature in dataset_features
    }
    patient_data = pd.DataFrame([patient_values], columns=dataset_features)

    # The model prediction and the risk level are intentionally calculated and
    # displayed separately. They answer different questions.
    prediction = model.predict(patient_data)[0]
    probabilities = model.predict_proba(patient_data)[0]
    classes = list(model.classes_)
    positive_class_index = classes.index(1) if 1 in classes else None
    if positive_class_index is None:
        raise ValueError("The saved model does not include class 1 (Heart Disease Present).")

    heart_disease_probability = probabilities[positive_class_index]
    risk_level, warning_message = get_risk_level(heart_disease_probability)
    prediction_label = "Heart Disease Present" if prediction == 1 else "No Heart Disease"

    print("\n" + "=" * 60)
    print("EARLY-WARNING RESULT")
    print("=" * 60)
    print(f"Prediction: {prediction_label}")
    print(f"Probability of Heart Disease Present: {heart_disease_probability:.2%}")
    print(f"Risk Level: {risk_level}")
    print(f"Early Warning: {warning_message}")
    print("\nThis system is a machine-learning decision-support prototype and is not a medical diagnosis.")


if __name__ == "__main__":
    main()
