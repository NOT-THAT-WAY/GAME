[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("Host", "Client", "Manual")]
    [string]$Role,
    [string]$Address,
    [ValidateRange(1, 65535)]
    [int]$Port = 7770,
    # Resolu plus bas comme sur macOS: identite Git d'abord, machine ensuite.
    [string]$Name,
    [switch]$SkipBuild,
    [switch]$BuildOnly,
    # Nomme TestProfile pour ne pas masquer la variable automatique $PROFILE ;
    # l'alias garde la meme ecriture que --profile sur macOS.
    [Alias("Profile")]
    [ValidateSet("Connection", "Maze")]
    [string]$TestProfile = "Connection"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "shared-validators.ps1")
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ToolchainPath = Join-Path $RepoRoot "config\toolchain.env"
$Toolchain = @{}
Get-Content $ToolchainPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.+)$') { $Toolchain[$Matches[1]] = $Matches[2] }
}
$UnityVersion = $Toolchain["UNITY_VERSION"]
$DefaultEditor = "C:\Program Files\Unity\Hub\Editor\$UnityVersion\Editor\Unity.exe"
$UnityEditor = if ($env:GAME_UNITY_EDITOR) { $env:GAME_UNITY_EDITOR } else { $DefaultEditor }
if ($TestProfile -eq "Maze") {
    $BuildMethod = "NotThatWay.Game.Editor.MazePlaytestBuild.BuildWindows"
    $BuildPath = Join-Path $RepoRoot "Builds\MazePlaytest\Windows\GAME-Maze-Playtest.exe"
    $BuildRelativePath = "Builds/MazePlaytest/Windows/GAME-Maze-Playtest.exe"
    $LogDirectory = Join-Path $RepoRoot "Logs\MazePlaytest"
    $BuildLogRelativePath = "Logs/MazePlaytest/build-windows.log"
    $ProfileLabel = "labyrinthe jouable"
} else {
    $BuildMethod = "NotThatWay.Game.Editor.ConnectionTestBuild.BuildWindows"
    $BuildPath = Join-Path $RepoRoot "Builds\ConnectionTest\Windows\GAME-Connection-Test.exe"
    $BuildRelativePath = "Builds/ConnectionTest/Windows/GAME-Connection-Test.exe"
    $LogDirectory = Join-Path $RepoRoot "Logs\ConnectionTest"
    $BuildLogRelativePath = "Logs/ConnectionTest/build-windows.log"
    $ProfileLabel = "test de connexion"
}

if ($Role -eq "Client" -and [string]::IsNullOrWhiteSpace($Address)) {
    throw "Un client doit recevoir -Address HOST_IP (ou -Address 127.0.0.1 pour un test local)."
}
if ([string]::IsNullOrWhiteSpace($Address)) { $Address = "127.0.0.1" }
if (-not (Test-Path $UnityEditor)) { throw "Unity $UnityVersion introuvable. Relancez setup-windows.ps1." }

Set-Location $RepoRoot

# Parite avec first-test-macos.sh, qui prend le nom du joueur dans l'identite Git
# afin que le roster affiche la meme personne quelle que soit la plateforme.
if ([string]::IsNullOrWhiteSpace($Name)) { $Name = (& git config --get user.name 2>$null) -join "" }
if ([string]::IsNullOrWhiteSpace($Name)) { $Name = $env:USERNAME }
if ([string]::IsNullOrWhiteSpace($Name)) { $Name = $env:COMPUTERNAME }

& (Join-Path $PSScriptRoot "doctor-windows.ps1")
if ($LASTEXITCODE -ne 0) { throw "Le diagnostic Windows doit passer avant le test." }

