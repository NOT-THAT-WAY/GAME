[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 7770,
    [ValidateRange(5, 120)]
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ToolchainPath = Join-Path $RepoRoot "config\toolchain.env"
$Toolchain = @{}
Get-Content -LiteralPath $ToolchainPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.+)$') { $Toolchain[$Matches[1]] = $Matches[2] }
}

$UnityVersion = $Toolchain["UNITY_VERSION"]
$DefaultEditor = "C:\Program Files\Unity\Hub\Editor\$UnityVersion\Editor\Unity.exe"
$UnityEditor = if ($env:GAME_UNITY_EDITOR) { $env:GAME_UNITY_EDITOR } else { $DefaultEditor }
$BuildMethod = "NotThatWay.Game.Editor.M1PlaytestBuild.BuildWindows"
$BuildRelativePath = "Builds/M1Playtest/Windows/GAME-M1-Playtest.exe"
$BuildPath = Join-Path $RepoRoot ($BuildRelativePath.Replace('/', '\'))
$SessionId = "il2cpp-handshake-$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))-$PID"
$SessionRelativePath = "Logs/WindowsIl2CppHandshake/$SessionId"
$SessionDirectory = Join-Path $RepoRoot ($SessionRelativePath.Replace('/', '\'))
$BuildLog = Join-Path $SessionDirectory "build.log"
$HostLog = Join-Path $SessionDirectory "host.log"
$SummaryPath = Join-Path $SessionDirectory "summary.json"
$PlayerProcess = $null
$ExitCode = 1

New-Item -ItemType Directory -Force -Path $SessionDirectory | Out-Null
Set-Location $RepoRoot

$GitCommit = ((& git rev-parse HEAD 2>$null) -join "").Trim()
$DirtyWorktree = -not [string]::IsNullOrWhiteSpace(((& git status --porcelain=v1 2>$null) -join "`n"))
$StartedAtUtc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$Summary = [ordered]@{
    schemaVersion = 1
    kind = "windows-il2cpp-fishnet-handshake"
    sessionId = $SessionId
    startedAtUtc = $StartedAtUtc
    gitCommit = $GitCommit
    sourceDirtyWorktree = $DirtyWorktree
    unityVersion = $UnityVersion
    scriptingBackend = "IL2CPP"
    buildMethod = $BuildMethod
    buildPath = $BuildRelativePath
    launchBinarySha256 = $null
    projectSettingsPreserved = $false
    handshakeMarkers = @()
    clientBoundaryObserved = $false
    serverBoundaryObserved = $false
    authenticated = $false
    result = "running"
    failure = $null
}

function Save-Summary {
    $Summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $SummaryPath -Encoding utf8
}

function Set-Failure([string]$Code) {
    $Summary.result = "failed"
    $Summary.failure = $Code
    Save-Summary
    Write-Host "IL2CPP handshake: FAIL ($Code)"
    Write-Host "Résumé: $SummaryPath"
}

try {
    if ($env:OS -ne "Windows_NT") {
        Set-Failure "WRONG_PLATFORM"
        exit 2
    }
    if (-not (Test-Path -LiteralPath $UnityEditor -PathType Leaf)) {
        Set-Failure "UNITY_EDITOR_MISSING"
        exit 2
    }

    . (Join-Path $PSScriptRoot "shared-validators.ps1")
    Invoke-SharedValidator "scripts/validate-repository.sh"

    & (Join-Path $PSScriptRoot "doctor-windows.ps1")
    if ($LASTEXITCODE -ne 0) {
        Set-Failure "WINDOWS_DOCTOR_FAILED"
        exit 2
    }

    $SettingsPath = Join-Path $RepoRoot "ProjectSettings\ProjectSettings.asset"
    $SettingsHashBefore = (Get-FileHash -LiteralPath $SettingsPath -Algorithm SHA256).Hash
    $BuildExitCode = 0

    $env:GAME_BUILD_PROFILE = "m1"
    $env:GAME_BUILD_PLATFORM = "windows"
    $env:GAME_SOURCE_GIT_COMMIT = $GitCommit
    $env:GAME_SOURCE_DIRTY_WORKTREE = $DirtyWorktree.ToString().ToLowerInvariant()
    $env:GAME_BUILD_STARTED_AT_UTC = $StartedAtUtc
    $env:GAME_UNITY_VERSION = $UnityVersion

    Write-Host "Construction du player Windows IL2CPP M1..."
    & $UnityEditor `
        -batchmode `
        -quit `
        -projectPath $RepoRoot `
        -executeMethod $BuildMethod `
        -logFile $BuildLog
    $BuildExitCode = $LASTEXITCODE

    $SettingsHashAfter = (Get-FileHash -LiteralPath $SettingsPath -Algorithm SHA256).Hash
    $Summary.projectSettingsPreserved = $SettingsHashBefore -eq $SettingsHashAfter
    if (-not $Summary.projectSettingsPreserved) {
        Set-Failure "PROJECT_SETTINGS_MUTATED"
        exit 1
    }
    if ($BuildExitCode -ne 0) {
        Set-Failure "BUILD_FAILED"
        exit 1
    }
    if (-not (Test-Path -LiteralPath $BuildPath -PathType Leaf)) {
        Set-Failure "BUILD_MISSING"
        exit 1
    }

    $Summary.launchBinarySha256 =
        (Get-FileHash -LiteralPath $BuildPath -Algorithm SHA256).Hash.ToLowerInvariant()

    if (Get-Command Get-NetUDPEndpoint -ErrorAction SilentlyContinue) {
        if (Get-NetUDPEndpoint -LocalPort $Port -ErrorAction SilentlyContinue) {
            Set-Failure "UDP_PORT_IN_USE"
            exit 2
        }
    }

    $PlayerArguments = @(
        "-batchmode",
        "-nographics",
        "--game-role=host",
        "--game-port=$Port",
        "--game-name=IL2CPP_PROBE",
        "-logFile",
        "`"$HostLog`""
    )
    $PlayerProcess = Start-Process `
        -FilePath $BuildPath `
        -ArgumentList $PlayerArguments `
        -PassThru

    $Deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $Deadline) {
        if ($PlayerProcess.HasExited) { break }
        if (Test-Path -LiteralPath $HostLog -PathType Leaf) {
            $LogText = Get-Content -Raw -LiteralPath $HostLog
            if ($LogText.Contains("Authenticated as IL2CPP_PROBE") -and
                $LogText.Contains("Roster updated (1 participant(s)).")) {
                $Summary.authenticated = $true
                break
            }
            if ($LogText.Contains("kicked for being on FishNet version") -or
                $LogText.Contains("[GAME-FISHNET-HANDSHAKE] unsupported backend=il2cpp")) {
                break
            }
        }
        Start-Sleep -Milliseconds 200
    }

    if (Test-Path -LiteralPath $HostLog -PathType Leaf) {
        $Summary.handshakeMarkers = @(
            Select-String `
                -LiteralPath $HostLog `
                -Pattern '\[GAME-FISHNET-HANDSHAKE\]' | ForEach-Object { $_.Line.Trim() }
        )
        $Summary.clientBoundaryObserved = [bool]($Summary.handshakeMarkers | Where-Object {
            $_.Contains("backend=il2cpp") -and $_.Contains("stage=client-outgoing")
        })
        $Summary.serverBoundaryObserved = [bool]($Summary.handshakeMarkers | Where-Object {
            $_.Contains("backend=il2cpp") -and $_.Contains("stage=server-incoming")
        })
    }

    if ($Summary.authenticated -and
        $Summary.clientBoundaryObserved -and
        $Summary.serverBoundaryObserved) {
        $Summary.result = "passed"
        $Summary.failure = $null
        Save-Summary
        $ExitCode = 0
        Write-Host "IL2CPP handshake: PASS"
        Write-Host "Résumé: $SummaryPath"
    } elseif ($Summary.authenticated) {
        Set-Failure "HANDSHAKE_MARKERS_MISSING"
    } else {
        Set-Failure "AUTHENTICATION_NOT_REACHED"
    }
} catch {
    $Summary.result = "failed"
    $Summary.failure = "UNEXPECTED_ERROR"
    $Summary.handshakeMarkers = @($Summary.handshakeMarkers)
    Save-Summary
    Write-Error $_
} finally {
    if ($null -ne $PlayerProcess -and -not $PlayerProcess.HasExited) {
        Stop-Process -Id $PlayerProcess.Id -Force -ErrorAction SilentlyContinue
    }
}

exit $ExitCode
