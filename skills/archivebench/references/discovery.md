# Discover footage and tools

Locate `archivebench`, `ffmpeg` and `ffprobe` on PATH (`Get-Command` in PowerShell). Run `archivebench doctor` and retain the build, libvmaf and configured encoder information. Listed GPU encoders still require actual probes on the selected device and format. A timeout is not proof of incompatibility.

If ArchiveBench is missing, explain the package installation route in [the public installation guide](https://github.com/Today20092/ArchiveBench/blob/main/docs/installation.md). Arrange installation only within the user's authorization. FFmpeg is installed separately from [the official download links](https://ffmpeg.org/download.html); use a build containing libvmaf and the intended encoders. If installation cannot proceed, provide these manual steps and stop dependent operations. No API key is required. Node is only needed to rebuild the report.

Use `archivebench scan SOURCE` to list eligible media, then inspect agreed sources with ffprobe. Establish duration, dimensions, frame rate, bit depth, chroma, stream layout, timecode/metadata needs and scratch space. HDR, interlaced and variable-frame-rate input may be unsupported; preserve unsupported footage. Review motion, fine texture and dark/noisy scenes. Do not infer grading intent from a filename.

Completion: exact selected sources and limits are known. A single clip's evidence remains scoped to that clip; wider camera or project claims need representative coverage.
