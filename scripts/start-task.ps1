[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("feat", "fix", "art", "audio", "data", "docs", "chore")]
    [string]$Type,
    [Parameter(Mandatory = $true, Position = 1)]
    [string]$Name
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BranchName = "$Type/$Name"

if ($BranchName.Length -gt 80 -or $BranchName -notmatch '^(feat|fix|art|audio|data|docs|chore)/[a-z0-9]+(-[a-z0-9]+)*$') {
    throw "Nom invalide: $BranchName. Exemple attendu: feat/player-movement"
}

Set-Location $RepoRoot
$Changes = (& git status --porcelain) -join "`n"
if ($LASTEXITCODE -ne 0) { throw "Impossible de lire l'etat Git." }
if ($Changes) { throw "Le depot contient des changements. Committez-les ou traitez-les avant de changer de tache.`n$Changes" }

& git switch main
if ($LASTEXITCODE -ne 0) { throw "Impossible de passer sur main." }
& git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw "Impossible de mettre main a jour." }
& git switch -c $BranchName
if ($LASTEXITCODE -ne 0) { throw "Impossible de creer $BranchName." }

Write-Host "Branche prete: $BranchName"
Write-Host "Quand le travail est committe: .\scripts\publish-task.ps1 '$Type`: resultat testable'"
