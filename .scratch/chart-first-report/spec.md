# Chart-first report

Status: confirmed; implemented and verified

Make the offline report primarily a chart-based decision tool. Put storage/time and quality/storage scatter plots before metrics and prose. Preserve the existing palette, light/dark modes, offline bundle, source-path redaction and archive-settings compatibility.

Selection and pinning must work across charts, zero-based horizontal rankings and sortable tables. State size/time comparisons against a named baseline and suppress comparisons with unequal sample coverage. Exact settings qualify only with complete planned-sample coverage and passing per-sample mean and optional low-5% thresholds. A projected time ceiling is optional. Preserve a separate conclusion reconstructed from canonical results and the saved target.

Expandable evidence shows per-sample means and low-5% scores, first-frame previews, optional scored-frame timelines, and synchronized playback of matching sample clips explicitly chosen locally. Record review status only for the inspected measured trial, clear loaded media on trial changes, and disclose unsupported codecs. Save scored-frame timestamps in future benchmark results; old runs show unavailable timelines.

Exports include unchanged version-2 archive settings and a separate decision JSON with coverage, active constraints, measurements, projections, baseline and outstanding visual review. No new dependencies, automatic encoding of user footage, deletion, or changes to archive safeguards.

Required checks: report math tests; bundled-JS build; offline browser checks including interaction, empty/partial evidence, hostile labels, exports, light/dark and narrow layouts; real synthetic playback; pytest, Ruff format/check and ty. Rebuild the requested demo from canonical results without modifying those results.
