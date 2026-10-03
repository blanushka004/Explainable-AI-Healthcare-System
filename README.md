# Clarity Â· Explainable AI Healthcare Workbench

An ML-focused cardiovascular assessment research project with FastAPI, scikit-learn, SHAP, SQLAlchemy, and an offline-capable HTML/CSS/JavaScript interface. The application estimates the UCI Cleveland disease-presence label from 13 recorded features and makes model behavior inspectable.

**Educational research prototype. Not a medical diagnosis, disease-severity model, future heart-attack forecast, or clinically validated decision tool.** Authentication is required for assessments and history. Use demonstration or anonymized research records, and do not expose the server publicly.

## Accounts and workspaces

Registration creates USER accounts only. Users can submit assessments and access only their own saved records; model metrics, dataset analysis, batch tools, threshold exploration, global SHAP, versions, and admin API documentation require an ADMIN account. Anonymous requests receive 401 and authenticated users receive 403 for admin APIs. Sessions use HttpOnly database-backed cookies, hashed session tokens, Argon2id password hashes, explicit expiry, logout revocation, and CSRF protection for state-changing requests.

Create the first administrator locally with an interactive prompt. The command never prints or stores the password in source:

```powershell
.venv\Scripts\python.exe -m backend.auth_cli
```

## Run on Windows (recommended)

1. Extract the ZIP into a new folder, for example `C:\Projects\healthcare-enhanced`. Do not overwrite your original environment or database.
2. Install Python 3.12 if needed. Run `py -3.12 --version` in a terminal to check.
3. Double-click **setup.bat** once to create `.venv` and install dependencies. An internet connection is required for installation.
4. Double-click **start.bat**.
5. Open **http://127.0.0.1:8000** after the server says it is ready. Keep the terminal open. Press Ctrl+C to stop.

The trained model bundle is included. No retraining, API key, Node.js, frontend build, or PostgreSQL installation is required for the first run. Initial SHAP computation can take several seconds while its numerical code initializes.

The default SQLite database (`healthcare.db`) is created on first startup. Open the application through FastAPI; do not double-click `frontend/index.html` or run it through a separate Live Server.

Startup applies an additive schema migration. It creates `users` and `session_tokens`, and adds nullable indexed `user_id` columns to `predictions` and `assessments_v2`. Existing ownerless records are preserved and are not assigned to the first user or administrator. They remain inaccessible through ordinary history routes.

### Terminal setup (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

No virtual-environment activation is necessary, so PowerShell execution-policy settings need not change.

### macOS / Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Implemented features

| Area | Implementation |
| --- | --- |
| Training | Fixed stratified internal holdout, training-only 5-fold CV selection, numeric scaling, categorical one-hot encoding, and exact-row deduplication before splitting |
| Calibration | Nested out-of-fold sigmoid calibration comparison; calibrated output is selected only if OOF Brier improves |
| Evaluation | Accuracy, precision, recall, specificity, F1, ROC-AUC, average precision, Brier, ROC/PR/calibration curves, and bootstrap intervals |
| Error analysis | Inspect each test false negative/false positive and load its inputs into the form |
| Threshold exploration | Live metrics from training OOF predictions; changing the slider does not change deployed inference |
| Explainability | Probability-space permutation SHAP, complete 13-feature waterfall, reference prediction, reconstruction check, global mean absolute SHAP |
| Model disagreement | Individual predictions and probability spread across three candidate pipelines; agreement is not called confidence |
| Input support | Training range checks and nearest-reference distance compared with a training leave-self-out distance threshold |
| Similar references | Three anonymized training examples with recorded labels, never held-out examples |
| What-if analysis | Hypothetical measurement changes with immutable age/categories, output delta, and no history writes |
| Batch | UTF-8 CSV validation, 1 MB / 250-row cap, per-row errors, result CSV export, no database writes |
| Persistence | Full original inputs, explanation, score, model version and timestamp saved atomically; filtering and pagination |
| Exports | Assessment JSON, evaluation JSON, batch CSV, and browser print / Save as PDF |
| Reproducibility | Versioned model bundles, dataset SHA-256, split IDs, metadata, environment versions, training background |
| UI | Five responsive tabs with no external JavaScript/CSS/CDN dependency |

## ML methodology and honest interpretation

The cleaned CSV has 297 complete-case records from the original 303 Cleveland records. The target maps original values 1â€“4 to 1 and leaves 0 as 0. This is disease-presence classification, not longitudinal outcome prediction.

