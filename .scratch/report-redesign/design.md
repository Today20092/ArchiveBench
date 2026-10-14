# Design decisions

The supplied user handoff is the accepted feedback and asks for implementation without repeating the interview. Copy and shapes are delegated design choices, not claims of separately approved wording.

- Keep the existing offline JavaScript architecture. Shadcn inspection found no React, Tailwind, configuration, or installed components. A framework migration is unnecessary.
- Small circles represent ordinary results; a larger filled circle represents selection; a hollow hexagon represents the pinned baseline; the combined state nests the large circle inside the hexagon. Draw emphasized marks last so overlap cannot hide them. Codec/hardware retains color ownership.
- Shade the preferred quadrant inside each plot, behind measured points: lower left for size/time, upper left for quality/size. The user rejected external explanatory boxes and supplied an Artificial Analysis reference. Screen-space shading expresses direction, never an eligibility cutoff, and does not contribute data or alter scale domains.
- Show source duration as minutes/seconds through a source option. Keep its exact numeric value internally; expose decimal minutes only for custom input.
- Use the chart library's structured tooltip content and native focus/placement behavior.
- Keep one sortable table. Put technical selected-result facts behind disclosure and keep evidence status visible.

No unresolved material design question. Preserve the unrelated guided-benchmark work.

## User clarification during implementation

## Accepted reusable layout

Final acceptance: the user approved the completed comparison selectors and actual codec/settings names as the benchmark tool's default report template. The shared HTML and bundled JavaScript already contain this version; write_report loads these assets for every generated report. No benchmark-specific values are saved as defaults.

The user accepted the current layout as the default for future reports. It is saved in the shared assets/report.html template and generated assets/report.js bundle, sourced from report/app.js. Report generation injects each run's own canonical results; the current benchmark settings and measurements are not template defaults. Preserve this layout as the accepted starting point for subsequent changes.

Comparison follow-up: the user approved an explicit Result A / Result B pair with visible configuration selectors, codec names on bars, and a short size/time/quality difference sentence. Implemented in the existing comparison area; Result B is explicitly the current selection, while Result A stays fixed until changed or cleared. The rest of the accepted layout remains unchanged.

The user explicitly wants the charts to drive a choice, followed by a settings summary to give their agent. Keep all measurements collapsed, explain fully checked choices in plain language, and offer smallest file, fastest encode and highest measured quality. Show codec names rather than encoder implementation names in the main view. Keep exact encoder/settings in the final handoff and exports. The highest-quality card uses the existing recommendation eligibility, never unvalidated points.
