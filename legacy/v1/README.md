# Explainable AI Healthcare Early Warning & Risk Decision Support System

## Overview

This project is a research and decision-support prototype for estimating heart-disease risk from 13 clinical features. It combines an existing trained scikit-learn model with FastAPI, PostgreSQL, SHAP feature contributions, risk/early-warning messages, and a browser dashboard.

It is **not a medical diagnostic system** and does not replace assessment by a qualified healthcare professional.

## Features

- Heart-disease prediction and positive-class probability
- Low, medium, and high early-warning risk bands
- SHAP-based feature contributions for each prediction
- Input-aware recommendations that encourage professional review where appropriate
- PostgreSQL persistence and prediction history
- FastAPI OpenAPI documentation at `/docs`
- Responsive frontend dashboard for entering features, reviewing results, and viewing history
- Strict API validation that follows the values used by the trained dataset

## Architecture

```text
Frontend (HTML/CSS/JS)
        │ HTTP + CORS
        ▼
FastAPI (`backend.main`)
        ├── Prediction service → existing `models/best_model.pkl`
        ├── SHAP service → real model contributions
        ├── Recommendation adapter → existing `src/recommendation.py`
        └── SQLAlchemy → PostgreSQL `healthcare_db.predictions`
```

## Tech stack

Python, pandas, scikit-learn, SHAP, FastAPI, Uvicorn, SQLAlchemy, PostgreSQL/psycopg, and plain HTML/CSS/JavaScript.

## Project structure

```text
src/                    Original data, training, EDA, ensemble, CLI, SHAP, and recommendation work
models/                 Authoritative trained model and feature order artifacts
backend/                FastAPI API, database code, schemas, CRUD, and services
backend/sevices/        Existing service directory (name intentionally preserved)
frontend/               Dashboard assets
data/heart_disease.csv  Cleaned Cleveland heart-disease dataset
reports/                Existing EDA and evaluation outputs
```

`models/best_model.pkl` is the existing fitted `StandardScaler` + `LogisticRegression` pipeline. The API uses the saved feature order in `models/feature_names.pkl`:

`age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal`

The empty compatibility files in `backend/model/` are not used. Do not replace or retrain the root artifacts merely to start the application.

## Installation

Use Python 3.10+ and install the project dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Database setup

Create the `healthcare_db` PostgreSQL database if it does not already exist. Copy the example environment file and fill in your local password:

```powershell
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env`, for example:

```text
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/healthcare_db
```

The `.env` file is ignored by Git. Create the table without deleting any existing data:

```powershell
python -m backend.init_db
python -m backend.test_db
```

## Run the application

From the repository root, start the API:

```powershell
uvicorn backend.main:app --reload
```

Verify `http://127.0.0.1:8000/health`, then open API documentation at `http://127.0.0.1:8000/docs`.

In a second terminal, serve the frontend:

```powershell
python -m http.server 5500 --directory frontend
```

Open `http://127.0.0.1:5500`. The frontend calls the API at `http://127.0.0.1:8000` and renders prediction, probability, risk summary, early warning, recommendations, SHAP factors, and saved history.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | API message and decision-support disclaimer |
| GET | `/health` | API readiness check |
| POST | `/predict` | Predict, explain, recommend, and persist a patient result |
| GET | `/history` | Return persisted predictions (newest first) |
| GET | `/predictions` | Backwards-compatible alias for history |
| GET | `/predictions/{prediction_id}` | Return one saved prediction |

Example request:

```json
{
  "age": 63,
  "sex": 1,
  "cp": 1,
  "trestbps": 145,
  "chol": 233,
  "fbs": 1,
  "restecg": 2,
  "thalach": 150,
  "exang": 0,
  "oldpeak": 2.3,
  "slope": 3,
  "ca": 0,
  "thal": 6
}
```

Example response fields:

```json
{
  "prediction_id": 42,
  "prediction": "No Heart Disease",
  "probability": 0.4034,
  "risk_level": "MEDIUM",
  "risk_summary": {"score": 40.34, "level": "MEDIUM", "severity": "Moderate"},
  "early_warning": "Moderate risk signal detected. Consider medical review and continued monitoring.",
  "factors_increasing_risk": [{"feature": "slope", "patient_value": 3.0, "shap_contribution": 0.82}],
  "recommendations": [{"priority": "Medium", "category": "Clinical", "title": "Consult Healthcare Provider", "reason": "..."}],
  "explainability_status": "available"
}
```

## Explainability, early warning, and recommendations

The service calculates actual SHAP values from the saved model; it never fabricates feature contributions. Positive values identify factors that increased the model score for the positive class and negative values identify factors that reduced it. If a future package/model incompatibility prevents SHAP from running, a valid prediction is still saved and the response explicitly marks explainability as unavailable.

Risk bands are probability based: low below 0.30, medium from 0.30 to below 0.70, and high at or above 0.70. Recommendations come from the existing `src/recommendation.py` engine and are based on risk level and submitted values such as blood pressure, cholesterol, blood sugar, maximum heart rate, and oldpeak.

## Testing

Run the module/import check and database check:

```powershell
python -m compileall backend src
python -m backend.test_db
```

With the API running, test the required endpoints:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/history
```

Submit the example JSON above to `POST /predict`, then check `/history` to confirm that the record was stored. The project verification should also include opening the frontend in a browser, submitting the form, and checking its browser console for errors.

## Limitations and future work

The dataset is relatively small and based on historical Cleveland data; probability calibration, fairness, external validation, clinical workflow integration, authentication, and audit controls are outside this prototype. Future work could add clinician-reviewed validation, stronger access control, pagination/filtering for history, model monitoring, and patient-specific longitudinal data.
