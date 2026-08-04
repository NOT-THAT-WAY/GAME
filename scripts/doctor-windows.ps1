[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ToolchainPath = Join-Path $RepoRoot "config\toolchain.env"
$Toolchain = @{}
Get-Content $ToolchainPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.+)$') { $Toolchain[$Matches[1]] = $Matches[2] }
}
$ExpectedUnity = $Toolchain["UNITY_VERSION"]
$ExpectedDvcMajor = $Toolchain["DVC_MAJOR_VERSION"]
$DefaultEditor = "C:\Program Files\Unity\Hub\Editor\$ExpectedUnity\Editor\Unity.exe"
$UnityEditor = if ($env:GAME_UNITY_EDITOR) { $env:GAME_UNITY_EDITOR } else { $DefaultEditor }
$ErrorCount = 0
$WarningCount = 0

function Write-Ok([string]$Message) { Write-Host "[OK]   $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { $script:WarningCount++; Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Fail([string]$Message) { $script:ErrorCount++; Write-Host "[FAIL] $Message" -ForegroundColor Red }
function Test-Command([string]$Name) { return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

Write-Host "GAME doctor - Windows"
Write-Host "Projet: $RepoRoot"
Write-Host "Unity attendue: $ExpectedUnity`n"

if ($env:OS -eq "Windows_NT") { Write-Ok "Windows detecte" } else { Write-Fail "Ce diagnostic est reserve a Windows" }

if ($RepoRoot -match 'OneDrive|Dropbox|iCloud|Google Drive') { Write-Warn "Le depot semble place dans un dossier synchronise" } else { Write-Ok "Depot hors des dossiers synchronises courants" }

if (Test-Command "git") {
    $GitVersion = (& git --version 2>$null)
    Write-Ok $GitVersion
} else { Write-Fail "Git absent" }

if (Test-Command "git-lfs") {
    $LfsVersion = (& git lfs version 2>$null)
    Write-Ok $LfsVersion
} else { Write-Fail "Git LFS absent" }

if (Test-Command "dvc") {
    $DvcVersion = (& dvc --version 2>$null) -join ""
    if ($DvcVersion -match "^$([regex]::Escape($ExpectedDvcMajor))\.") { Write-Ok "DVC $DvcVersion" } else { Write-Fail "DVC majeur $ExpectedDvcMajor attendu, version trouvee: $DvcVersion" }
} else { Write-Fail "DVC absent" }

$HubCandidates = @(
    "$env:ProgramFiles\Unity Hub\Unity Hub.exe",
    "${env:ProgramFiles(x86)}\Unity Hub\Unity Hub.exe",
    "$env:LOCALAPPDATA\Programs\Unity Hub\Unity Hub.exe"
)
if ($HubCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1) { Write-Ok "Unity Hub installe" } else { Write-Fail "Unity Hub absent" }

$SmartMerge = $null
if (Test-Path $UnityEditor) {
    Write-Ok "Unity $ExpectedUnity trouve"
    $SmartMerge = Join-Path (Split-Path $UnityEditor -Parent) "Data\Tools\UnityYAMLMerge.exe"
    if (Test-Path $SmartMerge) { Write-Ok "UnityYAMLMerge trouve" } else { Write-Fail "UnityYAMLMerge introuvable" }
} else { Write-Fail "Unity $ExpectedUnity absent (ou GAME_UNITY_EDITOR incorrect)" }

Set-Location $RepoRoot
if (Test-Command "git") {
    & git rev-parse --is-inside-work-tree *> $null
    if ($LASTEXITCODE -eq 0) { Write-Ok "Depot Git valide" } else { Write-Fail "Le dossier n'est pas un depot Git" }

    & git lfs env *> $null
    if ($LASTEXITCODE -eq 0) { Write-Ok "Git LFS initialise pour le depot" } else { Write-Fail "Git LFS non initialise" }

    $LfsAttribute = (& git check-attr filter -- Assets/_Project/Test.png 2>$null) -join " "
    if ($LfsAttribute -match ': lfs$') { Write-Ok "Regles Git LFS actives" } else { Write-Fail "Les regles Git LFS ne s'appliquent pas" }

    $Forbidden = & git ls-files | Where-Object { $_ -match '(^|/)(Library|Temp|Obj|Logs|UserSettings|Build|Builds)(/|$)' } | Select-Object -First 5
    if ($Forbidden) { Write-Fail "Caches Unity suivis par Git: $($Forbidden -join ', ')" } else { Write-Ok "Aucun cache Unity suivi par Git" }

    $MergeDriver = (& git config --local --get merge.unityyamlmerge.driver 2>$null) -join ""
    if ($MergeDriver) { Write-Ok "UnityYAMLMerge configure dans ce depot" } elseif ($SmartMerge) { Write-Warn "Relancer setup-windows.ps1 pour configurer Smart Merge" } else { Write-Warn "Smart Merge sera configure apres l'installation Unity" }

    $HooksPath = (& git config --local --get core.hooksPath 2>$null) -join ""
    if ($HooksPath -eq ".githooks" -and (Test-Path ".githooks\pre-commit") -and (Test-Path ".githooks\pre-push")) { Write-Ok "Gardes-fous commit/push et hook Git LFS actifs" } else { Write-Warn "Gardes-fous Git inactifs; relancer setup-windows.ps1" }

    if (Test-Path ".dvc\config") { Write-Ok "Projet DVC initialise" } else { Write-Fail "Configuration .dvc\config absente" }
    if (Test-Command "dvc") {
        $DvcRemotes = (& dvc remote list 2>$null) -join "`n"
        if ($LASTEXITCODE -eq 0 -and $DvcRemotes -match '(?m)^assets\s') {
            Write-Ok "Remote externe 'assets' configure localement"
        } else {
            $DvcPointers = @(& git ls-files "*.dvc" | Where-Object { $_ -notmatch '^\.dvc/' })
            if ($DvcPointers.Count -gt 0) { Write-Fail "Des assets DVC existent mais le remote 'assets' n'est pas configure" } else { Write-Warn "Remote externe 'assets' non configure - aucun master n'est encore requis" }
        }
    }

    $GitName = (& git config --get user.name 2>$null) -join ""
    $GitEmail = (& git config --get user.email 2>$null) -join ""
    if ($GitName -and $GitEmail) { Write-Ok "Identite Git configuree" } else { Write-Warn "Nom ou email Git non configure" }
}

$VsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $VsWhere) { Write-Ok "Visual Studio detecte" } else { Write-Warn "Visual Studio 2022 non detecte" }

$WwiseCandidates = @(
    "${env:ProgramFiles(x86)}\Audiokinetic\Launcher\WwiseLauncher.exe",
    "$env:ProgramFiles\Audiokinetic\Launcher\WwiseLauncher.exe"
)
if ($WwiseCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1) { Write-Ok "Wwise Launcher present (poste audio de Nils)" } else { Write-Warn "Wwise Launcher absent - normal hors poste audio de Nils" }

if ((Test-Path "${env:ProgramFiles(x86)}\Steam\steam.exe") -or (Test-Path "$env:ProgramFiles\Steam\steam.exe")) { Write-Ok "Steam present (gate Steam)" } else { Write-Warn "Steam non installe - normal avant la gate Steam" }

Write-Host "`nResultat: $ErrorCount erreur(s), $WarningCount avertissement(s)."
if ($ErrorCount -gt 0) { exit 1 }
