# Validation report

Validation date: 2026-09-09. Active artifact: `20260908T165602Z-02d58a0b`.

## Executed successfully

- Complete current suite: **43 passed, 0 failed, 0 errors, 0 skipped**, exit code 0, using the project `.venv`.
- Authoritative fresh JUnit report: `verification-authoritative-junit.xml`; captured stdout: `verification-authoritative-stdout.txt`; captured stderr: `verification-authoritative-stderr.txt`; captured exit code: `verification-authoritative-exit.txt`.
- The suite includes 10 authenticated security tests covering anonymous 401s, all admin-route 403s, admin evaluation access, ownership isolation, ownerless records, restricted user responses, CSRF reload stability, expiry, inactive accounts, logout revocation, and ML persistence/rollback regression coverage.
- Python compilation and `node --check frontend/script.js` passed for the final touched backend/frontend files. Pylance was not available for a current-revision diagnostic run.
- Current-revision browser automation was not available because no browser-control tool was attached. No visual assertion is claimed for this revision; see the remaining local check below.

- Full `python -m src.train_model` run: trained all candidates, performed training CV selection and nested calibration comparison, computed evaluation, and saved the active bundle.
- FastAPI TestClient integration suite: **25 passed in 8.72 seconds** on the final run.
- Coverage: feature codes, numeric validation, booleans, missing/extra/invalid inputs; real model prediction; real SHAP; full stored explanation retrieval; train/test ID separation and training-only background; recomputed report metrics; OOF threshold behavior; immutable simulation fields/no writes; mixed-validity CSV; limits and encoding; batch/individual consistency; support flags; similar training cases; global SHAP; history filters; version metadata; atomic rollback of both tables on commit failure.
- JavaScript syntax: `node --check frontend/script.js` passed.
- Uvicorn reached application-startup-complete state in the editing environment.
- Archive CRC/required-file checks are performed when packaging.

## Measured internal test performance (60 records)

| Metric | Value |
| --- | --- |
| Selected model | Logistic Regression |
| Calibration applied | False |
| Accuracy | 0.8167 |
| Precision | 0.8696 |
| Recall | 0.7143 |
| Specificity | 0.9062 |
| F1 | 0.7843 |
| ROC-AUC | 0.9408 |
| Average precision | 0.9286 |
| Brier score | 0.1046 |
| TN / FP / FN / TP | 29 / 3 / 8 / 20 |

These are internal benchmark results, not proof of clinical validity or improvement over every v1 metric. The historical v1 workflow already used this test split for model selection. The v2 selection process does not use test results, but cannot undo that prior exposure.

## Not verified in this environment

- Browser USER/ADMIN assessment flows, saved-history reopening, export/print, and narrow-screen visual layout were not rerun for this revision because browser automation was unavailable. They remain local release checks.
- PostgreSQL authenticated write/read and migration execution were not run against the configured application database. The PostgreSQL 18 Windows service was running, but the process did not have `DATABASE_URL`; `.env` was present and its credentials were intentionally not inspected or exposed. No application database was modified.
- Windows `.bat` execution and a fresh Windows dependency install: launchers provided, but this environment is Linux.
- Public deployment, authentication, clinical validation, and real-world outcomes: outside the scope of this local research application.

Two dependency deprecation warnings were emitted by the test-client stack (httpx compatibility and AnyIO portal alias); they did not fail the suite. They are recorded rather than hidden as passing browser evidence.

Read `CODEX_HANDOFF.md` for the remaining local checks. No generated test database is shipped.

## Compact USER result and recommendation regression update

- Full final automated suite: **43 passed** (`.venv\Scripts\python.exe -m pytest -q`), with three dependency/environment warnings.
- JavaScript syntax (`node --check frontend/script.js`) and Python backend compilation passed.
- Tests cover two distinct personal SHAP snapshots, all 13 factors, reconstruction, saved-history preservation, ownership, user-safe response projection, CSRF reload/missing-cookie recovery, explicit SHAP failure, score-band boundaries, and independent high/no-warning plus low/warning cases.
- New tests verify one complete USER waterfall with no grouped cards, duplicate table, expansion control, or second chart. They also verify saved recommendations are deterministic, separate from SHAP, persisted, reopened unchanged, and stripped of internal rule metadata from USER responses.
- New support-status regression coverage confirms that an older snapshot with an explicit saved boolean check displays the saved check rather than “Check unavailable.”
- Browser automation was unavailable in this environment, so desktop/mobile layout, print layout, and current USER/ADMIN visual workflows require the local manual check in `CODEX_HANDOFF.md`.
- PostgreSQL authenticated write/read was not run. The configured connectivity check can be run with `.venv\Scripts\python.exe -m backend.test_db`; no database was deleted, recreated, or migrated.
