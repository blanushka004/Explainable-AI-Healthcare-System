# v2 changes

- Replaced test-set model selection with training CV and nested OOF calibration comparison.
- Added appropriate categorical encoding; preserved original Cleveland feature codes.
- Added metrics, bootstrap intervals, test error analysis, threshold exploration, calibration curves and model lineage.
- Implemented consistent probability-space permutation SHAP, complete waterfalls and training-sample global explanations.
- Added candidate disagreement, training-range/distance support flags and training-only similar references.
- Added constrained hypothetical simulations and CSV batch analysis with row errors and download.
- Replaced the single-form interface with a five-tab local workbench served by FastAPI.
- Persisted complete explanation snapshots and model versions in an additive table while retaining legacy history endpoints.
- Removed hardcoded database credentials and frontend API host; SQLite is the default, PostgreSQL remains optional.
- Added Windows setup/start/retrain launchers, exact core dependency pins, tests and a Codex handoff.
- Corrected score language: disease-presence model output, not clinical severity or future-event prediction; corrected thal label to thallium stress-test result.
- Archived superseded models/plots/workflows under legacy/v1. Excluded credentials, environment folders, generated databases and git internals from the delivered ZIP.
