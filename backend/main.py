"""
FastAPI backend for heart-disease model predictions.

This API is a machine-learning decision-support prototype.
It does not provide medical diagnoses or medical advice.
"""

import logging
import math
from typing import Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import get_db
from . import crud, schemas

from .sevices.prediction import (
    predict_patient,
    REQUIRED_FEATURE_ORDER,
)

from .sevices.explainability import (
    get_shap_contributions,
    get_risk_factors,
)

from .sevices.recommendations import generate_recommendations


logger = logging.getLogger(__name__)


app = FastAPI(
    title="Explainable AI Healthcare Early Warning API",
    description=(
        "Heart-disease model prediction with explainability, "
        "recommendations, and prediction history."
    ),
    version="1.0.0",
)


LOCAL_FRONTEND_ORIGINS = [
    "null",
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PatientInput(BaseModel):
    """Validated clinical input for the heart disease prediction model."""

    model_config = ConfigDict(extra="forbid")

    age: int
    sex: int
    cp: int
    trestbps: int
    chol: int
    fbs: int
    restecg: int
    thalach: int
    exang: int
    oldpeak: float
    slope: int
    ca: int
    thal: int

    @field_validator("*")
    @classmethod
    def values_must_be_finite(cls, value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Each patient value must be finite.")
        return value

    @field_validator("age")
    @classmethod
    def validate_age(cls, value: int) -> int:
        if not 18 <= value <= 100:
            raise ValueError("Age must be between 18 and 100.")
        return value

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, value: int) -> int:
        if value not in [0, 1]:
            raise ValueError("Sex must be 0 or 1.")
        return value

    @field_validator("cp")
    @classmethod
    def validate_cp(cls, value: int) -> int:
        if value not in [1, 2, 3, 4]:
            raise ValueError("cp must be 1, 2, 3, or 4.")
        return value

    @field_validator("trestbps")
    @classmethod
    def validate_trestbps(cls, value: int) -> int:
        if not 70 <= value <= 250:
            raise ValueError("trestbps must be between 70 and 250.")
        return value

    @field_validator("chol")
    @classmethod
    def validate_chol(cls, value: int) -> int:
        if not 100 <= value <= 600:
            raise ValueError("chol must be between 100 and 600.")
        return value

    @field_validator("fbs")
    @classmethod
    def validate_fbs(cls, value: int) -> int:
        if value not in [0, 1]:
            raise ValueError("fbs must be 0 or 1.")
        return value

    @field_validator("restecg")
    @classmethod
    def validate_restecg(cls, value: int) -> int:
        if value not in [0, 1, 2]:
            raise ValueError("restecg must be 0, 1, or 2.")
        return value

    @field_validator("thalach")
    @classmethod
    def validate_thalach(cls, value: int) -> int:
        if not 40 <= value <= 250:
            raise ValueError("thalach must be between 40 and 250.")
        return value

    @field_validator("exang")
    @classmethod
    def validate_exang(cls, value: int) -> int:
        if value not in [0, 1]:
            raise ValueError("exang must be 0 or 1.")
        return value

    @field_validator("oldpeak")
    @classmethod
    def validate_oldpeak(cls, value: float) -> float:
        if not 0 <= value <= 10:
            raise ValueError("oldpeak must be between 0 and 10.")
        return value

    @field_validator("slope")
    @classmethod
    def validate_slope(cls, value: int) -> int:
        if value not in [1, 2, 3]:
            raise ValueError("slope must be 1, 2, or 3.")
        return value

    @field_validator("ca")
    @classmethod
    def validate_ca(cls, value: int) -> int:
        if value not in [0, 1, 2, 3]:
            raise ValueError("ca must be between 0 and 3.")
        return value

    @field_validator("thal")
    @classmethod
    def validate_thal(cls, value: int) -> int:
        if value not in [3, 6, 7]:
            raise ValueError("thal must be 3, 6, or 7.")
        return value

@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Healthcare prediction API is running.",
        "disclaimer": "Decision-support prototype; not a medical diagnosis.",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """Lightweight readiness endpoint that does not require a database query."""

    return {"status": "ok", "service": "healthcare-prediction-api"}


@app.post("/predict")
def predict(
    patient: PatientInput,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Predict heart disease risk, generate recommendations,
    calculate SHAP explanations, and save the result.
    """

    patient_dict = patient.model_dump()

    try:
        prediction_result = predict_patient(patient_dict)
    except Exception as error:
        logger.exception("Model prediction failed")
        raise HTTPException(
            status_code=500,
            detail="The saved model could not process this prediction.",
        ) from error

    prediction_value = prediction_result["prediction_value"]
    heart_disease_probability = prediction_result["probability"]
    risk_level = prediction_result["risk_level"]
    prediction_label = prediction_result["prediction"]
    early_warning = prediction_result["early_warning"]
    recommendations = generate_recommendations(
        data=patient_dict,
        prediction=prediction_value,
        probability=heart_disease_probability,
    )

    # Explainability must not turn an otherwise valid prediction into an API
    # failure when SHAP and a model version are temporarily incompatible.
    increasing_factors: list[dict[str, Any]] = []
    decreasing_factors: list[dict[str, Any]] = []
    explainability_status = "available"
    try:
        patient_data = pd.DataFrame([patient_dict], columns=REQUIRED_FEATURE_ORDER)
        contributions = get_shap_contributions(patient_data)
        increasing_factors, decreasing_factors = get_risk_factors(
            patient_data, contributions
        )
    except Exception:
        logger.exception("SHAP explanation failed")
        explainability_status = "unavailable"

    prediction_data = schemas.PredictionCreate(
        **patient_dict,
        prediction=prediction_label,
        probability=heart_disease_probability,
        risk_level=risk_level,
    )
    try:
        saved_prediction = crud.create_prediction(db, prediction_data)
    except SQLAlchemyError as error:
        logger.exception("Saving prediction failed")
        raise HTTPException(
            status_code=503,
            detail="Prediction was calculated but could not be saved to the database.",
        ) from error

    risk_summary = {
        "score": round(heart_disease_probability * 100, 2),
        "level": risk_level,
        "severity": (
            "High" if risk_level == "HIGH" else "Moderate" if risk_level == "MEDIUM" else "Low"
        ),
    }

    return {
        "prediction_id": saved_prediction.id,
        "prediction": prediction_label,
        "probability": heart_disease_probability,
        "risk_level": risk_level,
        "risk_summary": risk_summary,
        "early_warning": early_warning,
        "recommendations": recommendations,
        "factors_increasing_risk": increasing_factors,
        "factors_decreasing_risk": decreasing_factors,
        "explainability_status": explainability_status,
        "created_at": saved_prediction.created_at,
        "disclaimer": "This system is a machine-learning decision-support prototype and is not a medical diagnosis.",
    }
@app.get(
    "/history",
    response_model=list[schemas.PredictionResponse]
)
def get_prediction_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Return saved prediction history.
    """

    try:
        return crud.get_predictions(db, skip, limit)
    except SQLAlchemyError as error:
        logger.exception("Reading prediction history failed")
        raise HTTPException(status_code=503, detail="Prediction history is unavailable.") from error


app.add_api_route(
    "/predictions",
    get_prediction_history,
    methods=["GET"],
    response_model=list[schemas.PredictionResponse],
    include_in_schema=False,
)


@app.get(
    "/predictions/{prediction_id}",
    response_model=schemas.PredictionResponse
)
def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db)
):
    """
    Return one saved prediction.
    """

    prediction = crud.get_prediction_by_id(
        db,
        prediction_id
    )

    if prediction is None:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found."
        )

    return prediction
