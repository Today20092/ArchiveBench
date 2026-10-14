# Run a reusable archive

Inspect `archivebench archive --help` and any installed job commands. The established interface works on different projects by changing its roots:

```powershell
archivebench archive --source SOURCE --output DESTINATION --settings SETTINGS
archivebench archive --source SOURCE --output DESTINATION --settings SETTINGS --execute
```

The first command reviews the list; use the second for an authorized encode. Maintain a separate manifest/output root per project and retain the settings used. Relative subfolders are retained. The runner preserves originals and resumes with matching inputs/settings. Do not change a preset underneath a resumed job. If the installed release provides job files, snapshot settings there and use its explicit exception mechanism.

The legacy runner writes `.archive.mkv`, rejects unsupported streams and discards encodes below its savings threshold. Check timecode, data streams, sidecars and proprietary metadata before replacement. Container or filename changes can affect project relinking. Unsupported cases keep originals until a tested adaptation exists; a converted video playing successfully does not certify an editing project.

Report actual bytes and savings after verification, including retained streams. Verify source/output identity, stream retention and decode checks. Have the user review representative outputs and reopen/reconnect the intended editing project. Record which project/editor and outputs were checked; unsupported editor workflows remain unverified.

Completion: each authorized file has a verified output or an explicit keep-original/failure outcome, and required visual/editor acceptance is recorded separately from automated checks.
