param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)] [string[]]$SourcePath,
    [string]$PresetDirectory,
    [string]$Preset,
    [string]$OutputPath,
    [switch]$InspectOnly,
    [switch]$NoPause
)
$ErrorActionPreference = 'Stop'
$exitCode = 0
try {
    $command = Get-Command archivebench -CommandType Application -ErrorAction Stop | Select-Object -First 1
    function Invoke-ArchiveBench([string[]]$ArchiveArguments) {
        & $command.Source @ArchiveArguments
        if ($LASTEXITCODE -ne 0) { throw "ArchiveBench stopped with exit code $LASTEXITCODE." }
    }
    if ($SourcePath.Count -ne 1 -or -not (Test-Path -LiteralPath $SourcePath[0] -PathType Container)) {
        throw 'Select exactly one footage folder.'
    }
    $source = (Get-Item -LiteralPath $SourcePath[0]).FullName
    if (-not $Preset) {
        if (-not $PresetDirectory -or -not (Test-Path -LiteralPath $PresetDirectory -PathType Container)) {
            throw 'Choose a preset directory containing your approved JSON presets.'
        }
        $choices = @(Get-ChildItem -LiteralPath $PresetDirectory -File -Filter '*.json' | Sort-Object Name)
        if ($choices.Count -eq 0) { throw "No presets in $PresetDirectory. Export approved presets from your report first." }
        Write-Host "Archive folder: $source"
        for ($i = 0; $i -lt $choices.Count; $i++) { Write-Host "$($i + 1). $($choices[$i].BaseName)" }
        $selection = Read-Host 'Choose preset number (blank cancels)'
        if ([string]::IsNullOrWhiteSpace($selection)) { exit 0 }
        $number = 0
        if (-not [int]::TryParse($selection, [ref]$number) -or $number -lt 1 -or $number -gt $choices.Count) {
            throw 'Choose a listed preset number.'
        }
        $Preset = $choices[$number - 1].FullName
    }
    $presetFile = Get-Item -LiteralPath $Preset
    $selected = (Invoke-ArchiveBench -ArchiveArguments @('preset', 'inspect', $presetFile.FullName) | Out-String | ConvertFrom-Json).preset
    if (-not $OutputPath) { $OutputPath = $source.TrimEnd([char[]]'\/') + '-Archived-' + $presetFile.BaseName }
    $output = [IO.Path]::GetFullPath($OutputPath)
    $jobPath = $output + '.job.json'
    if (Test-Path -LiteralPath $jobPath) {
        $job = Get-Content -LiteralPath $jobPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($job.source_root -ne $source -or $job.output_root -ne $output -or
            $job.preset.evidence.settings_fingerprint -ne $selected.evidence.settings_fingerprint) {
            throw 'Existing job has different folders or settings. Choose another output folder; the existing job is unchanged.'
        }
        Write-Host 'Resuming existing job with its saved preset snapshot.'
    } else {
        Invoke-ArchiveBench -ArchiveArguments @('job', 'create', $jobPath, '--source', $source, '--output', $output, '--preset', $presetFile.FullName)
    }
    Write-Host "Job: $jobPath"
    Write-Host "Output: $output"
    Invoke-ArchiveBench -ArchiveArguments @('job', 'inspect', $jobPath)
    if (-not $InspectOnly) {
        $confirm = Read-Host 'Type ARCHIVE to encode/resume with these settings; originals stay intact (anything else cancels)'
        if ($confirm -eq 'ARCHIVE') { Invoke-ArchiveBench -ArchiveArguments @('job', 'run', $jobPath, '--execute') }
    }
    Write-Host 'Originals are kept. Review replacements and editor compatibility before a separate cleanup.'
} catch {
    Write-Error $_ -ErrorAction Continue
    $exitCode = 1
}
if (-not $InspectOnly -and -not $NoPause) { Read-Host 'Press Enter to close' | Out-Null }
exit $exitCode
