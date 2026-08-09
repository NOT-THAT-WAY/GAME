[CmdletBinding()]
param(
    [ValidateSet("All", "EditMode", "PlayMode")]
    [string]$Suite = "All",
    [string]$ResultsDirectory
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ToolchainPath = Join-Path $RepoRoot "config\toolchain.env"
$Toolchain = @{}
Get-Content $ToolchainPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.+)$') { $Toolchain[$Matches[1]] = $Matches[2] }
}

$UnityVersion = $Toolchain["UNITY_VERSION"]
if ([string]::IsNullOrWhiteSpace($UnityVersion)) {
    throw "UNITY_VERSION absente de config/toolchain.env."
}

$DefaultEditor = "C:\Program Files\Unity\Hub\Editor\$UnityVersion\Editor\Unity.exe"
$UnityEditor = if ($env:GAME_UNITY_EDITOR) { $env:GAME_UNITY_EDITOR } else { $DefaultEditor }
if (-not (Test-Path -LiteralPath $UnityEditor -PathType Leaf)) {
    throw "Unity $UnityVersion introuvable: $UnityEditor"
}

if ([string]::IsNullOrWhiteSpace($ResultsDirectory)) {
    if ($env:GAME_TEST_RESULTS_DIR) {
        $ResultsDirectory = $env:GAME_TEST_RESULTS_DIR
    } else {
        $RunId = "$(Get-Date -Format 'yyyyMMdd-HHmmss')-$PID"
        $ResultsDirectory = Join-Path $RepoRoot "Logs\Tests\windows\$RunId"
    }
} elseif (-not [System.IO.Path]::IsPathRooted($ResultsDirectory)) {
    $ResultsDirectory = Join-Path $RepoRoot $ResultsDirectory
}

New-Item -ItemType Directory -Force -Path $ResultsDirectory | Out-Null
$StartedAtUtc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$GitCommit = ((& git -C $RepoRoot rev-parse HEAD 2>$null) -join "").Trim()
if (-not $GitCommit) { $GitCommit = "unknown" }
$DirtyWorktree = [bool](((& git -C $RepoRoot status --porcelain=v1 2>$null) -join "`n").Trim())
$SuiteRecords = [Collections.Generic.List[object]]::new()
$TestPlatforms = switch ($Suite) {
    "EditMode" { @("EditMode") }
    "PlayMode" { @("PlayMode") }
    default { @("EditMode", "PlayMode") }
}

Write-Host "GAME - tests Unity $UnityVersion"
Write-Host "Projet: $RepoRoot"
Write-Host "Resultats: $ResultsDirectory"

$OverallExit = 0
foreach ($Platform in $TestPlatforms) {
    $Stem = $Platform.ToLowerInvariant()
    $ResultsFile = Join-Path $ResultsDirectory "$Stem-results.xml"
    $LogFile = Join-Path $ResultsDirectory "$Stem.log"

    Write-Host "`n[$Platform] lancement..."
    & $UnityEditor `
        -batchmode `
        -projectPath $RepoRoot `
        -runTests `
        -testPlatform $Platform `
        -testResults $ResultsFile `
        -logFile $LogFile
    $UnityExit = $LASTEXITCODE

    if ($UnityExit -ne 0) {
        Write-Error "[$Platform] ECHEC - Unity a retourne $UnityExit. Log: $LogFile" -ErrorAction Continue
        if ($OverallExit -eq 0) { $OverallExit = $UnityExit }
        $SuiteRecords.Add([ordered]@{
            name = $Platform; result = "failed"; unityExitCode = $UnityExit
            total = $null; passed = $null; failed = $null
            xml = "$Stem-results.xml"; log = "$Stem.log"
        })
        continue
    }

    if (-not (Test-Path -LiteralPath $ResultsFile -PathType Leaf) -or
        (Get-Item -LiteralPath $ResultsFile).Length -eq 0) {
        Write-Error "[$Platform] ECHEC - XML absent ou vide. Log: $LogFile" -ErrorAction Continue
        if ($OverallExit -eq 0) { $OverallExit = 1 }
        $SuiteRecords.Add([ordered]@{
            name = $Platform; result = "failed"; unityExitCode = 0
            total = $null; passed = $null; failed = $null
            xml = "$Stem-results.xml"; log = "$Stem.log"
        })
        continue
    }

    $Root = $null
    try {
        [xml]$ResultsXml = Get-Content -LiteralPath $ResultsFile -Raw
        $Root = $ResultsXml.DocumentElement
        if ($Root.Name -ne "test-run" -or $Root.GetAttribute("result") -ne "Passed") {
            throw "La racine XML ne declare pas test-run result=Passed."
        }
    } catch {
        Write-Error "[$Platform] ECHEC - XML invalide ou suite non verte: $ResultsFile ($($_.Exception.Message))" -ErrorAction Continue
        if ($OverallExit -eq 0) { $OverallExit = 1 }
        $SuiteRecords.Add([ordered]@{
            name = $Platform; result = "failed"; unityExitCode = 0
            total = $null; passed = $null; failed = $null
            xml = "$Stem-results.xml"; log = "$Stem.log"
        })
        continue
    }

    $SuiteRecords.Add([ordered]@{
        name = $Platform; result = "passed"; unityExitCode = 0
        total = [int]$Root.GetAttribute("total")
        passed = [int]$Root.GetAttribute("passed")
        failed = [int]$Root.GetAttribute("failed")
        xml = "$Stem-results.xml"; log = "$Stem.log"
    })
    Write-Host "[$Platform] OK - total=$($Root.GetAttribute('total')) passed=$($Root.GetAttribute('passed'))"
}

$Manifest = [ordered]@{
    schemaVersion = 1
    kind = "unity-test-run"
    startedAtUtc = $StartedAtUtc
    finishedAtUtc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    gitCommit = $GitCommit
    dirtyWorktree = $DirtyWorktree
    unityVersion = $UnityVersion
    platform = "windows"
    requestedSuite = $Suite.ToLowerInvariant()
    result = if ($OverallExit -eq 0) { "passed" } else { "failed" }
    exitCode = $OverallExit
    suites = @($SuiteRecords)
}
$Manifest | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $ResultsDirectory "test-run.json") -Encoding utf8

if ($OverallExit -ne 0) {
    Write-Error "Une ou plusieurs suites ont echoue. Resultats: $ResultsDirectory" -ErrorAction Continue
    exit $OverallExit
}

Write-Host "`nToutes les suites demandees sont vertes. Resultats: $ResultsDirectory"
