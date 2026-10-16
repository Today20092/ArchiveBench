# Portable skill smoke walkthrough

This walkthrough verifies packaging and local execution on Windows. It does not certify discovery or tool permissions in every skills-compatible client.

## Fresh installation outside a checkout

Build a wheel with `uv build`. Create a temporary Python 3.11 environment with `uv venv --python 3.11 TEMP_ENV`, then install the wheel using `uv pip install --python TEMP_ENV/Scripts/python.exe dist/archivebench-0.2.0-py3-none-any.whl`.

From an unrelated working directory, run:

```powershell
TEMP_ENV/Scripts/archivebench-skill.exe --destination TEMP_AGENT_SKILLS
TEMP_ENV/Scripts/archivebench.exe --help
TEMP_ENV/Scripts/archivebench.exe doctor
```

Inspect `TEMP_AGENT_SKILLS/archivebench/SKILL.md`, `agents/openai.yaml` and each linked local resource. All files must be present; no checkout or private paths may be required. Confirm the frontmatter contains `disable-model-invocation: true` and the Codex policy contains `allow_implicit_invocation: false`. A second install to the same directory must fail while preserving the existing contents. The public installation test exercises this behavior. The release-wheel walkthrough also checks packaging rather than relying on an editable checkout.

Run the installer regression test from a source checkout:

```powershell
uv run --python 3.11 pytest tests/test_skill.py -q
```

The strict Agent Skills reference validator currently rejects the documented Claude Code extension `disable-model-invocation`. This skill includes that extension deliberately to prevent automatic invocation in Claude Code. Use the installer and client checks here to verify the distributed skill. Passing those checks does not establish compatibility with every Agent Skills client.

## Activation and workflow cases

Use these prompts in a Codex discovery test. In Claude Code, replace `$archivebench` with `/archivebench`. Review expected routing before evaluating task outcomes; format validation does not prove invocation behavior.

| Request | Expected skill routing and first useful action |
|---|---|
| $archivebench Compare HEVC and AV1 for my completed wedding project. | Activate; locate tools, inspect source characteristics, propose a bounded experiment. |
| $archivebench Can I reuse my podcast archive preset for this noisy concert? | Activate; inspect preset scope and suggest a short confirmation comparison. |
| $archivebench Archive this completed project; I can leave it encoding overnight. | Activate; treat overnight as patience, review settings and job scope before encoding. |
| $archivebench Delete originals from the archive I just made. | Activate; inspect the finished job, verified identities, replacement acceptance (actual review or explicit quality tradeoff) and separate cleanup authorization. |
| Compare HEVC and AV1 for my completed wedding project. | Do not load the skill automatically; invocation is explicit in this revision. |
| ZIP this folder for email. | Do not activate; this is file packaging. |
| Export a small social-media delivery video. | Do not activate; this is delivery rather than camera-media replacement. |
| Compress these JPEG images. | Do not activate; this is image compression. |

Historical delivery checks, before the explicit-invocation policy change, discovered the packaged skill in Codex CLI 0.154.0 outside the repository and ran two folder jobs through the installed terminal command. Initial model attempts failed on the inherited model; invocation-local selection of the client's advertised default then demonstrated implicit activation, bounded comparisons, preset export and job planning. These checks do not verify the new invocation policy. Scratch permission failures and the baseline timeout remain recorded. See [delivery evidence](delivery-evaluation.md) for exact scope; no other client or universal comparative benefit is claimed.

## Synthetic archive walkthrough

Use temporary generated footage, never personal footage, for this check. Generate a short SDR constant-frame-rate FFV1 clip with FFmpeg, list built-in presets, export a listed starter, create a job with a separate destination, inspect it and execute it using [the terminal workflow](terminal-workflow.md#immediate-use-and-job-outcomes). Confirm the starter has unknown measurements and inspect `archive-summary.html` with its manifest after the run. Rerun the same job and confirm verified files are reused. The job summary tests cover persisted interrupted selection and unfinished outcomes; a completed rerun alone does not demonstrate interruption recovery.

Record a quality-tradeoff acceptance using the synthetic fixture only, then run cleanup without `--execute`. Check that the exact verified original appears in the preview and still exists. This walkthrough requires no deletion. Test actual visual/editor acceptance only when a person performed those checks; synthetic encode success supplies neither review nor real-camera quality evidence. A measured preset from the fixed-comparison demo can use the same job path; its historical measurements remain distinct from current-job verification.
