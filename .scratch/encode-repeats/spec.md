# Explicit encode repeats

Status: approved for implementation

The user requested configurable timing repeats and one measured encode per setting for the current benchmark. Add `encode_repeats`, a positive integer defaulting to 1 independently of quick/thorough mode. Setup must ask for it and startup output must disclose it. Apply it to tuning and fresh validation. Explain that repeats measure timing variability, while tuning attempts try different compression settings. Preserve scoring, compatibility probes, validation and resume identity checks.

The existing run is stopped with completed evidence preserved. Restart the requested experiment with one repeat in a fresh output folder after checks. Keep its quality target and footage unchanged. Do not transplant cached trials across changed runner/configuration fingerprints.

Scope: configuration validation and runner, setup, regression tests, glossary and benchmark/intake documentation, and the local experiment configuration. No new dependencies, report redesign or codec changes.
