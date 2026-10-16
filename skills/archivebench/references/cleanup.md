# Separately remove verified originals

Cleanup permanently deletes originals. It requires an explicit cleanup request covering the selected files; benchmarking, archiving and a quality score are insufficient authorization.

Wait for processing to end. Establish current identity-bound replacement acceptance for the specific verified outputs: actual visual/editor attestations or explicit quality-tradeoff acceptance without inspection. Changed source/output files invalidate that acceptance. Use installed job/review operations when present. Legacy `--reviewed` is a caller assertion, not an automated editing check; explain the missing evidence rather than treating the flag as proof.

For new jobs, `archivebench acceptance inspect --output DESTINATION` must report current replacement acceptance against the verified replacements. `--reviewed` cannot bypass missing job acceptance. Inspect the mapping, all unmet requirements, and keep-original exceptions before cleanup; record only the user's actual review or explicit quality-tradeoff decision; never invent inspection.

```powershell
archivebench cleanup --output DESTINATION
```

Review the dry-run list and all keep-original exceptions. Only for the authorized verified selection, with the required acceptance, execute the installed cleanup interface. The legacy interface is `archivebench cleanup --output DESTINATION --execute --reviewed`.

Preserve hash, path, savings, stream and full-decode checks. A failed check keeps the original; resolve the cause before another authorized attempt. Never bypass a guard or silently broaden the selection.

Completion: cleanup affects only the requested verified replacements and reports deleted, retained and failed files. Keep-original exceptions remain intact.
