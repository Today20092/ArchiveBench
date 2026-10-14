# Reuse accepted settings

Read the installed command help for preset operations. Legacy releases use exported archive-settings JSON; preserve it with a human explanation and historical evidence rather than inventing a newer schema. Later commands may provide portable presets and scope checks through the same engine.

A useful preset names the codec and implementation (for example HEVC with NVIDIA or AV1 with a CPU encoder) and retains exact controls, format/retention policy, tested footage characteristics, hardware/build and measured/visual evidence. A codec name alone is insufficient. Keep source/destination paths in each project's job, not in reusable preset data.

Compare the new project's formats, noise/motion/detail and hardware with the tested scope. Recommend a small confirmation comparison when differences matter. Record an explicit user choice to skip it and label historical evidence separately from current-project evidence. A preset is not a guarantee for untested footage.

Quality acceptance and encoding patience are independent. At accepted quality, show the fastest and smallest complete measured choices and explain Pareto tradeoffs where available. Use one project preset with explicit exceptions for stronger settings or keeping originals. Before execution, confirm the installed runner supports those exceptions; otherwise use separate explicit input selections or keep them outside the batch.

Completion: settings, tested scope, current compatibility, user acceptance and exceptions are known. Reusing a preset does not authorize cleanup.
