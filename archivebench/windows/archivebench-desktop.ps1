param([string]$Root, [switch]$Cleanup, [string]$PresetDirectory)
$ErrorActionPreference = 'Stop'
try {
    Start-Transcript -Path (Join-Path $PSScriptRoot 'desktop-last-launch.log') -Force -ErrorAction SilentlyContinue | Out-Null
    if (-not $Root) { throw 'Choose at least one folder or video file (cleanup requires exactly one folder).' }
    $command = Get-Command archivebench-desktop -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $arguments = @('--root', $Root) + $args
    if ($PresetDirectory) { $arguments += @('--preset-directory', $PresetDirectory) }
    if ($Cleanup) { $arguments += '--cleanup' }
    & $command.Source @arguments
    if ($LASTEXITCODE -ne 0) { throw "ArchiveBench stopped with exit code $LASTEXITCODE" }
} catch {
    Write-Error $_ -ErrorAction Continue
    # Keep the -NoExit Explorer console open so the error remains readable.
    $global:LASTEXITCODE = 1
} finally {
    Stop-Transcript -ErrorAction SilentlyContinue | Out-Null
}
