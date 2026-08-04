[CmdletBinding()]
param(
    [switch]$InstallTools,
    [switch]$InstallIDE,
    [switch]$OpenUnity,
    [switch]$All,
    [string]$AssetRemote,
    [string]$AssetEndpoint,
    [string]$AssetProfile
)

$ErrorActionPreference = "Stop"
if ($All) { $InstallTools = $true; $InstallIDE = $true; $OpenUnity = $true }

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ToolchainPath = Join-Path $RepoRoot "config\toolchain.env"
$Toolchain = @{}
Get-Content $ToolchainPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.+)$') { $Toolchain[$Matches[1]] = $Matches[2] }
}
$UnityVersion = $Toolchain["UNITY_VERSION"]
$UnityChangeset = $Toolchain["UNITY_CHANGESET"]
$DefaultEditor = "C:\Program Files\Unity\Hub\Editor\$UnityVersion\Editor\Unity.exe"
$UnityEditor = if ($env:GAME_UNITY_EDITOR) { $env:GAME_UNITY_EDITOR } else { $DefaultEditor }

function Install-WingetPackage([string]$Id, [string[]]$ExtraArguments = @()) {
    Write-Host "Installation/verification de $Id..."
    $Arguments = @("install", "--id", $Id, "--exact", "--accept-package-agreements", "--accept-source-agreements") + $ExtraArguments
    & winget @Arguments
    if ($LASTEXITCODE -ne 0) { throw "winget a echoue pour $Id" }
}

if ($env:OS -ne "Windows_NT") { throw "Ce script doit etre execute sur Windows." }
Set-Location $RepoRoot

if ($InstallTools) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "winget est requis pour -InstallTools." }
    Install-WingetPackage "Git.Git"
    Install-WingetPackage "GitHub.GitLFS"
    Install-WingetPackage "GitHub.cli"
    Install-WingetPackage "Iterative.DVC"
    Install-WingetPackage "Unity.UnityHub"
}

if ($InstallIDE) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "winget est requis pour -InstallIDE." }
    Install-WingetPackage "Microsoft.VisualStudio.2022.Community" @("--override", "--wait --passive --add Microsoft.VisualStudio.Workload.ManagedGame --includeRecommended")
}

$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git est absent. Installez-le puis rouvrez PowerShell." }
& git lfs version *> $null
if ($LASTEXITCODE -ne 0) { throw "Git LFS est absent." }
if (-not (Get-Command dvc -ErrorAction SilentlyContinue)) { throw "DVC est absent. Relancez avec -InstallTools puis rouvrez PowerShell." }

& git lfs install --local --skip-repo
& git lfs pull
& git config --local pull.ff only
& git config --local core.hooksPath .githooks

if ($AssetRemote) {
    $AssetArguments = @{
        Action = "Configure"
        RemoteUrl = $AssetRemote
    }
    if ($AssetEndpoint) { $AssetArguments["EndpointUrl"] = $AssetEndpoint }
    if ($AssetProfile) { $AssetArguments["Profile"] = $AssetProfile }
    & (Join-Path $PSScriptRoot "assets-windows.ps1") @AssetArguments
}

$DvcRemotes = (& dvc remote list 2>$null) -join "`n"
if ($LASTEXITCODE -eq 0 -and $DvcRemotes -match '(?m)^assets\s') {
    & (Join-Path $PSScriptRoot "assets-windows.ps1") -Action Pull
} else {
    Write-Host "Remote d'assets non configure - le test reseau fonctionne sans lui."
}

if (Test-Path $UnityEditor) {
    $SmartMerge = Join-Path (Split-Path $UnityEditor -Parent) "Data\Tools\UnityYAMLMerge.exe"
    if (Test-Path $SmartMerge) {
        $Driver = '"' + $SmartMerge + '" merge -p %O %B %A %A'
        & git config --local merge.unityyamlmerge.name "Unity SmartMerge"
        & git config --local merge.unityyamlmerge.driver $Driver
        & git config --local merge.unityyamlmerge.recursive binary
        Write-Host "UnityYAMLMerge configure."
    }
} elseif ($OpenUnity) {
    Write-Host "Ouverture de Unity Hub pour $UnityVersion. Ajoutez Windows Build Support (IL2CPP)."
    Start-Process "unityhub://$UnityVersion/$UnityChangeset"
}

if (Test-Path $UnityEditor) {
    & (Join-Path $PSScriptRoot "doctor-windows.ps1")
    exit $LASTEXITCODE
}

& (Join-Path $PSScriptRoot "doctor-windows.ps1")
Write-Host "`nTerminez l'installation Unity dans Hub, puis relancez setup-windows.ps1."
exit 0
