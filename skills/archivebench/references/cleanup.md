# Separately remove verified originals

Cleanup permanently deletes originals. It requires an explicit cleanup request covering the selected files; benchmarking, archiving and a quality score are insufficient authorization.

Establish user visual acceptance and required editor reopening/relinking for the specific replacements. Changed source/output files invalidate that acceptance. Use installed job/review operations when present. Legacy `--reviewed` is a caller assertion, not an automated editing check; explain the missing evidence rather than treating the flag as proof.

```powershell
archivebench cleanup --output DESTINATION
```

Review the dry-run list and all keep-original exceptions. Only for the authorized verified selection, with the required acceptance, execute the installed cleanup interface. The legacy interface is `archivebench cleanup --output DESTINATION --execute --reviewed`.

Preserve hash, path, savings, stream and full-decode checks. A failed check keeps the original; resolve the cause before another authorized attempt. Never bypass a guard or silently broaden the selection.

Completion: cleanup affects only the requested verified replacements and reports deleted, retained and failed files. Keep-original exceptions remain intact.
