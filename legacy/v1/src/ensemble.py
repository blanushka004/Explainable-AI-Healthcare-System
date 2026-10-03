"""Train and evaluate a soft-voting ensemble for heart disease prediction."""

from pathlib import Path

import joblib
import matplotlib
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    auc,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier


# Use a non-interactive backend so the script works in terminal environments.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "heart_disease.csv"
EVALUATION_DIRECTORY = PROJECT_ROOT / "reports" / "evaluation"
MODELS_DIRECTORY = PROJECT_ROOT / "models"
TARGET_COLUMN = "target"
RANDOM_STATE = 42


def create_output_directories() -> None:
    """Create report and model directories if they are missing."""
    EVALUATION_DIRECTORY.mkdir(parents=True, exist_ok=True)
    MODELS_DIRECTORY.mkdir(parents=True, exist_ok=True)


def load_and_split_data() -> tuple[pd.DataFrame, pd.DataFrame,
                                   pd.Series, pd.Series]:
    """Load data and create an 80/20 stratified train-test split."""
    dataframe = pd.read_csv(DATASET_PATH)
    features = dataframe.drop(columns=TARGET_COLUMN)
    target = dataframe[TARGET_COLUMN]

    return train_test_split(
        features,
        target,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=target,
    )


def build_models() -> tuple[LogisticRegression, DecisionTreeClassifier,
                            RandomForestClassifier, XGBClassifier]:
    """Build the individual classifiers used for comparison and voting."""
    logistic_regression = LogisticRegression(
        max_iter=1000,
        random_state=RANDOM_STATE,
    )
    decision_tree = DecisionTreeClassifier(random_state=RANDOM_STATE)
    random_forest = RandomForestClassifier(
        n_estimators=200,
        random_state=RANDOM_STATE,
    )
    xgboost = XGBClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=RANDOM_STATE,
    )
    return logistic_regression, decision_tree, random_forest, xgboost


def evaluate_model(model_name: str, model: object, features: pd.DataFrame,
                   target: pd.Series) -> tuple[dict[str, float], pd.Series,
                                                pd.Series]:
    """Calculate and print classification metrics for a trained model."""
    predictions = model.predict(features)
    probabilities = model.predict_proba(features)[:, 1]
    metrics = {
        "Model": model_name,
        "Accuracy": accuracy_score(target, predictions),
        "Precision": precision_score(target, predictions, zero_division=0),
        "Recall": recall_score(target, predictions, zero_division=0),
        "F1 Score": f1_score(target, predictions, zero_division=0),
        "ROC-AUC": roc_auc_score(target, probabilities),
    }

    print(f"\n{model_name}")
    for metric_name, value in metrics.items():
        if metric_name != "Model":
            print(f"{metric_name}: {value:.4f}")

    return metrics, predictions, probabilities


def save_comparison_table(results: list[dict[str, float]]) -> pd.DataFrame:
    """Save metrics from all models to a comparison CSV file."""
    comparison = pd.DataFrame(results).sort_values(
        by="Accuracy",
        ascending=False,
    )
    output_path = EVALUATION_DIRECTORY / "model_comparison.csv"
    comparison.to_csv(output_path, index=False)
    print(f"Generated: {output_path.relative_to(PROJECT_ROOT)}")
    return comparison


def save_confusion_matrix(target: pd.Series, predictions: pd.Series) -> None:
    """Create and save a confusion matrix for the voting ensemble."""
    matrix = confusion_matrix(target, predictions)
    figure, axis = plt.subplots(figsize=(7, 6))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        cbar=False,
        xticklabels=["No Heart Disease", "Heart Disease"],
        yticklabels=["No Heart Disease", "Heart Disease"],
        ax=axis,
    )
    axis.set_title("Voting Ensemble Confusion Matrix")
    axis.set_xlabel("Predicted Label")
    axis.set_ylabel("True Label")
    figure.tight_layout()

    output_path = EVALUATION_DIRECTORY / "ensemble_confusion_matrix.png"
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    print(f"Generated: {output_path.relative_to(PROJECT_ROOT)}")


