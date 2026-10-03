# Codex handoff

## 2026-09-09 final USER waterfall presentation revision

### Root cause

The secure backend was already calculating, reconstructing, persisting, and owner-filtering real personal SHAP snapshots. The defect was presentation drift: the USER page accumulated competing bar, table, and waterfall displays. The required current presentation is one complete waterfall, not a return to the historical unsecured application.

### Implemented behavior

- USER results show the assessment summary once, then exactly one always-visible waterfall titled **What influenced your assessment?**.
- The waterfall contains the starting score, every one of the 13 actual saved personal contributions, each readable measurement label and recorded value, signed percentage-point contribution, a raised/lowered legend, and the final assessment score.
- USER has no grouped contribution cards, duplicate contribution table, second chart, “Show all” control, or factor expansion button. ADMIN keeps its technical waterfall and reconstruction details.
- Recommendations remain directly below the visualization, use the separately versioned deterministic measurement rules, and reopen from the saved snapshot unchanged.
- The submitted form remains available above the result. The result has one **Download report** menu containing the existing JSON and print/PDF options; history and sign-out remain in navigation.
- The measurement check stays secondary under collapsed measurements and remains independent of the score category. Older snapshots with an explicit boolean check are handled as available; truly missing checks are not fabricated.
- Authentication, CSRF, ownership, model selection, threshold, probabilities, SHAP reconstruction, and history persistence were not changed.

### Reference inspection

The repository initial frontend revision and current upgraded `frontend/script.js` were inspected before editing. The attached ZIP was not present in the workspace, so it was not imported or used to overwrite the application. The historical `legacy/v1/src/recommendation.py` supplied recommendation-card context only; its unsafe urgency/treatment logic was not restored.

### Verification performed

```powershell
node --check frontend/script.js
.\.venv\Scripts\python.exe -m compileall backend
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **43 passed**, with three existing dependency/environment warnings. Tests cover personal SHAP reconstruction and snapshots, ownership and role protection, CSRF recovery, saved recommendations, measurement-check compatibility, and a USER-renderer contract that requires one complete waterfall and no duplicate explanation display.

### Remaining local checks

Browser automation was not attached in this environment. Manually verify a USER and ADMIN assessment at desktop and narrow widths, the full waterfall, report menu, print layout, saved-history reopening, recommendation cards, logout/account switch, and a HIGH score with “No unusual inputs detected.” PostgreSQL authenticated write/read was not performed. No database was deleted, migrated, committed, or published.
