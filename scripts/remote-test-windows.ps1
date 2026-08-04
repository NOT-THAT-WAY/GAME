[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("Host", "Client")]
    [string]$Role,
    [string]$Address,
    [ValidateRange(1, 65535)]
    [int]$Port = 7770,
    [string]$Name = $env:USERNAME,
    [switch]$SkipBuild,
    [switch]$BuildOnly,
    [Alias("Profile")]
    [ValidateSet("Connection", "Maze")]
    [string]$TestProfile = "Connection"
)

$ErrorActionPreference = "Stop"
$TailscaleScript = Join-Path $PSScriptRoot "tailscale-windows.ps1"
$ConnectionScript = Join-Path $PSScriptRoot "first-test-windows.ps1"
$LocalTailscaleIp = (& $TailscaleScript -Action Ip) -join ""

if ($Role -eq "Host") {
    Write-Host "Adresse distante de l'hote: $LocalTailscaleIp (a partager uniquement avec l'equipe)"
} else {
    if (-not $Address) { throw "Le client attend -Address TAILSCALE_HOST_IP." }
    Write-Host "Verification Tailscale de l'hote $Address..."
    & $TailscaleScript -Action Ping -PeerAddress $Address
    if ($LASTEXITCODE -ne 0) { throw "La verification Tailscale a echoue." }
}

$ConnectionArguments = @{
    Role = $Role
    Port = $Port
    Name = $Name
    TestProfile = $TestProfile
}
if ($Address) { $ConnectionArguments["Address"] = $Address }
if ($SkipBuild) { $ConnectionArguments["SkipBuild"] = $true }
if ($BuildOnly) { $ConnectionArguments["BuildOnly"] = $true }

& $ConnectionScript @ConnectionArguments
exit $LASTEXITCODE
