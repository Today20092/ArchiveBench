# Put direction shading inside charts

Status: done
Blocked by: 01-shared-report (done)

Scope: replace the rejected external direction boxes with chart-native quadrant shading in shared sources and rebuild the bundle.

Acceptance: lower-left size/time and upper-left quality/size shading, responsive plot alignment, readable points in both themes, no scale or eligibility changes, compact legend key, no external boxes.

Required checks: project gates in docs/development.md; browser geometry assertions at desktop/mobile sizes, offline selection/tooltips, regenerated saved report and visual inspection.

## Comments

- Used TanStack createMark with final plot bounds, no data channels or interaction candidates. Drawn before point layers. Browser geometry, keyboard selection, tooltip and offline checks pass. Inspected real report in both themes and viewport sizes.
- All required checks passed: 30 Python tests on 3.11, Ruff format/check, ty, 13 report math tests, playback tests, native stills, offline browser checks, bundle and package builds. Regenerated saved synthetic and real reports. No new benchmark or commit.
