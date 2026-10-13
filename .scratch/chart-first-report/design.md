# Chart-first report decisions

Status: confirmed by the user; implementation authorized

The user completed the report interview, accepted the recommendations, and then explicitly asked to implement the chart-first report.

- Audience: other technical users choosing archival settings.
- Appearance: restrained technical report; charts lead, with selective color and clear typography.
- Tradeoffs: show named baseline comparisons, not an arbitrary balanced winner. Time is a visible tradeoff with an optional ceiling.
- Qualification: exact settings must be measured on every required sample; use the weakest sample rather than a collection average to gate quality.
- Quality: mean and low-5% scores have independent thresholds. Leave the optional low-5% threshold unset rather than inventing one.
- Interaction: synchronize selection across charts, rankings, table, preview and exports; pin a second configuration.
- Evidence: expand per-sample and scored-frame evidence; clearly identify unavailable data in old runs.
- Review: separate measured checks from self-reported visual review. Offer synchronized local clip playback where the browser supports the codec.
- Export: retain exact archive settings and add a decision summary with measurements, projections, active constraints and remaining review.
- Chart choices: linked scatter plots and horizontal rankings. Defer boxplots until distributions are useful; omit radar normalization, violin smoothing and unmeasured stacked components.

This work is separate from the draft `.scratch/benchmark-comparisons` design. It does not add multi-format runs, held-out validation, source-duration-weighted estimates, companion media generation or full-resolution weak-moment crops. Existing reports project a user-entered duration using the measured sample mix and label that limitation.

The repository's local tracker instructions appeared during implementation. These records capture the already confirmed scope without changing the other design's readiness.
