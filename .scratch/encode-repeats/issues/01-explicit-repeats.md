# Explicit encode repeats

Status: done
Blocked by: none

## Scope

Add the validated repeat count, setup prompt and startup disclosure; document timing repeats separately from quality attempts; restart the user's setup with one repeat.

## Acceptance criteria

- Missing repeat count means one in either mode.
- Explicit positive integers control actual tuning and validation encode calls and recorded timings.
- Invalid values fail before encoding.
- Setup saves and displays the choice.
- Changed repeat settings cannot reuse an incompatible run cache.
- Original evidence and original videos remain intact; the updated experiment launches in a new folder.

## Required checks

Python 3.11 locked environment, pytest, Ruff format/check, ty, report math tests and package build. No report source changes are planned.

## Comments

The prior benchmark was stopped before editing runner code. Four completed trials remain in its output folder.

Implemented positive-integer `encode_repeats`, default 1 for both modes, setup prompt and startup disclosure. Integration tests count real FFmpeg encode calls for tuning and validation at default 1, explicit 2 and explicit 3, verify resume does not encode again, and reject changed repeat settings on the old run identity. Fixed the test counter to exclude FFprobe verification calls.

Python 3.11 checks passed: 40 pytest tests, Ruff format and lint, ty. All 13 report math tests and two playback tests passed. Package build and git diff whitespace check passed. No report sources changed, so no report rebuild or additional browser/still layout checks were needed.

Validated replacement configuration differs only in one repeat and a 660-minute allowance. Launched the replacement in its own output folder; prior canonical results and source files remain unchanged.
