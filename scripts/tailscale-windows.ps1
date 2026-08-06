[CmdletBinding()]
param(
    [ValidateSet("Status", "Ip", "Ping")]
    [string]$Action = "Status",
    [string]$PeerAddress
)

$ErrorActionPreference = "Stop"

function Find-TailscaleCli {
    if ($env:GAME_TAILSCALE_CLI -and (Test-Path $env:GAME_TAILSCALE_CLI)) {
        return $env:GAME_TAILSCALE_CLI
    }

    $Candidates = @(
        (Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Tailscale\tailscale.exe")
    )
    $Command = Get-Command tailscale.exe -ErrorAction SilentlyContinue
    if ($Command) { $Candidates += $Command.Source }

    return $Candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

$TailscaleCli = Find-TailscaleCli
if (-not $TailscaleCli) { throw "Tailscale est absent. Relancez setup-windows.ps1 -RemotePlay." }

$StatusOutput = (& $TailscaleCli status --json 2>$null) -join "`n"
if ($LASTEXITCODE -ne 0 -or -not $StatusOutput) { throw "Impossible de lire l'etat Tailscale." }
$Status = $StatusOutput | ConvertFrom-Json
if ($Status.BackendState -ne "Running") {
    throw "Tailscale n'est pas connecte (etat: $($Status.BackendState)). Ouvrez Tailscale et rejoignez le tailnet de l'equipe."
}

$TailscaleIp = ((& $TailscaleCli ip -4 2>$null) | Select-Object -First 1)
if ($LASTEXITCODE -ne 0 -or -not $TailscaleIp) { throw "Aucune IPv4 Tailscale attribuee." }

switch ($Action) {
    "Status" { Write-Host "Tailscale connecte: $TailscaleIp" }
    "Ip" { Write-Output $TailscaleIp }
    "Ping" {
        if (-not $PeerAddress) { throw "L'action Ping attend -PeerAddress HOST_IP." }
        # --until-direct=false comme sur macOS: un lien relaye par DERP suffit a
        # prouver que l'hote repond. Sans ce drapeau, tailscale n'accepte qu'une
        # connexion directe et un poste derriere un NAT strict serait declare muet.
        & $TailscaleCli ping --c 1 --until-direct=false --timeout 5s $PeerAddress
        if ($LASTEXITCODE -ne 0) { throw "La machine Tailscale $PeerAddress ne repond pas." }
    }
}
