# Report clarity redesign

Status: accepted problem statement; implementation authorized by the supplied handoff.

Apply the six requested improvements to shared report sources: chart direction cues, a short introduction, plain controls, distinct selection/baseline shapes, structured tooltips, and one sortable result table with a concise selected result. Preserve recommendation math, exports, validation distinctions, and visual review. Existing domain requirements remain in ../benchmark-comparisons/spec.md.

Acceptance: both charts communicate the desirable direction without obscuring measurements; selected and pinned points are distinct without color; duration estimates retain exact source precision; failed/incomplete evidence stays visible; details remain accessible; desktop/mobile and both themes work offline with hostile labels rendered as text.

Checks: docs/development.md plus focused browser assertions, saved-result regeneration, and visual inspection. Reuse saved synthetic and real results; no new benchmark is needed.
