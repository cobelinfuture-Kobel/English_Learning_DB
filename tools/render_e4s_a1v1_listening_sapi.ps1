[CmdletBinding(DefaultParameterSetName = 'Render')]
param(
    [Parameter(ParameterSetName = 'List', Mandatory = $true)] [switch] $ListVoices,
    [Parameter(ParameterSetName = 'Render', Mandatory = $true)] [string] $RequestFile,
    [Parameter(ParameterSetName = 'Render', Mandatory = $true)] [string] $OutputRoot,
    [Parameter(ParameterSetName = 'Render')] [string] $VoiceName,
    [Parameter(ParameterSetName = 'Render')] [ValidateRange(-3, 1)] [int] $Rate = -1,
    [Parameter(ParameterSetName = 'Render')] [ValidateRange(0, 100)] [int] $Volume = 100
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech

function Get-EnglishVoice {
    param([System.Speech.Synthesis.InstalledVoice[]] $Voices, [string] $ExactName)
    $enabled = @($Voices | Where-Object { $_.Enabled })
    if ($ExactName) {
        $selected = @($enabled | Where-Object { $_.VoiceInfo.Name -ceq $ExactName })
        if ($selected.Count -ne 1) { throw "Requested enabled voice not found: $ExactName" }
        return $selected[0]
    }
    $english = @($enabled | Where-Object { $_.VoiceInfo.Culture.Name -like 'en-*' })
    if ($english.Count -eq 0) { throw 'No enabled English SAPI voice is installed.' }
    $preferred = @('en-US', 'en-GB')
    foreach ($culture in $preferred) {
        $match = @($english | Where-Object { $_.VoiceInfo.Culture.Name -eq $culture } | Sort-Object { $_.VoiceInfo.Name })
        if ($match.Count -gt 0) { return $match[0] }
    }
    return @($english | Sort-Object { $_.VoiceInfo.Culture.Name }, { $_.VoiceInfo.Name })[0]
}

function Assert-NoReparsePoint {
    param([string] $RootPath, [string] $TargetParent)
    $current = [IO.Path]::GetFullPath($RootPath).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $limit = [IO.Path]::GetFullPath($TargetParent).TrimEnd([IO.Path]::DirectorySeparatorChar)
    while ($true) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -Force -LiteralPath $current
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse point is not allowed in audio output path: $current" }
        }
        if ($current -eq $limit) { break }
        $relative = $limit.Substring($current.Length).TrimStart([IO.Path]::DirectorySeparatorChar)
        if (-not $relative) { break }
        $nextPart = $relative.Split([IO.Path]::DirectorySeparatorChar)[0]
        $current = Join-Path $current $nextPart
    }
}

$synth = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $voices = @($synth.GetInstalledVoices())
    if ($ListVoices) {
        @($voices | ForEach-Object {
            [ordered]@{ name = $_.VoiceInfo.Name; culture = $_.VoiceInfo.Culture.Name; gender = [string]$_.VoiceInfo.Gender; age = [string]$_.VoiceInfo.Age; enabled = $_.Enabled }
        }) | ConvertTo-Json -Depth 4
        exit 0
    }

    $requestPath = [IO.Path]::GetFullPath($RequestFile)
    $root = [IO.Path]::GetFullPath($OutputRoot).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $audioRoot = [IO.Path]::GetFullPath((Join-Path $root 'audio')).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not (Test-Path -LiteralPath $requestPath -PathType Leaf)) { throw "Request file not found: $requestPath" }
    $payload = Get-Content -Raw -Encoding UTF8 -LiteralPath $requestPath | ConvertFrom-Json
    if ($payload.private_local_only -ne $true -or $payload.request_count -ne 96 -or @($payload.requests).Count -ne 96) { throw 'Invalid render request contract.' }
    $selected = Get-EnglishVoice -Voices $voices -ExactName $VoiceName
    $info = $selected.VoiceInfo
    $synth.SelectVoice($info.Name)
    $synth.Rate = $Rate
    $synth.Volume = $Volume
    $format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    $seen = @{}
    foreach ($request in @($payload.requests)) {
        if (-not ($request.transcript -is [string]) -or [string]::IsNullOrWhiteSpace($request.transcript)) { throw "Missing transcript: $($request.activity_id)" }
        if ($seen.ContainsKey([string]$request.activity_id)) { throw "Duplicate activity: $($request.activity_id)" }
        $seen[[string]$request.activity_id] = $true
        $relative = ([string]$request.audio_relative_path).Replace('/', [IO.Path]::DirectorySeparatorChar)
        if ([IO.Path]::IsPathRooted($relative) -or -not $relative.StartsWith("audio$([IO.Path]::DirectorySeparatorChar)")) { throw "Unsafe output path: $relative" }
        $target = [IO.Path]::GetFullPath((Join-Path $root $relative))
        if (-not $target.StartsWith($audioRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "Output path escapes audio root: $relative" }
        $parent = Split-Path -Parent $target
        Assert-NoReparsePoint -RootPath $root -TargetParent $parent
        [IO.Directory]::CreateDirectory($parent) | Out-Null
        $temporary = "$target.tmp.wav"
        foreach ($candidate in @($target, $temporary)) {
            if (Test-Path -LiteralPath $candidate) {
                $candidateItem = Get-Item -Force -LiteralPath $candidate
                if (($candidateItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse-point audio file is not allowed: $candidate" }
            }
        }
        try {
            $synth.SetOutputToWaveFile($temporary, $format)
            $synth.Speak([string]$request.transcript)
            $synth.SetOutputToNull()
            Move-Item -Force -LiteralPath $temporary -Destination $target
        }
        finally {
            $synth.SetOutputToNull()
            if (Test-Path -LiteralPath $temporary) { Remove-Item -Force -LiteralPath $temporary }
        }
    }
    [ordered]@{
        rendered = $seen.Count
        voice = [ordered]@{
            name = $info.Name; culture = $info.Culture.Name; gender = [string]$info.Gender; age = [string]$info.Age
            rate = $Rate; volume = $Volume; audio_format = 'WAV_PCM_16000HZ_16BIT_MONO'
        }
    } | ConvertTo-Json -Compress -Depth 4
}
finally {
    $synth.Dispose()
}
