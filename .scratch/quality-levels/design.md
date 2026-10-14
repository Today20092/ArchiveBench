# Decisions

- Add optional `target_vmafs`; legacy `target_vmaf` remains the default report threshold and single-target fallback. When both are supplied, the default must be a member of the list.
- Setup explicitly offers a comma-separated list, default 80,90,95,97. Targets share cached trials and references. Each target has the existing bounded adaptive search; start from the closest existing measurement and bracket when available.
- Select the smallest/fastest complete tuning candidates per target and variant; deduplicate before fresh validation. Record statuses per target. A failed high target never implies a failed lower target, or vice versa.
- Report shows a target comparison table and selectable thresholds. Higher thresholds always check actual tuning and validation scores. Preserve canonical provenance in archive exports.
- New run directory required; no transplant of old results across changed runner fingerprints. Keep the remaining original time allowance conservative rather than adding an unlimited retry budget.
