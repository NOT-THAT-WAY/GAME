[CmdletBinding()]
param(
    [ValidateSet("Configure", "Pull", "Push", "Track", "Status")]
    [string]$Action = "Status",
    [string]$RemoteUrl,
    [string]$EndpointUrl,
    [string]$Profile,
    [string]$Path
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RemoteName = "assets"
Set-Location $RepoRoot

function Invoke-Dvc([string[]]$DvcArguments) {
    & dvc @DvcArguments
    if ($LASTEXITCODE -ne 0) { throw "DVC a echoue: dvc $($DvcArguments -join ' ')" }
}

function Test-DvcRemote {
    $RemoteList = (& dvc remote list 2>$null) -join "`n"
    return ($LASTEXITCODE -eq 0 -and $RemoteList -match "(?m)^$RemoteName\s")
}

function Assert-DvcRemote {
    if (-not (Test-DvcRemote)) { throw "Remote '$RemoteName' non configure. Lancez d'abord -Action Configure." }
}

if (-not (Get-Command dvc -ErrorAction SilentlyContinue)) {
    throw "DVC est absent. Relancez setup-windows.ps1 -InstallTools."
}
if (-not (Test-Path (Join-Path $RepoRoot ".dvc\config"))) {
    throw "Le depot DVC n'est pas initialise."
}

switch ($Action) {
    "Configure" {
        if (-not $RemoteUrl) { throw "-RemoteUrl est requis pour Configure." }
        Invoke-Dvc @("remote", "add", "--local", "--force", "--default", $RemoteName, $RemoteUrl)
        if ($EndpointUrl) { Invoke-Dvc @("remote", "modify", "--local", $RemoteName, "endpointurl", $EndpointUrl) }
        if ($Profile) { Invoke-Dvc @("remote", "modify", "--local", $RemoteName, "profile", $Profile) }
        Write-Host "Remote DVC '$RemoteName' configure localement. Aucun credential n'est ajoute a Git."
    }

    "Pull" {
        Assert-DvcRemote
        $DvcArguments = @("pull", "--remote", $RemoteName)
        if ($Path) { $DvcArguments += $Path }
        Invoke-Dvc $DvcArguments
    }

    "Push" {
        Assert-DvcRemote
        $DvcArguments = @("push", "--remote", $RemoteName)
        if ($Path) { $DvcArguments += $Path }
        Invoke-Dvc $DvcArguments
        Write-Host "Contenu envoye. Committez les pointeurs .dvc et le registre avant git push."
    }

    "Track" {
        if (-not $Path) { throw "-Path est requis pour Track." }
        $ResolvedTarget = (Resolve-Path $Path).Path
        $TargetItem = Get-Item $ResolvedTarget
        if ($TargetItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Les liens symboliques ne sont pas acceptes comme lots d'assets."
        }

        $RepoPrefix = $RepoRoot.TrimEnd('\') + '\'
        if (-not $ResolvedTarget.StartsWith($RepoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Le lot doit etre dans le depot, sous ExternalAssets/."
        }
        $RelativePath = $ResolvedTarget.Substring($RepoPrefix.Length).Replace('\', '/')
        if ($RelativePath -notmatch '^ExternalAssets/[^/]+/.+') {
            throw "Utilisez ExternalAssets/<Discipline>/<AssetId>, pas un dossier global."
        }

        Invoke-Dvc @("add", $RelativePath)
        Write-Host "`nLot indexe: $RelativePath"
        Write-Host "Etapes suivantes: mettre a jour le registre, lancer -Action Push, puis committer les pointeurs.`n"
        & git status --short -- "$RelativePath.dvc" "$(Split-Path $RelativePath -Parent)/.gitignore" "docs/assets/ASSET_REGISTER.md"
    }

    "Status" {
        Write-Host "DVC $(& dvc --version)"
        Invoke-Dvc @("status")
        if (Test-DvcRemote) {
            Write-Host "`nComparaison avec le remote:"
            Invoke-Dvc @("status", "--cloud", "--remote", $RemoteName)
        } else {
            Write-Host "`nRemote '$RemoteName' non configure sur cette machine."
        }
    }
}
