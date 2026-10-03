"""Explain one heart-disease model prediction with SHAP.

This script explains how the saved machine-learning model used its input
features.  It is not a medical diagnosis and must not be used as medical
advice.
"""

import argparse
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

# Use a non-interactive backend so plots can be saved when this script is run
# from a terminal or server without a graphical display.
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# Find project files relative to this script, so the command works from any
# current working directory.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "heart_disease.csv"
MODEL_FILE = BASE_DIR / "models" / "best_model.pkl"
EXPLANATION_DIR = BASE_DIR / "models" / "explanations"


def parse_arguments() -> argparse.Namespace:
    """Allow the user to choose which dataset row represents the patient."""
    parser = argparse.ArgumentParser(
        description="Explain one saved heart-disease model prediction with SHAP."
    )
    parser.add_argument(
        "--patient-index",
        type=int,
        default=0,
        help="Zero-based row number from heart_disease.csv to explain (default: 0).",
    )
    return parser.parse_args()


def prepare_model_inputs(model, features: pd.DataFrame):
    """Transform features for SHAP while preserving compatibility with pipelines.

    A scikit-learn Pipeline can contain preprocessing (for example, scaling)
    followed by the fitted classifier. SHAP should explain the fitted
    classifier using the same transformed values it receives during prediction.
    For a non-pipeline model, the original feature values are used directly.
    """
    if isinstance(model, Pipeline):
        estimator = model.steps[-1][1]
        transformer = model[:-1]
        transformed_values = transformer.transform(features)

        try:
            feature_names = list(transformer.get_feature_names_out())
        except (AttributeError, ValueError):
            feature_names = list(features.columns)
    else:
        estimator = model
        transformed_values = features.to_numpy()
        feature_names = list(features.columns)

    # Some preprocessing steps return sparse matrices, so convert the result
    # to a regular array before creating a SHAP-friendly DataFrame.
    if hasattr(transformed_values, "toarray"):
        transformed_values = transformed_values.toarray()

    transformed_values = np.asarray(transformed_values)

    # Fall back to neutral column names if a custom transformer changes the
    # number of columns but cannot report their output names.
    if len(feature_names) != transformed_values.shape[1]:
        feature_names = [f"feature_{index}" for index in range(transformed_values.shape[1])]

    transformed_features = pd.DataFrame(
        transformed_values,
        columns=feature_names,
        index=features.index,
    )
    return estimator, transformed_features


def select_positive_class_explanation(shap_values, class_index: int):
    """Return SHAP values for the Heart Disease Present class when available."""
    # Newer SHAP versions usually return one Explanation with an output axis.
    if hasattr(shap_values, "values") and shap_values.values.ndim == 3:
        return shap_values[:, :, class_index]

    # Older SHAP explainers may return a list with one array per class.
    if isinstance(shap_values, list):
        return shap_values[class_index]

    # Binary tree explainers can return values for only the positive class.
    return shap_values


def main() -> None:
    """Load the saved model, explain one patient, and save a SHAP bar plot."""
    args = parse_arguments()

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")
    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"Saved model not found: {MODEL_FILE}")

    # Load the same cleaned dataset used during model training.
    dataset = pd.read_csv(DATA_FILE)
    if "target" not in dataset.columns:
        raise ValueError("The dataset must contain a 'target' column.")
    if not 0 <= args.patient_index < len(dataset):
        raise IndexError(
            f"patient-index must be between 0 and {len(dataset) - 1}; "
            f"received {args.patient_index}."
        )

    features = dataset.drop(columns="target")
    patient = features.iloc[[args.patient_index]]
    model = joblib.load(MODEL_FILE)

    # Use the complete saved model for the prediction. This ensures pipeline
    # preprocessing is applied exactly as it was during training.
    prediction = model.predict(patient)[0]
    if not hasattr(model, "predict_proba"):
        raise TypeError("The saved model must support predict_proba for risk reporting.")

    probabilities = model.predict_proba(patient)[0]
    classes = list(model.classes_)
    positive_class_index = classes.index(1) if 1 in classes else int(np.argmax(classes))
    heart_disease_probability = probabilities[positive_class_index]

    # Prepare transformed data for the final estimator when the saved model is
    # a Pipeline (such as StandardScaler followed by LogisticRegression).
    estimator, shap_features = prepare_model_inputs(model, features)
    shap_patient = shap_features.iloc[[args.patient_index]]

    # A small background sample represents typical training inputs. SHAP picks
    # an appropriate explainer (TreeExplainer, LinearExplainer, etc.) based on
    # the fitted estimator, so this works for tree and linear classifiers.
    background = shap_features.sample(n=min(100, len(shap_features)), random_state=42)
    explainer = shap.Explainer(estimator, background)
    raw_shap_values = explainer(shap_patient)
    patient_shap_values = select_positive_class_explanation(
        raw_shap_values, positive_class_index
    )

    # Obtain a one-dimensional contribution for each feature. A positive SHAP
    # value increases the model's score for Heart Disease Present; a negative
    # value decreases it. This describes model behavior, not clinical cause.
    if hasattr(patient_shap_values, "values"):
        contributions = patient_shap_values.values[0]
    else:
        contributions = np.asarray(patient_shap_values)[0]

    contribution_series = pd.Series(contributions, index=shap_features.columns)
    increasing_features = contribution_series.sort_values(ascending=False).head(5)
    decreasing_features = contribution_series.sort_values().head(5)

    # Create the output directory only when an explanation is generated.
    EXPLANATION_DIR.mkdir(parents=True, exist_ok=True)
    plot_file = EXPLANATION_DIR / f"patient_{args.patient_index}_shap_bar.png"

    # SHAP's bar plot is a compact visualization of the selected patient's
    # strongest feature contributions. show=False keeps it suitable for scripts.
    shap.plots.bar(patient_shap_values[0], max_display=10, show=False)
    plt.tight_layout()
    plt.savefig(plot_file, dpi=150, bbox_inches="tight")
    plt.close()

    predicted_label = "Heart Disease Present" if prediction == 1 else "No Heart Disease"
    print("=" * 60)
    print("SHAP MODEL EXPLANATION")
    print("=" * 60)
    print(f"Patient row: {args.patient_index}")
    print(f"Model prediction: {predicted_label} ({prediction})")
    print(f"Model probability of Heart Disease Present: {heart_disease_probability:.2%}")
    print("\nTop features increasing the model's predicted risk:")
    for feature, value in increasing_features.items():
        print(f"  {feature}: {value:+.4f}")
    print("\nTop features decreasing the model's predicted risk:")
    for feature, value in decreasing_features.items():
        print(f"  {feature}: {value:+.4f}")
    print(f"\nSaved SHAP visualization: {plot_file}")
    print(
        "\nImportant: This explanation describes model behavior for this dataset row "
        "and is not a medical diagnosis or medical advice."
    )


if __name__ == "__main__":
    main()
