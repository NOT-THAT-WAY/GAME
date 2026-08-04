[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("Host", "Client", "Manual")]
    [string]$Role,
    [string]$Address,
    [ValidateRange(1, 65535)]
    [int]$Port = 7770,
    [string]$Name = $env:USERNAME,
    [switch]$SkipBuild,
    [switch]$BuildOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ToolchainPath = Join-Path $RepoRoot "config\toolchain.env"
$Toolchain = @{}
Get-Content $ToolchainPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.+)$') { $Toolchain[$Matches[1]] = $Matches[2] }
}
$UnityVersion = $Toolchain["UNITY_VERSION"]
$DefaultEditor = "C:\Program Files\Unity\Hub\Editor\$UnityVersion\Editor\Unity.exe"
$UnityEditor = if ($env:GAME_UNITY_EDITOR) { $env:GAME_UNITY_EDITOR } else { $DefaultEditor }
$BuildPath = Join-Path $RepoRoot "Builds\ConnectionTest\Windows\GAME-Connection-Test.exe"
$LogDirectory = Join-Path $RepoRoot "Logs\ConnectionTest"

if ($Role -eq "Client" -and [string]::IsNullOrWhiteSpace($Address)) {
    throw "Un client doit recevoir -Address HOST_IP (ou -Address 127.0.0.1 pour un test local)."
}
if ([string]::IsNullOrWhiteSpace($Address)) { $Address = "127.0.0.1" }
if (-not (Test-Path $UnityEditor)) { throw "Unity $UnityVersion introuvable. Relancez setup-windows.ps1." }

Set-Location $RepoRoot
& (Join-Path $PSScriptRoot "doctor-windows.ps1")
if ($LASTEXITCODE -ne 0) { throw "Le diagnostic Windows doit passer avant le test." }

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
if (-not $SkipBuild) {
    $BuildLog = Join-Path $LogDirectory "build-windows.log"
    Write-Host "Build Windows IL2CPP du test de connexion..."
    & $UnityEditor `
        -batchmode `
        -quit `
        -projectPath $RepoRoot `
        -executeMethod "NotThatWay.Game.Editor.ConnectionTestBuild.BuildWindows" `
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
