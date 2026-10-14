# Clarify comparisons and unify codec colors

Status: done
Blocked by: 02-chart-quadrants (done)

Scope: shared report template, rendering, bundle, browser checks.

Acceptance: explain the comparison action without pinned-baseline jargon; show kept and selected results with paired size/time bars and exact values; remove the extra evidence disclosure border; use theme-aware codec tokens across plots, cards, selected result and handoff; keep tooltips off focused markers on desktop/mobile, with keyboard access retained.

Required checks: docs/development.md project gates and focused browser/visual checks, using saved results.

## Comments

- User supplied design-taste-frontend. Applied its contextual redesign-preserve protocol: retain Segoe UI, neutral surfaces, existing chart interaction and codec palette; replace redundant framing and inconsistent accents. No framework or dependency change.
- The optional priority triangle is a design discussion, not an approved scoring change. A useful version would express user preferences and rank measured eligible settings with disclosed normalization; it would not pretend size, time and quality are compositional coordinates. Existing scatterplots remain the exact evidence.
- Tooltip cause: local chart collision bounds clamp the large tooltip across its anchor. Use the installed chart library's viewport portal, directional placement and marker-sized offset, then verify no overlap.
- Used TanStack's AI authoring guide and Diagram Design paired-bar guidance. Comparison charts start at zero, use separate units, and distinguish the kept result with an outline from the filled current selection. No added dependency.
- Verified saved real and synthetic reports in dark/light themes and mobile layouts. Offline browser assertions cover comparison charts, codec identity colors and tooltip/marker separation across both scatterplots at narrow widths.
- Passed: 30 pytest tests on Python 3.11, Ruff format/check, ty, 13 report math tests, 2 playback tests, offline browser check, native-still check, JS build, package build and git diff check. Bundle is 162.2 kB minified (previously 142.2 kB). Canonical results unchanged; no new benchmark.