The training script uses 237 training and 60 internal test records (seed 42). It fits preprocessing within each validation fold, selects the highest mean training CV ROC-AUC, and compares calibration using nested OOF predictions. The holdout is not used in these selection steps. **The historical v1 project had already inspected this same split, so these are internal benchmark results, not a new independent external validation.** Do not repeatedly tune to improve this test score.

The packaged active model is Logistic Regression without calibration. Re-run the script to obtain the full recorded metrics. `models/versions/<version>/evaluation.json` is the authoritative report. Historical v1 plots and scores are archived under `legacy/v1` and must not be reported as current results.

The classification threshold is 0.5. LOW/MEDIUM/HIGH display bands use 0.30 and 0.70 and are explicitly exploratory. The â‰¥90% OOF recall threshold shown in the explorer is a demonstration, not a validated clinical operating point.

SHAP uses 32 fixed training reference rows and five permutation cycles in probability space. Values are approximate and may vary slightly with explainer call order. The reconstruction check ensures that reference plus contributions equals the model output. Displayed contributions are percentage points, not log-odds or causal treatment effects. Global SHAP uses 24 fixed training cases; global permutation importance uses the internal test set for post-hoc interpretation only.

Subgroup results are exploratory, with small sample counts. Bootstrap intervals represent resampling of this internal test set; they do not account for all sources of selection bias, population shift, or clinical uncertainty. Distance flags and candidate agreement do not establish prediction reliability.

## PostgreSQL (optional; existing project compatibility)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-postgres.txt
Copy-Item .env.example .env
```

Create the database in PostgreSQL, then set `DATABASE_URL` in `.env` using your own credentials:

```text
DATABASE_URL=postgresql+psycopg://postgres:YOUR_URL_ENCODED_PASSWORD@localhost:5432/healthcare_db
```

Restart the server. It creates missing tables automatically. This additive change retains the existing `predictions` table and creates `assessments_v2` for complete new records. `/history` and `/predictions/{id}` still expose old records. Old records do not have v2 SHAP snapshots, so they are not backfilled or misrepresented in the new archive.

The SQLite history and PostgreSQL history are separate stores. Switching the database URL does not migrate data. Back up an existing database before using it. No credentials are bundled. PostgreSQL was not integration-tested in the editing environment.

## Retraining and model artifacts

```powershell
.\.venv\Scripts\python.exe -m src.train_model
```

Or double-click `retrain.bat`. Restart the API afterward. Training writes a new `models/versions/<version>/bundle.joblib` and `evaluation.json`, then updates `models/active.json` only after these files are written. Previous versions are retained. Comparable metrics require the same dataset and split seed; inspecting many versions against a holdout can itself overfit that holdout.

The bundle contains every candidate, the active pipeline, training reference rows, SHAP background, OOF predictions, split identifiers and report. `best_model.pkl` is retained for simple compatibility. The API loads the versioned bundle, not a separate scaler. Only load trusted model files: joblib/pickle artifacts execute code during deserialization. Keep the pinned scikit-learn version, or retrain if you intentionally change it.

Standalone commands:

```powershell
.\.venv\Scripts\python.exe -m src.predict examples/patient.json
.\.venv\Scripts\python.exe -m src.explain examples/patient.json
.\.venv\Scripts\python.exe -m backend.test_db
```

## Testing

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover schema rejection, inference, SHAP reconstruction, full-result persistence, training-reference separation, threshold monotonicity, unchanged deployment threshold, simulation invariants, CSV limits, batch/individual agreement, history filters, and model lineage. Test endpoint writes use an isolated in-memory database. Application startup still initializes the configured database, so run tests with the default disposable local database rather than a production database.

See `VALIDATION.md` for measured results and environment limitations.

## Structure

- `src/train_model.py`: training, selection, calibration, version publication.
- `src/features.py`: shared feature names, units, categories and display contract.
- `src/metrics.py`: evaluation, curves and bootstrap intervals.
- `backend/engine.py`: active-model inference, SHAP, similarity and support checks.
- `backend/contracts.py`: API validation and simulation payloads.
- `backend/main.py`: same-origin frontend, inference, batch, evaluation and history endpoints.
- `backend/models.py`: legacy predictions plus full assessment snapshots.
- `frontend/`: five-tab interface, SVG evaluation charts and SHAP waterfall.
- `models/versions/`: reproducible active and future training artifacts.
- `tests/`: meaningful behavior tests.
- `examples/`: fictitious demonstration inputs and CSV examples.
- `legacy/v1/`: superseded scripts, models and reports, retained for reference only.

## Troubleshooting

- **Python not found:** install CPython 3.12 with the Python launcher; verify `py -3.12 --version`.
- **Dependency installation fails:** copy the final error lines for Codex; do not mix this `.venv` with the original project's environment.
- **Port 8000 in use:** add `--port 8001` to the startup command and open `http://127.0.0.1:8001`. The frontend uses relative API URLs.
- **Model unavailable / incompatible artifact:** install pinned requirements, run training, and restart.
- **Database failure:** check `.env` and run the connectivity command. Remove an unintended `DATABASE_URL` environment variable to return to SQLite.
- **Slow first explanation:** the first SHAP call initializes numerical code. Subsequent explanations are cached (256 unique inputs).
- **Explanation unavailable:** inspect server logs; predictions may still succeed and explicitly indicate missing explanations.
- **PowerShell blocks activation:** use the explicit `.venv\Scripts\python.exe` commands above; activation is unnecessary.
- **Blank page from a file URL:** use the FastAPI URL, not the HTML file directly.