# Parite avec first-test-macos.sh: le contrat du depot est verifie avant de builder.
Invoke-SharedValidator "scripts/validate-repository.sh"

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$BuildLog = Join-Path $RepoRoot $BuildLogRelativePath
$BuildManifestPath = Join-Path (Split-Path -Parent $BuildPath) "build-manifest.json"
$BuildFingerprintPath = Join-Path (Split-Path -Parent $BuildPath) "build-bundle-fingerprint.json"
$BundleRoot = Split-Path -Parent $BuildPath
$BundleRelativePath = $BuildRelativePath -replace '/[^/]+$', ''
$GitCommit = ((& git rev-parse HEAD 2>$null) -join "").Trim()
if ([string]::IsNullOrWhiteSpace($GitCommit)) { $GitCommit = "unknown" }
$DirtyWorktree = -not [string]::IsNullOrWhiteSpace(((& git status --porcelain=v1 2>$null) -join "`n"))
$BuildStartedAtUtc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")

function Get-Sha256Text([string]$Value) {
    $Algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $Bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Value)
        return ([BitConverter]::ToString($Algorithm.ComputeHash($Bytes))).Replace("-", "").ToLowerInvariant()
    } finally {
        $Algorithm.Dispose()
    }
}

$NormalizedProfile = $TestProfile.ToLowerInvariant()
$BuildSetSeed = "schema=1|commit=$GitCommit|profile=$NormalizedProfile|unity=$UnityVersion"
if ($DirtyWorktree) { $BuildSetSeed += "|dirty=true|started=$BuildStartedAtUtc" }
$BuildSetId = Get-Sha256Text $BuildSetSeed
$BuildId = Get-Sha256Text "$BuildSetId|platform=windows|started=$BuildStartedAtUtc"

