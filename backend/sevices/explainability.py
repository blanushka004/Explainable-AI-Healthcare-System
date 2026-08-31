from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap

from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .prediction import (
    model,
    REQUIRED_FEATURE_ORDER,
)


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_FILE = BASE_DIR / "data" / "heart_disease.csv"


def load_shap_background() -> pd.DataFrame:
    """Load deterministic background data for SHAP."""

    if not DATA_FILE.exists():
        raise RuntimeError(
            f"SHAP background data not found: {DATA_FILE}"
        )

    dataset = pd.read_csv(DATA_FILE)

    if not set(REQUIRED_FEATURE_ORDER).issubset(dataset.columns):
        raise RuntimeError(
            "SHAP background data is missing required features."
        )

    return dataset.loc[
        :, REQUIRED_FEATURE_ORDER
    ].sample(
        n=min(100, len(dataset)),
        random_state=42
    )


SHAP_BACKGROUND = load_shap_background()


def _as_dense_array(values: Any) -> np.ndarray:
    """Convert sparse or pandas values to NumPy array."""

    if hasattr(values, "toarray"):
        values = values.toarray()

    return np.asarray(values)


def _positive_class_contributions(
    shap_values: Any,
    positive_class_index: int,
    classes: list[Any],
) -> np.ndarray:
    """Extract SHAP values for Heart Disease Present."""

    values = (
        shap_values.values
        if hasattr(shap_values, "values")
        else shap_values
    )

    if isinstance(values, list):

        contributions = _as_dense_array(
            values[positive_class_index]
        )[0]

    else:

        values = _as_dense_array(values)

        if values.ndim == 3:

            contributions = values[
                0,
                :,
                positive_class_index
            ]

        elif values.ndim == 2:

            contributions = values[0]

            if len(classes) == 2 and classes[1] != 1:
                contributions = -contributions

        elif values.ndim == 1:

            contributions = values

        else:

            raise ValueError(
                "Unexpected SHAP value shape."
            )

    return np.asarray(
        contributions,
        dtype=float
    ).reshape(-1)


def _transformed_pipeline_inputs(
    pipeline: Pipeline,
    patient_data: pd.DataFrame,
):
    """Transform patient and background data for pipeline models."""

    estimator = pipeline.steps[-1][1]

    transformer = pipeline[:-1]

    transformed_patient = _as_dense_array(
        transformer.transform(patient_data)
    )

    transformed_background = _as_dense_array(
        transformer.transform(SHAP_BACKGROUND)
    )

    try:

        transformed_names = list(
            transformer.get_feature_names_out()
        )

    except (AttributeError, ValueError):

        transformed_names = list(
            REQUIRED_FEATURE_ORDER
        )

    if (
        transformed_patient.shape[1]
        != len(REQUIRED_FEATURE_ORDER)
        or transformed_background.shape[1]
        != len(REQUIRED_FEATURE_ORDER)
        or transformed_names
        != REQUIRED_FEATURE_ORDER
    ):

        return None

    return (
        estimator,
        pd.DataFrame(
            transformed_patient,
            columns=REQUIRED_FEATURE_ORDER
        ),
        pd.DataFrame(
            transformed_background,
            columns=REQUIRED_FEATURE_ORDER
        ),
    )


def _model_agnostic_contributions(
    patient_data: pd.DataFrame,
    positive_index: int,
) -> np.ndarray:
    """Fallback SHAP explanation."""

    explainer = shap.KernelExplainer(
        lambda values: model.predict_proba(
            pd.DataFrame(
                values,
                columns=REQUIRED_FEATURE_ORDER
            )
        )[:, positive_index],
        SHAP_BACKGROUND,
    )

    shap_values = explainer.shap_values(
        patient_data,
        nsamples=200
    )

    return _positive_class_contributions(
        shap_values,
        positive_index,
        list(model.classes_),
    )


def get_shap_contributions(
    patient_data: pd.DataFrame,
) -> np.ndarray:
    """Calculate SHAP contributions."""

    classes = list(model.classes_)

    if 1 not in classes:
        raise ValueError(
            "The saved model does not contain class 1."
        )

    positive_index = classes.index(1)

    estimator = model

    shap_patient = patient_data

    shap_background = SHAP_BACKGROUND

    if isinstance(model, Pipeline):

        pipeline_inputs = (
            _transformed_pipeline_inputs(
                model,
                patient_data
            )
        )

        if pipeline_inputs is None:

            return _model_agnostic_contributions(
                patient_data,
                positive_index
            )

        (
            estimator,
            shap_patient,
            shap_background,
        ) = pipeline_inputs

    if isinstance(
        estimator,
        (
            RandomForestClassifier,
            GradientBoostingClassifier,
        ),
    ):

        shap_values = shap.TreeExplainer(
            estimator
        )(shap_patient)

    elif isinstance(
        estimator,
        LogisticRegression,
    ):

        shap_values = shap.LinearExplainer(
            estimator,
            shap_background
        )(shap_patient)

    else:

        return _model_agnostic_contributions(
            patient_data,
            positive_index
        )

    return _positive_class_contributions(
        shap_values,
        positive_index,
        classes,
    )


def get_risk_factors(
    patient_data: pd.DataFrame,
    contributions: np.ndarray,
):
    """Return factors increasing and decreasing risk."""

    if contributions.shape[0] != len(
        REQUIRED_FEATURE_ORDER
    ):

        raise ValueError(
            "SHAP output does not match feature count."
        )

    contribution_series = pd.Series(
        contributions,
        index=REQUIRED_FEATURE_ORDER
    )

    def format_factors(series):

        return [
            {
                "feature": feature,
                "patient_value": float(
                    patient_data.at[0, feature]
                ),
                "shap_contribution": float(
                    contribution
                ),
            }

            for feature, contribution
            in series.items()
        ]

    increasing = (
        contribution_series[
            contribution_series > 0
        ]
        .sort_values(
            ascending=False
        )
        .head(5)
    )

    decreasing = (
        contribution_series[
            contribution_series < 0
        ]
        .sort_values()
        .head(5)
    )

    return (
        format_factors(increasing),
        format_factors(decreasing),
    )
