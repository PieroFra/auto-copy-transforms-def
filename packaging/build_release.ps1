param(
    [string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe',
    [string]$Rar = '',
    [switch]$SkipRar
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$builder = Join-Path $PSScriptRoot 'build_extension.ps1'
$dist = Join-Path $root 'dist'
$source = Join-Path $root 'actd_build\auto_copy_transforms_def.py'
$license = Join-Path $root 'LICENSE'
$readme = Join-Path $PSScriptRoot 'README.txt'
$readmeIt = Join-Path $PSScriptRoot 'README.it.txt'

foreach ($requiredFile in @($builder, $source, $license, $readme, $readmeIt)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "File richiesto non trovato: $requiredFile"
    }
}

function Resolve-RarExecutable {
    param([string]$Name)

    if ([string]::IsNullOrWhiteSpace($Name)) {
        return $null
    }

    if (Test-Path -LiteralPath $Name -PathType Leaf) {
        return (Resolve-Path -LiteralPath $Name).Path
    }

    $command = Get-Command -Name $Name -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $command) {
        return $null
    }

    $executable = $command.Path
    if (-not $executable) {
        $executable = $command.Source
    }
    if (-not $executable) {
        throw "Impossibile determinare il percorso dell'eseguibile RAR: $Name"
    }
    return $executable
}

if ($SkipRar) {
    Write-Host '-SkipRar attivo: salto la ricerca di rar.exe/WinRAR e la creazione del RAR; si producono solo ZIP e SHA256.txt.'
    $rarExe = $null
} elseif ($Rar) {
    $rarExe = Resolve-RarExecutable -Name $Rar
    if (-not $rarExe) {
        throw "Eseguibile RAR non trovato: $Rar"
    }
} else {
    $rarExe = $null
    foreach ($candidate in @(
        'rar.exe',
        'WinRAR.exe',
        'C:\Program Files\WinRAR\Rar.exe',
        'C:\Program Files (x86)\WinRAR\Rar.exe'
    )) {
        $rarExe = Resolve-RarExecutable -Name $candidate
        if ($rarExe) {
            break
        }
    }
    if (-not $rarExe) {
        throw 'RAR non trovato: installa rar.exe/WinRAR.exe o passa -Rar <percorso o comando>.'
    }
}

& $builder -Blender $Blender
if ($LASTEXITCODE -ne 0) {
    throw 'Il builder ZIP Ã¨ terminato con un errore.'
}

$zip = Join-Path $dist 'auto_copy_transforms_def-1.1.5.zip'
if (-not (Test-Path -LiteralPath $zip -PathType Leaf)) {
    throw "ZIP atteso non trovato: $zip"
}

$rar = Join-Path $dist 'Auto_Copy_Transforms_DEF_1.1.5.rar'
$stage = Join-Path ([System.IO.Path]::GetTempPath()) ('actd_release_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dist -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stage 'legacy') -Force | Out-Null

try {
    Copy-Item -LiteralPath $zip -Destination $stage
    Copy-Item -LiteralPath $source -Destination (Join-Path $stage 'legacy\auto_copy_transforms_def.py')
    Copy-Item -LiteralPath $readme -Destination (Join-Path $stage 'README.txt')
    Copy-Item -LiteralPath $readmeIt -Destination (Join-Path $stage 'README.it.txt')
    Copy-Item -LiteralPath $license -Destination (Join-Path $stage 'LICENSE.txt')
    @'
A.C.T.D. versione 1.1.5

Installazione: installa l'add-on dal file ZIP incluso. In alternativa, nel RAR
installa legacy/auto_copy_transforms_def.py.

Documentazione: README.txt (inglese) e README.it.txt (italiano).
Licenza: GNU General Public License (GPL), consultare LICENSE.txt.
'@ | Set-Content -LiteralPath (Join-Path $stage 'LEGGIMI.txt') -Encoding UTF8

    $artefatti = @($zip)
    if ($rarExe) {
        Remove-Item -LiteralPath $rar -Force -ErrorAction SilentlyContinue
        Push-Location -LiteralPath $stage
        try {
            & $rarExe a -idq -o+ $rar `
                'auto_copy_transforms_def-1.1.5.zip' `
                'legacy\auto_copy_transforms_def.py' `
                'README.txt' 'README.it.txt' 'LICENSE.txt' 'LEGGIMI.txt'
            if ($LASTEXITCODE -ne 0) {
                throw "Creazione RAR fallita (exit code $LASTEXITCODE): $rar"
            }
        } finally {
            Pop-Location
        }

        if (-not (Test-Path -LiteralPath $rar -PathType Leaf)) {
            throw "RAR atteso non trovato: $rar"
        }
        $artefatti += $rar
        # Rimuove l'artefatto RAR superato dalla versione precedente.
        Remove-Item -LiteralPath (Join-Path $dist 'Auto_Copy_Transforms_DEF_1.1.1.rar') -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host 'RAR non generato (-SkipRar): in dist/ ci sono solo ZIP e SHA256.txt.'
    }

    $hashLines = foreach ($artifact in $artefatti) {
        $hash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
        "{0} *{1}" -f $hash, [System.IO.Path]::GetFileName($artifact)
    }
    Set-Content -LiteralPath (Join-Path $dist 'SHA256.txt') -Value $hashLines -Encoding ASCII
    Write-Host "Pacchetti locali pronti in: $dist"
} finally {
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
}
