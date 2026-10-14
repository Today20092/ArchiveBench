# Everyday archive workflow

Status: approved by user request, 2026-10-14.

Clarify two uses: benchmark representative footage on local hardware, visually choose and save portable presets; reuse those presets to archive unrelated future folders without repeating the benchmark. Explain project-specific snapshots, actual verification/savings and resume by repeating the same job. Preserve current README diagrams, badges, attribution and links.

Add an optional Windows Send to launcher: accept one folder, choose a saved preset, show preflight, explicitly start encoding, reuse an unchanged matching job on repeat launch. Use the existing CLI engine and guards, never benchmark or delete originals. Install a per-user shortcut and a durable copy of the launcher; support spaces/metacharacters without shell interpolation. Ship installer resources with the wheel, require no new dependencies, test isolated shortcut installation and synthetic encode/resume. Do not change the running benchmark's installed tool/config.
