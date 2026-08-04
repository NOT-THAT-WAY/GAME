[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Title
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$BranchName = (& git branch --show-current) -join ""
if ($LASTEXITCODE -ne 0 -or -not $BranchName) { throw "Branche Git introuvable." }
if ($BranchName -notmatch '^(feat|fix|art|audio|data|docs|chore)/[a-z0-9]+(-[a-z0-9]+)*$') {
    throw "Nom de branche invalide: $BranchName"
}

$BranchType = $BranchName.Split('/')[0]
$EscapedType = [regex]::Escape($BranchType)
if ($Title -notmatch "^$EscapedType(\([a-z0-9][a-z0-9._-]*\))?:\s.+") {
    throw "La branche '$BranchName' attend un titre commencant par '$BranchType`: '."
}

$Changes = (& git status --porcelain) -join "`n"
if ($LASTEXITCODE -ne 0) { throw "Impossible de lire l'etat Git." }
if ($Changes) { throw "Le depot contient des changements non committes.`n$Changes" }

& git push -u origin $BranchName
if ($LASTEXITCODE -ne 0) { throw "Le push a echoue." }

$Gh = Get-Command gh -ErrorAction SilentlyContinue
if ($Gh) {
    & gh auth status *> $null
    if ($LASTEXITCODE -eq 0) {
        $ExistingUrl = (& gh pr view $BranchName --json url --jq .url 2>$null) -join ""
        if ($LASTEXITCODE -eq 0 -and $ExistingUrl) {
            Write-Host "PR deja ouverte: $ExistingUrl"
        } else {
            & gh pr create --base main --head $BranchName --title $Title --body-file .github/PULL_REQUEST_TEMPLATE.md
            if ($LASTEXITCODE -ne 0) { throw "Impossible de creer la PR." }
        }
        exit 0
    }
}

$RemoteUrl = (& git remote get-url origin) -join ""
$Repository = $RemoteUrl -replace '^git@github\.com:', '' -replace '^https://github\.com/', '' -replace '\.git$', ''
Write-Host "Branche poussee. GitHub CLI n'est pas connecte; ouvrez la PR ici:"
Write-Host "https://github.com/$Repository/compare/main...$($BranchName)?expand=1"
