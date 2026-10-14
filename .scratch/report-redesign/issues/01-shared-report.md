# Redesign shared report

Status: done
Blocked by: none

Scope: archivebench/assets/report.html and report/app.js. Rebuild archivebench/assets/report.js. Update report/browser-check.mjs for the changed structure and requested behaviors.

Acceptance: all six improvements and invariants in ../spec.md. Existing stills, playback, exports, sorting, filtering and evidence remain usable.

Required checks: docs/development.md checks, saved synthetic report browser/stills checks, real report regeneration with unchanged canonical JSON, desktop/mobile dark/light inspection.

## Comments

- Read the handoff, glossary, tracker, development instructions and earlier accepted report specifications. Graph discovery identified render, drawChart, selection, event wiring and generation as the affected path. Math, stills and playback remain shared unchanged dependencies.
- Implemented shared chart cues, circle/hexagon states, structured tooltips, exact source-duration estimates with readable labels, plain choice cards, a collapsed sortable table, and a final selected-settings handoff. The user's follow-up changed the main flow to charts, choice, and agent handoff.
- Corrected a presentation mismatch: a failing fresh-footage low-5% score now displays the same failure already enforced by eligibility math. Added a browser regression case; recommendation math remains unchanged.
- Passed 30 pytest cases on Python 3.11, Ruff format/check, ty, 13 report math tests, 2 playback tests, browser and native-still checks, bundle build and package build.
- Browser coverage includes keyboard selection, marker layers, tooltips at narrow widths, exact custom/source duration, recommendation card selection, collapsed table/sorting, copy fallback, settings exports, fresh-validation failures, hostile sample/variant labels and zero network requests.
- Regenerated a saved synthetic report and the real reference report through the normal report command. Inspected desktop/mobile and dark/light renderings. Both charts retain all three measured codec families. The canonical real results SHA-256 is unchanged.
- Reused saved synthetic results instead of running create_demo.py, as requested in the handoff. No benchmark, archive encode, commit or push was performed. Guided-benchmark edits remain separate.
- The first context-mode check batch timed out during pytest, and its Node commands later failed due to that tool's executable path. Re-ran the affected checks through the normal shell; all completed successfully.