function New-BundleFingerprint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [string[]]$ExcludedRelativePaths = @()
    )

    $ResolvedRoot = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\', '/')
    $Records = @()
    foreach ($File in Get-ChildItem -LiteralPath $ResolvedRoot -Recurse -File) {
        $RelativePath = $File.FullName.Substring($ResolvedRoot.Length).TrimStart('\', '/').Replace('\', '/')
        if ($ExcludedRelativePaths -contains $RelativePath) { continue }
        $Records += [pscustomobject][ordered]@{
            relativePath = $RelativePath
            sizeBytes = [long]$File.Length
            sha256 = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    $Records = @($Records | Sort-Object -Property relativePath)
    $Canonical = [System.Text.StringBuilder]::new()
    [long]$TotalBytes = 0
    foreach ($Record in $Records) {
        [void]$Canonical.Append($Record.relativePath).Append("`t").Append($Record.sizeBytes).Append("`t").Append($Record.sha256).Append("`n")
        $TotalBytes += $Record.sizeBytes
    }

    return [ordered]@{
        schemaVersion = 1
        kind = "unity-build-bundle-fingerprint"
        algorithm = "sha256-relative-path-size-content-v1"
        fileCount = $Records.Count
        totalBytes = $TotalBytes
        bundleManifestSha256 = Get-Sha256Text $Canonical.ToString()
        files = $Records
    }
}

function Write-BuildManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Result,
        [Parameter(Mandatory = $true)]
        [int]$ExitCode,
        [Parameter(Mandatory = $true)]
        [string]$Provenance,
        [switch]$IncludeArtifact
    )

    $BinaryHash = $null
    $BinarySize = $null
    $BundleFingerprint = $null
    if ($IncludeArtifact) {
        if (-not (Test-Path -LiteralPath $BuildPath -PathType Leaf)) {
            throw "Binaire absent au moment de produire le manifeste: $BuildPath"
        }
        $BinaryHash = (Get-FileHash -LiteralPath $BuildPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $BinarySize = (Get-Item -LiteralPath $BuildPath).Length
        $BundleFingerprint = New-BundleFingerprint `
            -Root $BundleRoot `
            -ExcludedRelativePaths @("build-manifest.json", "build-bundle-fingerprint.json")
        $BundleFingerprint | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $BuildFingerprintPath -Encoding utf8
    }

    $Manifest = [ordered]@{
        schemaVersion = 2
        kind = "unity-player-build"
        buildId = $BuildId
        buildSetId = $BuildSetId
        profile = $NormalizedProfile
        platform = "windows"
        buildTarget = "StandaloneWindows64"
        developmentBuild = $true
        scriptingBackendPolicy = "il2cpp-forced"
        startedAtUtc = $BuildStartedAtUtc
        finishedAtUtc = if ($Result -eq "building") { $null } else { [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ") }
        sourceGitCommit = $GitCommit
        sourceDirtyWorktree = $DirtyWorktree
        unityVersion = $UnityVersion
        buildMethod = $BuildMethod
        buildPath = $BuildRelativePath
        bundlePath = $BundleRelativePath
        bundleFingerprintPath = "$BundleRelativePath/build-bundle-fingerprint.json"
        bundleFingerprint = $BundleFingerprint
        binaryPath = $BuildRelativePath
        binarySha256 = $BinaryHash
        binarySizeBytes = $BinarySize
        buildLog = $BuildLogRelativePath
        provenance = $Provenance
        result = $Result
        exitCode = $ExitCode
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $BuildManifestPath) | Out-Null
    $Manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $BuildManifestPath -Encoding utf8
}

if (-not $SkipBuild) {
    Write-Host "Build Windows IL2CPP du $ProfileLabel..."
    Write-BuildManifest -Result "building" -ExitCode 0 -Provenance "current-run"
    $env:GAME_BUILD_ID = $BuildId
    $env:GAME_BUILD_SET_ID = $BuildSetId
    $env:GAME_BUILD_PROFILE = $NormalizedProfile
    $env:GAME_BUILD_PLATFORM = "windows"
    $env:GAME_SOURCE_GIT_COMMIT = $GitCommit
    $env:GAME_SOURCE_DIRTY_WORKTREE = $DirtyWorktree.ToString().ToLowerInvariant()
    $env:GAME_BUILD_STARTED_AT_UTC = $BuildStartedAtUtc
    $env:GAME_UNITY_VERSION = $UnityVersion
    & $UnityEditor `
        -batchmode `
        -quit `
        -projectPath $RepoRoot `
        -executeMethod $BuildMethod `
        -logFile $BuildLog
    $BuildExitCode = $LASTEXITCODE
    if ($BuildExitCode -ne 0) {
        Write-BuildManifest -Result "failed" -ExitCode $BuildExitCode -Provenance "current-run"
        throw "Le build Unity a echoue. Voir $BuildLog"
    }
}

if (-not (Test-Path -LiteralPath $BuildPath -PathType Leaf)) {
    if (-not $SkipBuild) {
        Write-BuildManifest -Result "failed" -ExitCode 1 -Provenance "artifact-invalid"
    }
    throw "Build absent: $BuildPath"
}

if (-not $SkipBuild) {
    try {
        Write-BuildManifest -Result "passed" -ExitCode 0 -Provenance "current-run" -IncludeArtifact
    } catch {
        Write-BuildManifest -Result "failed" -ExitCode 1 -Provenance "artifact-hash-failed"
        throw
    }
    Write-Host "Manifeste: $BuildManifestPath"
} elseif (-not (Test-Path -LiteralPath $BuildManifestPath -PathType Leaf)) {
    Write-Warning "Build reutilise sans manifeste de provenance: $BuildPath"
}

if ($BuildOnly) {
    Write-Host "Build pret: $BuildPath"
    exit 0
}

$SafeName = $Name.Replace('"', '')
$PlayerLog = Join-Path $LogDirectory "player-$($Role.ToLowerInvariant())-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$ArgumentLine = "--game-role=$($Role.ToLowerInvariant()) --game-address=$Address --game-port=$Port --game-name=`"$SafeName`" -logFile `"$PlayerLog`""
Start-Process -FilePath $BuildPath -ArgumentList $ArgumentLine

Write-Host "Test lance en $Role sous le nom '$SafeName'. Log: $PlayerLog"
if ($Role -eq "Host") {
    $LocalIp = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and $_.AddressState -eq 'Preferred' } |
        Select-Object -ExpandProperty IPAddress -First 1
    Write-Host "Les clients utilisent le port UDP $Port et cette IP probable: $LocalIp"
    Write-Host "Au premier lancement, autorisez GAME sur les reseaux prives dans le pare-feu Windows."
}
