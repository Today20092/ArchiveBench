# Timestamp shortcuts show saved frames

Status: done

Cause: timestamp shortcuts called video seek without updating the still viewer. renderStills now returns a controller that selects a matching saved timestamp and updates both images, caption and slider. Shared seek calls it alongside paired video seek and marks the active shortcut. No exact saved frame produces an explicit message rather than substituting a different moment. Crop position is retained.

Verified timestamp shortcuts against the saved real report, including exact original/encoded asset paths and slider values. Offline browser, native still, playback, report math, Ruff, ty and build checks passed. Reports regenerated without encoding or changing canonical results.
