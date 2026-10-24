# run_scout.ps1 — Scout AST: mappa Simbolo -> Righe del monolite A.C.T.D.
#
# Non carica il codice dell'addon nella memoria dell'Architetto: restituisce
# solo nome, tipo e intervallo di righe, letti con il modulo `ast`.
#
# Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\run_scout.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\run_scout.ps1 -Filter Panel
#   powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\run_scout.ps1 -Line 3200
param(
  [string]$File = 'actd_build\auto_copy_transforms_def.py',
  # Nome breve del modulo (es. registry, tokens, ui): evita che il modello
  # locale debba scrivere percorsi, che sbaglia.
  [string]$Mod = '',
  [string]$Filter = '',
  [int]$Line = 0,
  [int]$Max = 60,
  # Se valorizzato, la mappa viene scritta in questo file e su stdout resta
  # solo una riga di riepilogo: evita che il Tester locale la ripeta a parole.
  [string]$Out = ''
)

if ($Mod) {
  $base = Join-Path $PSScriptRoot '..\..\actd_build\actd_mods'
  $cand = Join-Path $base ("actd_{0}.py" -f $Mod)
  if (-not (Test-Path $cand)) { $cand = Join-Path $base ("{0}.py" -f $Mod) }
  if (Test-Path $cand) { $File = (Resolve-Path $cand).Path }
  else {
    Write-Output ("SCOUT_ERROR modulo sconosciuto: {0} (disponibili: {1})" -f $Mod, (((Get-ChildItem $base -Filter '*.py').BaseName) -join ', '))
    exit 2
  }
}

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'

# 'python' nel PATH e' la stub del Microsoft Store: usa il percorso completo.
$py = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe'
if (-not (Test-Path $py)) { throw "Python di Blender non trovato: $py" }

$callArgs = @((Join-Path $PSScriptRoot 'scout_ast.py'), $File)
if ($Filter) { $callArgs += @('--filter', $Filter) }
if ($Line -gt 0) { $callArgs += @('--line', "$Line") }
if ($Max -gt 0) { $callArgs += @('--max', "$Max") }

$result = & $py @callArgs
if ($Out) {
  # Scrittura senza BOM: il file viene letto da Python/Blender e dall'Architetto.
  [IO.File]::WriteAllText($Out, (($result | Out-String).TrimEnd() + "`n"), (New-Object System.Text.UTF8Encoding($false)))
  $n = (@($result) | Select-String 'SIMBOLO').Count
  Write-Output "SCOUT_OUT $Out simboli=$n"
} else {
  $result
}
exit $LASTEXITCODE