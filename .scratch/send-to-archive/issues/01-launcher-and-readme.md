# Presets, everyday archiving and Windows Send to

Status: done
Readiness: ready-for-agent
Blocked by: none

Scope and acceptance: ../spec.md. Update README and existing guides; add a packaged optional per-user installer/launcher delegating to job create/inspect/run. Prove selection, cancellation, snapshot mismatch refusal, isolated shortcut installation, synthetic archive/resume and preserved sources. No automatic cleanup or benchmark.

Checks: Python 3.11 pytest, Ruff format/check, ty, report math and package build; PowerShell parser/isolated install/launcher tests; README links. No report source changes expected.

## Comments

User explicitly requested this workflow clarification and optional right-click launcher. Working in an isolated checkout; active camera runner remains installed at its existing revision.

Implemented two-stage README, future-folder example, file-level resume and linked Windows guide. Packaged installer creates a durable per-user PowerShell shortcut/launcher; selection and execution delegate to the existing CLI. Cancel, multiple-folder rejection, changed-preset refusal, actual synthetic encode/resume and preserved source hashes pass. Paths with spaces, ampersands and percent characters are covered. Errors remain visible; no benchmark or cleanup operation is launched.

Python 3.11 full suite: 79 passed in 153.56s; Ruff format/check, ty, 16 report math tests, wheel/sdist and isolated installed helper help passed. Both PowerShell resources were verified inside the wheel. All 46 affected local documentation links resolve; whitespace checks pass. Report source and existing diagram assets are unchanged, so no report rebuild/new synthetic benchmark is needed. The actual Explorer menu click and README desktop/mobile rendering remain human smoke checks. No personal footage or global benchmark runner was changed by these checks.
