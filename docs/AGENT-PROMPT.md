# Paste into Codex or Claude

Help me use ArchiveBench from this local checkout: [CHECKOUT PATH]. Read AGENTS.md and docs/agent-workflow.md, then inspect the installed tools.

My footage is in [SOURCE FOLDER OR CLIPS]. I want [COMPACT / EDITING] archives. My benchmark budget is [MINUTES], and scratch files should go in [OUTPUT FOLDER / DRIVE]. Help me select representative short sections, choose whether to keep source bit depth/chroma or convert to 4:2:0/4:2:2, and keep resolution or choose a resolution cap. Show the resulting dimensions. Also help me choose archive audio, subtitle, attachment and metadata retention, defaulting to keeping them. Explain that benchmark measurements are video-only. Review the saved configuration before encoding.

Run the approved benchmark, open the offline HTML report and explain the measured tradeoffs. Recommend exact tested settings meeting my goal, disclose skipped encoders and quality targets not reached, and show projected size/time for 10 minutes, 30 minutes and one hour. Give me comparison clips to review visually before I decide to archive.

If I request full archival encoding, use the exported configuration with the supplied starter runner. Adapt it only where my explicit requirements need changes, keeping restart and verification checks. Keep originals during encoding; use separate cleanup only after I explicitly request it and review the results.