def save_roc_curve(target: pd.Series, probabilities: pd.Series) -> None:
    """Create and save a ROC curve for the voting ensemble."""
    false_positive_rate, true_positive_rate, _ = roc_curve(
        target,
        probabilities,
    )
    roc_auc = auc(false_positive_rate, true_positive_rate)
    figure, axis = plt.subplots(figsize=(8, 6))
    axis.plot(
        false_positive_rate,
        true_positive_rate,
        color="darkorange",
        linewidth=2,
        label=f"Voting Ensemble (AUC = {roc_auc:.3f})",
    )
    axis.plot([0, 1], [0, 1], color="navy", linestyle="--")
    axis.set_title("Voting Ensemble ROC Curve")
    axis.set_xlabel("False Positive Rate")
    axis.set_ylabel("True Positive Rate")
    axis.legend(loc="lower right")
    axis.grid(alpha=0.3)
    figure.tight_layout()

    output_path = EVALUATION_DIRECTORY / "ensemble_roc_curve.png"
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    print(f"Generated: {output_path.relative_to(PROJECT_ROOT)}")


def save_model_and_scaler(ensemble: VotingClassifier,
                          scaler: StandardScaler) -> None:
    """Save the fitted voting ensemble and Logistic Regression scaler."""
    model_path = MODELS_DIRECTORY / "voting_ensemble.pkl"
    scaler_path = MODELS_DIRECTORY / "scaler.pkl"
    joblib.dump(ensemble, model_path)
    print(f"Generated: {model_path.relative_to(PROJECT_ROOT)}")
    joblib.dump(scaler, scaler_path)
    print(f"Generated: {scaler_path.relative_to(PROJECT_ROOT)}")


def main() -> None:
    """Train, evaluate, save, and report the voting ensemble workflow."""
    # Load data, create output folders, and prepare scaled regression data.
    create_output_directories()
    sns.set_theme(style="whitegrid")
    x_train, x_test, y_train, y_test = load_and_split_data()
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    # Train each individual classifier.
    logistic_regression, decision_tree, random_forest, xgboost = build_models()
    logistic_regression.fit(x_train_scaled, y_train)
    decision_tree.fit(x_train, y_train)
    random_forest.fit(x_train, y_train)
    xgboost.fit(x_train, y_train)

    # Build an ensemble with scaling applied only to Logistic Regression.
    ensemble = VotingClassifier(
        estimators=[
            (
                "logistic_regression",
                Pipeline(
                    [
                        ("scaler", StandardScaler()),
                        (
                            "model",
                            LogisticRegression(
                                max_iter=1000,
                                random_state=RANDOM_STATE,
                            ),
                        ),
                    ]
                ),
            ),
            ("random_forest", random_forest),
            ("xgboost", xgboost),
        ],
        voting="soft",
    )
    ensemble.fit(x_train, y_train)

    # Evaluate every individual model and the voting ensemble on the test set.
    evaluations = []
    model_inputs = [
        ("Logistic Regression", logistic_regression, x_test_scaled),
        ("Decision Tree", decision_tree, x_test),
        ("Random Forest", random_forest, x_test),
        ("XGBoost", xgboost, x_test),
        ("Voting Ensemble", ensemble, x_test),
    ]
    ensemble_predictions = None
    ensemble_probabilities = None
    for model_name, model, test_features in model_inputs:
        metrics, predictions, probabilities = evaluate_model(
            model_name,
            model,
            test_features,
            y_test,
        )
        evaluations.append(metrics)
        if model_name == "Voting Ensemble":
            ensemble_predictions = predictions
            ensemble_probabilities = probabilities

    # Save comparisons, visual reports, and trained artifacts.
    comparison = save_comparison_table(evaluations)
    save_confusion_matrix(y_test, ensemble_predictions)
    save_roc_curve(y_test, ensemble_probabilities)
    save_model_and_scaler(ensemble, scaler)

    best_model = comparison.iloc[0]
    print(
        f"Best performing model (by accuracy): {best_model['Model']} "
        f"({best_model['Accuracy']:.4f})"
    )
    print("Training completed successfully.")
    print("Generated:")
    print("model_comparison.csv")
    print("ensemble_confusion_matrix.png")
    print("ensemble_roc_curve.png")
    print("voting_ensemble.pkl")
    print("scaler.pkl")


if __name__ == "__main__":
    main()
