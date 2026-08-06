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
    $LogDirectory = Join-Path $RepoRoot "Logs\MazePlaytest"
    $ProfileLabel = "labyrinthe jouable"
} else {
    $BuildMethod = "NotThatWay.Game.Editor.ConnectionTestBuild.BuildWindows"
    $BuildPath = Join-Path $RepoRoot "Builds\ConnectionTest\Windows\GAME-Connection-Test.exe"
    $LogDirectory = Join-Path $RepoRoot "Logs\ConnectionTest"
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
if (-not $SkipBuild) {
    $BuildLog = Join-Path $LogDirectory "build-windows.log"
    Write-Host "Build Windows IL2CPP du $ProfileLabel..."
    & $UnityEditor `
        -batchmode `
        -quit `
        -projectPath $RepoRoot `
        -executeMethod $BuildMethod `
        -logFile $BuildLog
    if ($LASTEXITCODE -ne 0) { throw "Le build Unity a echoue. Voir $BuildLog" }
}

if (-not (Test-Path $BuildPath)) { throw "Build absent: $BuildPath" }
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
