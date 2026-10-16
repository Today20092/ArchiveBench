param(
    [string]$PresetDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'ArchiveBench Presets'),
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'ArchiveBench\SendTo'),
    [string]$SendToDirectory = ([Environment]::GetFolderPath('SendTo')),
    [switch]$Legacy,
    [string]$TuiExecutable,
    [ValidateSet('wezterm', 'conhost')][string]$Terminal = 'conhost'
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
    if (-not $Legacy) {
        if (-not $TuiExecutable) { $TuiExecutable = (Get-Command archivebench-tui -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source }
        $TuiExecutable = (Get-Item -LiteralPath $TuiExecutable -ErrorAction Stop).FullName
        if ($TuiExecutable.Contains('"')) { throw 'Invalid TUI executable path.' }
    }
    New-Item -ItemType Directory -Path $presetRoot, $InstallDirectory, $SendToDirectory -Force | Out-Null
    $installedScript = Join-Path ([IO.Path]::GetFullPath($InstallDirectory)) 'archivebench-send-to.ps1'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'archivebench-send-to.ps1') -Destination $installedScript -Force
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $SendToDirectory 'Archive footage (terminal).lnk'))
    $shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\conhost.exe'
    $consoleCommand = '"' + (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') + '" '
    $shortcut.Arguments = $consoleCommand + '-NoProfile -NoExit -File "' + $installedScript + '" -PresetDirectory "' + $presetRoot + '"'
    $shortcut.WorkingDirectory = $InstallDirectory
    $shortcut.Description = 'Choose an archive preset and archive or resume one folder; originals are kept.'
    $shortcut.Save()
    $desktopScript = Join-Path ([IO.Path]::GetFullPath($InstallDirectory)) 'archivebench-desktop.ps1'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'archivebench-desktop.ps1') -Destination $desktopScript -Force
    $desktop = $shell.CreateShortcut((Join-Path $SendToDirectory 'Archive footage.lnk'))
    $desktop.TargetPath = $shortcut.TargetPath
    $desktop.Arguments = $consoleCommand + '-NoProfile -STA -NoExit -File "' + $desktopScript + '" -PresetDirectory "' + $presetRoot + '" -Root'
    $desktop.WorkingDirectory = $InstallDirectory
    $desktop.Description = 'Archive selected folders, clips, or a mixture; add sources in the window.'
    $desktop.Save()
    if (-not $Legacy) {
        $wezterm = $null
        if ($Terminal -eq 'wezterm') {
            $wezterm = (Get-Command wezterm-gui.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
            if (-not $wezterm -and (Test-Path -LiteralPath "$env:ProgramFiles\WezTerm\wezterm-gui.exe")) { $wezterm = "$env:ProgramFiles\WezTerm\wezterm-gui.exe" }
            if ($Terminal -eq 'wezterm' -and -not $wezterm) { throw 'WezTerm is not installed.' }
        }
        foreach ($archiveShortcut in @($shortcut, $desktop)) {
            $archiveShortcut.Arguments = '"' + $TuiExecutable + '" --fit-window --preset-directory "' + $presetRoot + '"'
            if ($wezterm) {
                $archiveShortcut.TargetPath = $wezterm
                $archiveShortcut.Arguments = 'start --always-new-process -- "' + $TuiExecutable + '" --preset-directory "' + $presetRoot + '"'
            }
            $archiveShortcut.Description = 'ArchiveBench TUI: review sources, presets, preflight, encode and resume.'
            $archiveShortcut.Save()
        }
    }
    $cleanup = $shell.CreateShortcut((Join-Path $SendToDirectory 'Review originals for deletion.lnk'))
    $cleanup.TargetPath = Join-Path $env:SystemRoot 'System32\conhost.exe'
    $cleanup.Arguments = $consoleCommand + '-NoProfile -STA -NoExit -File "' + $desktopScript + '" -PresetDirectory "' + $presetRoot + '" -Cleanup -Root'
    $cleanup.WorkingDirectory = $InstallDirectory
    $cleanup.Description = 'Review accepted, verified originals before separately confirmed deletion.'
    $cleanup.Save()
    foreach ($oldName in @('ArchiveBench.lnk', 'ArchiveBench Desktop.lnk', 'ArchiveBench Cleanup.lnk')) {
        $oldPath = Join-Path $SendToDirectory $oldName
        if (Test-Path -LiteralPath $oldPath) { Remove-Item -LiteralPath $oldPath }
    }
    Write-Host "Installed archive, terminal and cleanup shortcuts. Presets: $presetRoot"
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
