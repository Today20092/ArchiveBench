# Implementation plan

Approved direction: [specification](spec.md). Evidence and decisions: [design record](design.md).

Packaging follows the [Agent Skills standard](https://agentskills.io/specification). The skill invokes the shared CLI; the terminal route remains independent of any agent. Release evaluation must compare agent performance with and without the skill, not only validate its Markdown format.

| Order | Ticket | Depends on | Done when |
|---|---|---|---|
| 1 | [Installable skill](issues/01-installable-skill.md) | None | An agent outside the checkout can follow a truthful installed workflow using existing tools. |
| 2 | [Portable presets](issues/02-portable-presets.md) | None | Exact settings, scope and evidence are reusable through CLI and report, with legacy compatibility. |
| 3 | [Bounded experiments](issues/03-bounded-experiments.md) | 2 | Users see cost/scope before encoding, useful progress and evidence-based expansion. |
| 4 | [Native comparison and decisions](issues/04-native-review.md) | 2 | Matching original/candidate footage opens in a verified viewer and review decisions persist. |
| 5 | [Reusable archive jobs](issues/05-reusable-jobs.md) | 2 | One runner handles separate project folders, preset snapshots, resume and explicit exceptions. |
| 6 | [Editor acceptance and cleanup](issues/06-replacement-acceptance.md) | 4, 5 | A tested reopening path and scoped acceptance gate protect replacement/cleanup. |
| 7 | [Both entry points and release checks](issues/07-delivery.md) | 1–6 | Agent and terminal-only walkthroughs both work on two folders with the same engine. |

All tickets are specified and open; dependencies govern when work may begin. Current camera benchmark operation is not an implementation ticket and is not changed by this plan.

## Validation

Follow `docs/development.md`: Python 3.11 locked environment, pytest, Ruff format/check, ty, report math tests, playback tests and package build. Report changes also require bundled JS rebuild plus offline browser and native-still checks. Test actual native-viewer behavior separately. Exercise installed-package/skill use outside the repository and terminal-only use without an agent.

Use synthetic fixtures for automated tests and a separately reviewed representative camera/editor workflow for replacement acceptance. Synthetic metrics are not camera recommendations. Keep footage, local configs and raw results out of Git.
