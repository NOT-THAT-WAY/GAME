[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Title,
    [string]$BodyFile
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "shared-validators.ps1")
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$BranchName = (& git branch --show-current) -join ""
if ($LASTEXITCODE -ne 0 -or -not $BranchName) { throw "Branche Git introuvable." }

# Parite avec publish-task.sh: branche et titre passent par le validateur partage,
# celui-la meme que la CI applique a la pull request.
Invoke-SharedValidator "scripts/validate-pr-policy.sh" @($BranchName, $Title)

$ResolvedBodyFile = $null
if ($BodyFile) {
    $ResolvedBodyFile = (Resolve-Path -LiteralPath $BodyFile).Path
    Invoke-SharedValidator "scripts/validate-pr-body.sh" @($ResolvedBodyFile)
}

$Changes = (& git status --porcelain) -join "`n"
if ($LASTEXITCODE -ne 0) { throw "Impossible de lire l'etat Git." }
if ($Changes) { throw "Le depot contient des changements non committes.`n$Changes" }

# Parite avec publish-task.sh: le contrat du depot est verifie avant le push. Le
# hook pre-push le fait aussi, mais il reste inactif tant que le setup n'a pas pose
# core.hooksPath, et la CI ne repond qu'apres la publication.
Invoke-SharedValidator "scripts/validate-repository.sh"

$Gh = Get-Command gh -ErrorAction SilentlyContinue
$GhAuthenticated = $false
$ExistingUrl = ""
if ($Gh) {
    & gh auth status *> $null
    if ($LASTEXITCODE -eq 0) {
        $GhAuthenticated = $true
        $ExistingUrl = ((& gh pr view $BranchName --json url --jq .url 2>$null) -join "").Trim()
        if (-not $ExistingUrl -and -not $ResolvedBodyFile -and
            ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected)) {
            throw "Une nouvelle PR non interactive exige -BodyFile FICHIER. En terminal interactif, gh ouvre la saisie du corps."
        }
    }
}

& git push -u origin $BranchName
if ($LASTEXITCODE -ne 0) { throw "Le push a echoue." }

if ($GhAuthenticated) {
    if ($ExistingUrl) {
        Write-Host "PR deja ouverte: $ExistingUrl"
    } else {
        $CreateArguments = @("pr", "create", "--base", "main", "--head", $BranchName, "--title", $Title)
        if ($ResolvedBodyFile) { $CreateArguments += @("--body-file", $ResolvedBodyFile) }
        & gh @CreateArguments
        if ($LASTEXITCODE -ne 0) { throw "Impossible de creer la PR." }
    }
    exit 0
}

$RemoteUrl = (& git remote get-url origin) -join ""
$Repository = $RemoteUrl -replace '^git@github\.com:', '' -replace '^https://github\.com/', '' -replace '\.git$', ''
Write-Host "Branche poussee. GitHub CLI n'est pas connecte; ouvrez la PR ici:"
Write-Host "https://github.com/$Repository/compare/main...$($BranchName)?expand=1"
