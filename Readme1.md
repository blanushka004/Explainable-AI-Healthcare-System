# Continue local verification 

The uploaded project was enhanced in place into an authenticated USER/ADMIN ML research workbench. Preserve the working feature set and UI. Read README.md and VALIDATION.md before editing.

## First local checks

1. Confirm Python 3.12 and use a fresh `.venv` with requirements-dev.txt.
2. Run `python -m pytest -q`.
3. Create an initial administrator with `python -m backend.auth_cli`, then start `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`.
4. Browser-test registration, login, USER assessment/history/export/logout, direct admin-route denial, ADMIN diagnostics, and narrow layout. Batch, threshold, global SHAP, and model versions are ADMIN-only.
5. Test narrow/mobile layout and keyboard navigation. This was not browser-verified in the editing environment because the browser URL policy blocked the local application.
6. If PostgreSQL is requested, install requirements-postgres.txt and verify a real PostgreSQL write/read. Never display .env contents or credentials.

## Changes that must remain correct

- Model/preprocessing selection and calibration comparison use training data only.
- Preserve the caveat: the old project already inspected the internal test split.
- Keep SHAP in probability units and verify base + contributions equals output.
- Never reuse test cases as SHAP background or nearest-training references.
- The threshold explorer uses OOF training predictions and must not mutate deployed threshold.
- Simulation never overwrites an original assessment and cannot change age/category fields.
- CSV batches never save individual assessments; invalid rows return clear errors.
- A single save commits legacy prediction and v2 full snapshot atomically.
- Opening history returns the original model version and explanation, not a recomputed result.
- New training publishes versioned artifacts and updates the active pointer last.
- Historical scripts and plots in legacy/v1 are reference material, not active metrics.
- This is a local authenticated research demo, not a clinical system. Do not deploy publicly without a deployment security review.

Fix reproducible defects, run the relevant checks, and report changed files, cause, verified behavior, and remaining limitations. Do not claim browser or PostgreSQL checks passed without executing them. Do not add synthetic training rows to inflate performance, optimize repeatedly against the internal test set, or promise diagnostic accuracy.
