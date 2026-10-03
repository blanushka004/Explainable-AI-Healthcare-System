# Clarity — Explainable AI Healthcare System

An end-to-end machine learning project for **explainable cardiovascular risk assessment** built with FastAPI, scikit-learn, SHAP, SQLAlchemy, PostgreSQL, and a responsive HTML/CSS/JavaScript frontend.

> **Educational research prototype only.** This application is not a medical diagnosis, treatment recommendation, disease-severity model, or clinically validated decision-support system.

## 🌐 Live Demo

### [Try Clarity — Explainable AI Healthcare System](https://explainable-ai-healthcare-system.onrender.com/)

The application is deployed on **Render** with a managed PostgreSQL database.

> The free Render service may take a short time to start after a period of inactivity.

---

## Project Overview

Clarity predicts the **presence of heart disease** using the UCI Cleveland Heart Disease dataset and explains each prediction using SHAP-based feature contributions.

The project goes beyond a basic ML prediction form by providing authentication, personal assessment history, explainability, input validation, model evaluation tools, versioned model artifacts, and role-based USER / ADMIN workspaces.

### Technology Stack

- **Dataset:** UCI Heart Disease — Cleveland
- **Machine Learning:** scikit-learn
- **Explainability:** SHAP
- **Backend:** FastAPI
- **Database:** PostgreSQL / SQLite
- **ORM:** SQLAlchemy
- **Frontend:** HTML, CSS, JavaScript
- **Authentication:** Database-backed sessions + Argon2
- **Deployment:** Render
- **Language:** Python 3.12

---

## Model Performance

Current packaged Logistic Regression model:

| Metric | Score |
| --- | ---: |
| Accuracy | 0.8333 |
| Precision | 0.8462 |
| Recall | 0.7857 |
| F1 Score | 0.8148 |
| ROC-AUC | **0.9498** |

These results are internal benchmark results and do not represent external clinical validation.

---

## Key Features

### Explainable Health Assessment

Users enter the 13 measurements used by the Cleveland Heart Disease dataset and receive:

- Assessment score
- Risk indicator
- SHAP explanation
- Factors that raised or lowered the model output
- Measurement summary
- Input-support checks
- Educational guidance

SHAP explanations describe model behavior and should not be interpreted as causal medical effects.

### Authentication & Security

- User registration
- Login and logout
- USER and ADMIN roles
- Argon2 password hashing
- Database-backed sessions
- HttpOnly authentication cookies
- SameSite cookies
- CSRF protection
- Session expiration
- Logout revocation
- User-specific assessment history

Public registration creates **USER** accounts only.

### USER Workspace

Authenticated users can:

- Perform health assessments
- View their personal assessment history
- Reopen stored results
- View saved SHAP explanations
- Review measurements used for each assessment
- Receive educational guidance

### ADMIN Workspace

Administrators additionally have access to:

- Model evaluation metrics
- Threshold exploration
- Dataset analysis
- Global SHAP information
- Model version information
- Batch processing tools
- Administrative API documentation

---

## Explainability

The application uses **SHAP PermutationExplainer** to explain predictions.

Each explanation includes:

- Reference prediction
- All 13 feature contributions
- Positive and negative contribution directions
- Final predicted score
- Reconstruction consistency checking

The explanations show how the machine-learning model reached its output.

They do **not** establish medical causality.

---

## Architecture

```text
                    User Browser
                         │
                         ▼
              HTML / CSS / JavaScript
                         │
                         ▼
                     FastAPI
          ┌──────────────┼───────────────┐
          │              │               │
          ▼              ▼               ▼
     Authentication   Assessment      History
       + CSRF            API             API
          │              │
          │              ▼
          │       ML Inference Engine
          │              │
          │       scikit-learn + SHAP
          │              │
          └──────────────┼───────────────┐
                         ▼               ▼
                    SQLAlchemy       Model Files
                         │
                         ▼
                PostgreSQL / SQLite
```

