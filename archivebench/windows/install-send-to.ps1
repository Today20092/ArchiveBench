param(
    [string]$PresetDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'ArchiveBench Presets'),
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'ArchiveBench\SendTo'),
    [string]$SendToDirectory = ([Environment]::GetFolderPath('SendTo'))
)
$ErrorActionPreference = 'Stop'
try {
    if (-not (Get-Command archivebench -CommandType Application -ErrorAction SilentlyContinue)) {
        throw 'Install the archivebench command on PATH before installing Send to.'
    }
    $presetRoot = [IO.Path]::GetFullPath($PresetDirectory)
    if ($presetRoot.Contains('"') -or $presetRoot.Contains("`n") -or $presetRoot.Contains("`r")) {
        throw 'Choose a valid Windows preset directory.'
    }
    New-Item -ItemType Directory -Path $presetRoot, $InstallDirectory, $SendToDirectory -Force | Out-Null
    $installedScript = Join-Path ([IO.Path]::GetFullPath($InstallDirectory)) 'archivebench-send-to.ps1'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'archivebench-send-to.ps1') -Destination $installedScript -Force
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $SendToDirectory 'ArchiveBench.lnk'))
    $shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $shortcut.Arguments = '-NoProfile -File "' + $installedScript + '" -PresetDirectory "' + $presetRoot + '"'
    $shortcut.WorkingDirectory = $InstallDirectory
    $shortcut.Description = 'Choose an archive preset and archive or resume one folder; originals are kept.'
    $shortcut.Save()
    Write-Host "Installed Send to > ArchiveBench. Save your approved JSON presets in: $presetRoot"
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
