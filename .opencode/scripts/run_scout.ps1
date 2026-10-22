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
  [string]$Filter = '',
  [int]$Line = 0,
  [int]$Max = 60
)

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'

# 'python' nel PATH e' la stub del Microsoft Store: usa il percorso completo.
$py = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe'
if (-not (Test-Path $py)) { throw "Python di Blender non trovato: $py" }

$callArgs = @((Join-Path $PSScriptRoot 'scout_ast.py'), $File)
if ($Filter) { $callArgs += @('--filter', $Filter) }
if ($Line -gt 0) { $callArgs += @('--line', "$Line") }
if ($Max -gt 0) { $callArgs += @('--max', "$Max") }

& $py @callArgs
exit $LASTEXITCODE