FastAPI serves both the frontend and backend from the same origin.

---

## Project Structure

```text
Explainable-AI-Healthcare-System/
│
├── backend/
│   ├── auth.py
│   ├── auth_cli.py
│   ├── contracts.py
│   ├── database.py
│   ├── engine.py
│   ├── main.py
│   ├── models.py
│   └── sevices/
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── src/
│   ├── explain.py
│   ├── features.py
│   ├── metrics.py
│   ├── predict.py
│   └── train_model.py
│
├── models/
│   ├── active.json
│   ├── best_model.pkl
│   └── versions/
│
├── tests/
├── examples/
├── legacy/
│
├── requirements.txt
├── requirements-postgres.txt
├── requirements-dev.txt
├── setup.bat
├── start.bat
└── README.md
```

---

## Run Locally

### Requirements

- Python 3.12
- Git
- PostgreSQL is optional

SQLite is used by default for local development.

### 1. Clone the repository

```bash
git clone https://github.com/blanushka004/Explainable-AI-Healthcare-System.git
cd Explainable-AI-Healthcare-System
```

### 2. Create the virtual environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Start the application

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

The SQLite database is created automatically when required.

---

## PostgreSQL

Install PostgreSQL dependencies:

```powershell
python -m pip install -r requirements-postgres.txt
```

Configure:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

For HTTPS deployments:

```text
COOKIE_SECURE=true
SESSION_DAYS=8
```

Missing tables are created automatically during application startup.

---

## Create an Administrator

Run:

```powershell
python -m backend.auth_cli
```

The interactive CLI creates an administrator without storing the password in source code.

---

## Retraining

Run:

```powershell
python -m src.train_model
```

New model versions are stored under:

```text
models/versions/<version>/
```

`models/active.json` points to the active model version.

---

## Testing

Install development dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Run:

```powershell
python -m pytest -q
```

The test suite covers:

- Authentication
- Authorization
- CSRF protection
- ML inference
- SHAP reconstruction
- Assessment persistence
- History isolation
- Threshold behavior
- Simulations
- Batch validation
- Model lineage

---

## Dataset

This project uses the **UCI Heart Disease — Cleveland dataset**.

The cleaned dataset contains **297 complete records** from the original 303 Cleveland samples.

The original target is converted into a binary classification problem:

```text
0     → No disease-presence label
1–4   → Disease-presence label
```

This project therefore predicts the dataset's disease-presence label.

It is **not** a future heart-attack prediction system.

Dataset:

https://archive.ics.uci.edu/dataset/45/heart+disease

---

## Deployment

The project is currently deployed using **Render**.

### Live Application

https://explainable-ai-healthcare-system.onrender.com/

Deployment stack:

```text
GitHub
   │
   ▼
Render Web Service
   │
   ├── FastAPI
   ├── Uvicorn
   │
   ▼
Render PostgreSQL
```

The deployed service runs from the `master` branch.

Future changes can be deployed using:

```bash
git add .
git commit -m "Update healthcare application"
git push origin master
```

Render can automatically redeploy the newest GitHub commit.

---

## Important Limitations

- Educational and research project only
- Not clinically validated
- Not medical advice
- Not a substitute for professional healthcare evaluation
- Small dataset
- Internal benchmark results may not generalize to real populations
- SHAP explains model behavior, not causality
- Risk indicators are not diagnoses
- Guidance is educational, not a treatment plan
- Do not submit real sensitive healthcare information to the public demo

---

## References

- [UCI Heart Disease Dataset](https://archive.ics.uci.edu/dataset/45/heart+disease)
- [scikit-learn](https://scikit-learn.org/)
- [SHAP](https://shap.readthedocs.io/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Render](https://render.com/)

---

## Author

**Bokka Lakshmi Anushka**

B.Tech — Computer Science and Business Systems  
SRKR Engineering College  
Class of 2028

GitHub: [@blanushka004](https://github.com/blanushka004)

---

⭐ If you find this project useful, consider starring the repository.
