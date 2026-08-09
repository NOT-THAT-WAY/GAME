[CmdletBinding()]
param(
    [ValidateSet("Connection", "Maze")]
    [string]$TestProfile = "Maze",
    [ValidateRange(1, 65535)]
    [int]$Port = 7770,
    [switch]$Build,
    [switch]$TwoInstances,
    [switch]$PreflightOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ToolchainPath = Join-Path $RepoRoot "config\toolchain.env"
$Warnings = [Collections.Generic.List[string]]::new()
$Blockers = [Collections.Generic.List[string]]::new()
$BuildProducedByWrapper = $false

function Add-Warning([string]$Code) {
    if (-not $Warnings.Contains($Code)) { $Warnings.Add($Code) }
}

function Add-Blocker([string]$Code) {
    if (-not $Blockers.Contains($Code)) { $Blockers.Add($Code) }
}

function Get-Readiness {
    if ($Blockers.Count -gt 0) { return "BLOCKED" }
    if ($Warnings.Count -gt 0) { return "READY-WITH-WARNINGS" }
    return "READY"
}

Set-Location $RepoRoot

if ($env:OS -ne "Windows_NT") {
    Add-Blocker "WRONG_PLATFORM"
}

$UnityVersion = "unknown"
if (Test-Path $ToolchainPath) {
    $UnityLine = Get-Content $ToolchainPath | Where-Object { $_ -match '^UNITY_VERSION=' } | Select-Object -First 1
    if ($UnityLine) { $UnityVersion = ($UnityLine -split '=', 2)[1] }
    if (-not $UnityVersion) {
        $UnityVersion = "unknown"
        Add-Blocker "UNITY_VERSION_MISSING"
    }
} else {
    Add-Blocker "TOOLCHAIN_MISSING"
}

$GitCommit = "unknown"
if (Get-Command git -ErrorAction SilentlyContinue) {
    & git rev-parse --is-inside-work-tree *> $null
    if ($LASTEXITCODE -eq 0) {
        $GitCommit = ((& git rev-parse HEAD 2>$null) -join "").Trim()
        if (-not $GitCommit) {
            $GitCommit = "unknown"
            Add-Blocker "GIT_COMMIT_UNAVAILABLE"
        }

        $DirtyStatus = ((& git status --porcelain=v1 2>$null) -join "`n")
        if ($DirtyStatus) { Add-Warning "DIRTY_WORKTREE" }
    } else {
        Add-Blocker "GIT_UNAVAILABLE"
    }
} else {
    Add-Blocker "GIT_UNAVAILABLE"
}

$ShortCommit = if ($GitCommit.Length -ge 8) { $GitCommit.Substring(0, 8) } else { $GitCommit }
$StartedAtUtc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$SessionStamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$SessionId = "ht00-$SessionStamp-$ShortCommit-$PID"
$SessionRelativePath = "Logs/HumanTest/$SessionId"
$SessionDirectory = Join-Path $RepoRoot $SessionRelativePath

try {
    New-Item -ItemType Directory -Force -Path $SessionDirectory | Out-Null
} catch {
    Write-Host "HT-00 readiness: BLOCKED"
    Write-Error "Blocage: SESSION_DIRECTORY_UNWRITABLE"
    exit 2
}

$PreflightLog = Join-Path $SessionDirectory "preflight.log"
$ManifestPath = Join-Path $SessionDirectory "manifest.json"
$ObservationPath = Join-Path $SessionDirectory "observation.md"
$HostLog = Join-Path $SessionDirectory "host.log"
$ClientLog = Join-Path $SessionDirectory "client.log"
$InstanceCount = if ($TwoInstances) { 2 } else { 1 }
$TransportScope = if ($TwoInstances) { "two-instance-loopback" } else { "single-host-local" }
$PlayerLabels = if ($TwoInstances) { @("HT_HOST", "HT_CLIENT") } else { @("HT_HOST") }
$ClientLogArtifact = if ($TwoInstances) { "$SessionRelativePath/client.log" } else { $null }
"HT-00 local preflight - $StartedAtUtc" | Set-Content -Path $PreflightLog -Encoding utf8

$Bash = Get-Command bash -ErrorAction SilentlyContinue
$RepositoryValidator = Join-Path $PSScriptRoot "validate-repository.sh"
if ($Bash -and (Test-Path $RepositoryValidator)) {
    $BashPath = $Bash.Path
    & $BashPath $RepositoryValidator *>> $PreflightLog
    if ($LASTEXITCODE -ne 0) { Add-Warning "REPOSITORY_VALIDATION_FAILED" }
} else {
    Add-Warning "REPOSITORY_VALIDATOR_UNAVAILABLE"
}

if (Get-Command git-lfs -ErrorAction SilentlyContinue) {
    & git lfs fsck *>> $PreflightLog
    if ($LASTEXITCODE -ne 0) { Add-Warning "LFS_VALIDATION_FAILED" }
} else {
    Add-Warning "GIT_LFS_UNAVAILABLE"
}

if ($TestProfile -eq "Maze") {
    $BuildRelativePath = "Builds/MazePlaytest/Windows/GAME-Maze-Playtest.exe"
    $BuildCommandHint = ".\scripts\first-test-windows.ps1 Manual -TestProfile Maze -BuildOnly"
} else {
    $BuildRelativePath = "Builds/ConnectionTest/Windows/GAME-Connection-Test.exe"
    $BuildCommandHint = ".\scripts\first-test-windows.ps1 Manual -TestProfile Connection -BuildOnly"
}

if ($Build) {
    $BuildWrapper = Join-Path $PSScriptRoot "first-test-windows.ps1"
    if (-not (Test-Path $BuildWrapper)) {
        Add-Blocker "BUILD_WRAPPER_MISSING"
    } else {
        $PowerShellHost = (Get-Process -Id $PID).Path
        & $PowerShellHost -NoProfile -ExecutionPolicy Bypass -File $BuildWrapper Manual -TestProfile $TestProfile -BuildOnly *>> $PreflightLog
        if ($LASTEXITCODE -eq 0) {
            $BuildProducedByWrapper = $true
        } else {
            Add-Blocker "BUILD_FAILED"
        }
    }
} else {
    Add-Warning "BUILD_PROVENANCE_UNVERIFIED"
}

$BuildPath = Join-Path $RepoRoot $BuildRelativePath
$BuildHash = "unavailable"
if (-not (Test-Path $BuildPath -PathType Leaf)) {
    Add-Blocker "BUILD_MISSING_OR_NOT_EXECUTABLE"
} else {
    try {
        $BuildHash = (Get-FileHash -Algorithm SHA256 -Path $BuildPath).Hash.ToLowerInvariant()
    } catch {
        Add-Blocker "BUILD_HASH_FAILED"
    }
}

if (Get-Command Get-NetUDPEndpoint -ErrorAction SilentlyContinue) {
    $ExistingEndpoint = Get-NetUDPEndpoint -LocalPort $Port -ErrorAction SilentlyContinue
    if ($ExistingEndpoint) { Add-Blocker "UDP_PORT_IN_USE" }
} else {
    Add-Warning "PORT_AVAILABILITY_UNCHECKED"
}

function Write-Manifest([string]$Readiness, [string]$LaunchStatus) {
    $Manifest = [ordered]@{
        schemaVersion = 1
        testId = "HT-00"
        evidenceLevel = "developer-smoke"
        isFinalNetworkProof = $false
        sessionId = $SessionId
        startedAtUtc = $StartedAtUtc
        gitCommit = $GitCommit
        unityVersion = $UnityVersion
        platform = "windows"
        architecture = if ($env:PROCESSOR_ARCHITECTURE) { $env:PROCESSOR_ARCHITECTURE } else { "unknown" }
        profile = $TestProfile.ToLowerInvariant()
        transportScope = $TransportScope
        instanceCount = $InstanceCount
        port = $Port
        buildPath = $BuildRelativePath.Replace('\', '/')
        launchBinarySha256 = $BuildHash
        buildProducedByWrapper = $BuildProducedByWrapper
        readiness = $Readiness
        warnings = @($Warnings)
        blockers = @($Blockers)
        launchStatus = $LaunchStatus
        playerLabels = $PlayerLabels
        artifacts = [ordered]@{
            preflight = "$SessionRelativePath/preflight.log"
            hostLog = "$SessionRelativePath/host.log"
            clientLog = $ClientLogArtifact
            observation = "$SessionRelativePath/observation.md"
            report = "$SessionRelativePath/report.json"
        }
    }

    $Manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestPath -Encoding utf8
}

function Write-Observation([string]$Readiness) {
    $WarningLines = if ($Warnings.Count -gt 0) {
        ($Warnings | ForEach-Object { "- $_" }) -join "`n"
    } else {
        "- aucun"
    }
    $InstanceCheck = if ($TwoInstances) {
        "- [ ] Les deux fenetres sont actives et le deplacement de ``HT_HOST`` est visible dans ``HT_CLIENT``."
    } else {
        "- [ ] La fenetre ``HT_HOST`` est active."
    }

    $Observation = @"
# HT-00 - smoke test minimum

- Session : ``$SessionId``
- Commit : ``$GitCommit``
- Profil : ``$($TestProfile.ToLowerInvariant())``
- Plateforme : Windows
- Instances : ``$InstanceCount``
- Preparation : **$Readiness**
- Binaire lance : ``$BuildHash``

## Avertissements de preflight

$WarningLines

## Actions strictement necessaires

$InstanceCheck
- [ ] Bouger et regarder autour de soi.
- [ ] Sauter une fois.
- [ ] Faire tourner un pivot ou un mur mobile.
- [ ] Donner un coup de poing au bot et le toucher.
- [ ] Fermer le jeu.

## Note humaine facultative

- Probleme casse ou genant :
- Etapes minimales pour le reproduire :

## Verdict automatique apres fermeture

``````powershell
python scripts/human-test-report.py --session "$SessionRelativePath"
``````

Le rapport exige uniquement les actions ci-dessus et l'absence d'erreur fatale. Ce test ne prouve
ni le reseau distant, ni l'autorite serveur, ni la convergence multi-machine ou la performance finale.
Ne pas publier les logs bruts : ils peuvent contenir des chemins locaux ou d'autres donnees techniques.
"@

    $Observation | Set-Content -Path $ObservationPath -Encoding utf8
}

$Readiness = Get-Readiness
Write-Observation $Readiness

Write-Host "HT-00 readiness: $Readiness"
if ($Warnings.Count -gt 0) { Write-Host "Avertissements: $($Warnings -join ', ')" }
if ($Blockers.Count -gt 0) {
    Write-Host "Blocages: $($Blockers -join ', ')"
    Write-Host "Build attendu: $BuildCommandHint"
    Write-Manifest $Readiness "not-started"
    Write-Host "Session: $SessionRelativePath"
    exit 2
}

if ($PreflightOnly) {
    Write-Manifest $Readiness "not-requested"
    Write-Host "Preflight uniquement. Session: $SessionRelativePath"
    Write-Host "HT-00 reste un smoke local et ne constitue pas une preuve reseau finale."
    exit 0
}

$HostArguments = @(
    "--human-test",
    "--game-role=host",
    "--game-address=127.0.0.1",
    "--game-port=$Port",
    "--game-name=HT_HOST",
    "-logFile",
    "`"$HostLog`""
)
$ClientArguments = @(
    "--human-test",
    "--game-role=client",
    "--game-address=127.0.0.1",
    "--game-port=$Port",
    "--game-name=HT_CLIENT",
    "-logFile",
    "`"$ClientLog`""
)

try {
    Start-Process -FilePath $BuildPath -ArgumentList $HostArguments | Out-Null
    if ($TwoInstances) {
        Start-Sleep -Seconds 1
        Start-Process -FilePath $BuildPath -ArgumentList $ClientArguments | Out-Null
    }
} catch {
    Add-Blocker "APP_LAUNCH_FAILED"
}

$Readiness = Get-Readiness
if ($Blockers.Count -gt 0) {
    Write-Manifest $Readiness "failed"
    Write-Host "HT-00 readiness: BLOCKED"
    Write-Host "Blocages: $($Blockers -join ', ')"
    Write-Host "Fermez toute instance deja ouverte, puis consultez $PreflightLog."
    exit 2
}

Write-Manifest $Readiness "started"
if ($TwoInstances) {
    Write-Host "Deux instances locales lancees avec --human-test."
} else {
    Write-Host "Instance hote locale lancee avec --human-test."
}
Write-Host "Checklist minimale: $ObservationPath"
Write-Host "Log prive: $HostLog"
if ($TwoInstances) { Write-Host "Log client prive: $ClientLog" }
Write-Host "Apres fermeture: python scripts/human-test-report.py --session $SessionRelativePath"
Write-Host "HT-00 est un smoke local : ce resultat ne valide pas le reseau final."