## Sources

- Dataset: https://archive.ics.uci.edu/dataset/45/heart+disease
- Cross-validation: https://scikit-learn.org/stable/modules/cross_validation.html
- Probability calibration: https://scikit-learn.org/stable/modules/calibration.html
- SHAP permutation explainer: https://shap.readthedocs.io/en/latest/generated/shap.PermutationExplainer.html

## Personal explanations, recommendations, and CSRF recovery

Each saved assessment retains its original validated measurements, score, probability-space SHAP snapshot, and the educational guidance displayed when it was saved. The owner can reopen that exact snapshot without recomputing it against a newer model. USER API responses contain only personal values, signed contributions, the saved recommendation cards, and safe input-check status; model versions, SHAP settings, rule identifiers, training references, candidate comparisons, and evaluation data remain ADMIN-only.

The USER result is deliberately compact: **Your heart-health assessment** with an **Assessment score** and **Risk indicator**, one **What influenced your assessment?** waterfall, **General guidance, not a treatment plan**, collapsed **Your measurements**, and one educational-use statement. The single always-visible waterfall shows the starting score, all 13 saved measurement contributions with their recorded values and signed percentage points, and the final assessment score. It has a raised/lowered legend and no duplicate factor cards, table, chart, or expansion control. ADMIN retains its technical waterfall and reconstruction detail.

Recommendations are a separate deterministic rule layer (`guidance-2026-09-09-v1`), not a SHAP interpretation and not a score-band action. Every new result receives a report-review card. A blood-pressure card is added for the recorded systolic value of 130 mm Hg or higher; a serum-cholesterol card is added for 200 mg/dL or higher; the dataset fasting-blood-sugar flag may be reviewed only as a dataset entry, never as a diabetes assessment. At most three cards are saved. They ask the user to discuss recorded report values with a healthcare professional; they do not diagnose, prescribe medication, advise vigorous exercise, or assign urgency. Historical snapshots without the new cards state that recommendations were not stored rather than generating replacement advice.

The source thresholds are limited to educational prompts. The blood-pressure prompt follows the American Heart Association’s 2025 category framework, but the form contains only one systolic measurement and cannot diagnose hypertension. The cholesterol prompt uses the NHLBI total-cholesterol reference bands, while this dataset’s single serum-cholesterol field is not a complete lipid panel. The fasting-blood-sugar card reflects MedlinePlus guidance that blood glucose testing depends on the type and conditions of testing; it does not establish diabetes. Sources: [AHA blood-pressure guidance](https://professional.heart.org/en/science-news/2025-high-blood-pressure-guideline/top-things-to-know), [NHLBI cholesterol guide](https://www.nhlbi.nih.gov/files/docs/public/heart/chol_tlc.pdf), and [MedlinePlus fasting blood-test guidance](https://medlineplus.gov/lab-tests/fasting-for-a-blood-test/).

The independent **Measurement check** appears inside **Your measurements**. It checks inputs, not disease status: it reports either “No unusual inputs detected,” “Check entered measurements” with an accurate user-safe reason, or “Check unavailable.” New saved results carry an explicit available status. Older snapshots with an explicit saved boolean check remain available even if they predate the status field; absent support data stays unavailable.

CSRF uses a readable same-site token paired with an HttpOnly session cookie. `/api/auth/csrf` preserves a valid token on reload; if the readable CSRF cookie is missing or stale while a session remains valid, it updates the server-side hash and cookie together. The frontend refreshes a rejected token but never replays a state-changing assessment automatically, preventing duplicate records. If the session has actually expired, the user is returned to sign-in with “Your session needs refreshing. Sign in again.”
