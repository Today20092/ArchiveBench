# Decisions

The user's instruction to change the tool and current setup to one encode is confirmation of this scope. No further design interview is needed.

- Default to one repeat for both modes; allow any positive integer explicitly.
- Reject booleans, fractions, strings, null and nonpositive counts in JSON.
- Retain median timing aggregation; a one-element median is the single measurement.
- Print repeat count and distinguish full measured encodes from screening, pilots, scoring and separate quality attempts.
- Keep VMAF 97 for the existing experiment. It was the agent's proposed target, not a mandatory tool default.
- Preserve the interrupted run separately. Its last canonical status may still say running because the process was terminated; record interruption outside canonical evidence.
- Restart within the remaining original allowance rather than granting another 12 hours.
