# Focus the footage review

Status: done

User requested work on the repeated footage comparison area. The main native-still original/encoded pair remains visible. Controls now use an evenly spaced four-column grid, two columns on mobile, with live values for moment, zoom and crop coordinates. Image labels, gaps and edges are consistent. First-frame previews and the divider remain accessible inside a collapsed disclosure, avoiding three competing image views.

Preserved normalized crop math, native assets, image loading errors, unavailable-evidence messaging, seek synchronization and review/export behavior. Tests cover crop outputs, collapsed fallback previews, actual saved still loading and responsive layout. Browser, native-still, math, playback, Ruff, ty and package checks passed; saved reports regenerated without a benchmark.
