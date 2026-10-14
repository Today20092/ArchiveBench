# Explicit comparison selectors

Status: done

Follow-up: replaced visible Result A/B labels with actual codec/settings names in selectors, bar labels, difference summary and accessible chart descriptions. Table shortcut wording uses Compare. Internal selector IDs and export state are unchanged. Offline checks assert that comparison copy includes the setting name and contains no Result A/B wording.

User approved replacing the keep-then-select flow with Result A and Result B, preserving the accepted layout. Result A is independently selectable; Result B is explicitly labeled as the current selection and stays synchronized with charts, cards and handoff. Clearing comparison resets A. Table shortcuts explicitly set A. Existing comparison/export state remains compatible.

The comparison reports B relative to A for file size, encoding time and quality in VMAF points. Bars name codec/settings; different sample coverage still blocks numeric comparison. Both selectors remain available for identical settings, with an explanatory empty state. Keyboard focus survives selection rerendering.

Validation: offline browser checks cover selector changes, identical settings, numeric quality differences, sample mismatch, themes, mobile layouts and existing handoff/export behavior. Report math, playback, native-still, Ruff, ty and package build passed. Saved reports regenerated without running benchmarks.
