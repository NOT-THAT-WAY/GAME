# Les regles de branche, de titre de PR et de contrat du depot vivent dans les
# scripts .sh de ce dossier: ce sont exactement ceux que macOS et la CI executent.
# Windows les appelle au lieu de les reecrire, sinon une regle modifiee d'un seul
# cote fait diverger les deux plateformes sans que rien ne le signale.
#
# Git for Windows fournit bash, mais ne le place pas toujours dans le PATH et ne
# s'installe pas toujours dans C:\Program Files\Git. La resolution part donc de
# l'emplacement reel de git.exe avant de retomber sur les chemins habituels.

function Resolve-Bash {
    $Command = Get-Command bash -ErrorAction SilentlyContinue
    if ($Command) { return $Command.Source }

    $Candidates = @()
    $Git = Get-Command git -ErrorAction SilentlyContinue
    if ($Git) {
        $GitRoot = Split-Path (Split-Path $Git.Source -Parent) -Parent
        $Candidates += (Join-Path $GitRoot "bin\bash.exe")
    }

    $Bases = @()
    if ($env:ProgramFiles) { $Bases += $env:ProgramFiles }
    if (${env:ProgramFiles(x86)}) { $Bases += ${env:ProgramFiles(x86)} }
    if ($env:LOCALAPPDATA) { $Bases += (Join-Path $env:LOCALAPPDATA "Programs") }
    foreach ($Base in $Bases) { $Candidates += (Join-Path $Base "Git\bin\bash.exe") }

    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) { return $Candidate }
    }

    throw "bash est introuvable. Il est fourni par Git for Windows: reinstallez Git ou ajoutez son dossier bin au PATH."
}

# Le chemin est relatif a la racine du depot; les appelants font Set-Location avant.
function Invoke-SharedValidator([string]$RelativePath, [string[]]$Arguments = @()) {
    $Bash = Resolve-Bash
    & $Bash $RelativePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$RelativePath a refuse la verification (code $LASTEXITCODE)." }
}
