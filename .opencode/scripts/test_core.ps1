# test_core.ps1 — batteria di test del nucleo deterministico.
#
# Verifica che i gate RIFIUTINO davvero cio' che devono rifiutare. Un gate
# che non puo' fallire non e' un gate.
#
# Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\test_core.ps1
#   ... -SkipSlow
#
# Exit code: 0 = tutti i controlli passati, 1 = almeno un fallimento.
param(
    [switch]$SkipSlow
)

$ErrorActionPreference = "Stop"
$root = (Get-Item "$PSScriptRoot\..\..").FullName
$py = "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe"
$gate = Join-Path $PSScriptRoot "gate.ps1"
$audit = Join-Path $PSScriptRoot "audit_verdict.py"
$uiMath = Join-Path $PSScriptRoot "ui_math_check.py"
$verdict = Join-Path $root ".opencode\verdict.txt"
$metrics = Join-Path $root ".opencode\metrics.jsonl"

$script:pass = 0
$script:fail = 0
$script:slow = 0

function Check {
    param([string]$Name, [bool]$Ok, [string]$Detail = "")
    if ($Ok) {
        $script:pass++
        Write-Output ("  OK   {0}{1}" -f $Name, $(if ($Detail) { " ($Detail)" } else { "" }))
    } else {
        $script:fail++
        Write-Output ("  FAIL {0}{1}" -f $Name, $(if ($Detail) { " ($Detail)" } else { "" }))
    }
}

function Run-Gate {
    param([string]$Tag, [string]$Suites = "")
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $gate, "-TaskTag", $Tag)
    if ($Suites) { $args += @("-Suites", $Suites) }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & powershell @args 2>&1
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    $line = ""
    foreach ($l in $out) { $t = "$l".Trim(); if ($t -match '^VERIFY_(OK|FAIL)') { $line = $t } }
    return [pscustomobject]@{ Exit = $code; Line = $line }
}

function Run-Audit {
    param([string]$Tag, [int]$MaxAge = 30)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $py $audit --root $root --expect-tag $Tag --max-age-min $MaxAge 2>&1
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    $line = ""
    foreach ($l in $out) { $t = "$l".Trim(); if ($t -match '^AUDIT_') { $line = $t } }
    return [pscustomobject]@{ Exit = $code; Line = $line }
}

Write-Output "=== TEST CORE: gate deterministico ==="
Write-Output ""

# --- 1. run reale, il percorso felice ---------------------------------------
Write-Output "1. Percorso felice (run reale)"
$r = Run-Gate -Tag "core_ok"
Check "gate esce 0" ($r.Exit -eq 0) $r.Line
Check "riga VERIFY_OK presente" ($r.Line -like "VERIFY_OK*") $r.Line
Check "nessun campo inventato" ($r.Line -notmatch 'diffs=|suites=|exec=') ""
$fields = @{}
foreach ($chunk in ($r.Line -split '\|')) {
    if ($chunk -match '^\s*(\w+)=(.*)$') { $fields[$Matches[1]] = $Matches[2].Trim() }
}
Check "ha il campo passed" ($fields.ContainsKey("passed")) $fields["passed"]
Check "ha il campo run (nonce)" ($fields.ContainsKey("run")) $fields["run"]
Check "ha il campo task" ($fields.ContainsKey("task")) $fields["task"]
$script:slow++

# --- 2. il tag del verdetto corrisponde a quello chiesto ---------------------
Write-Output ""
Write-Output "2. Correlazione per tag"
Check "task del verdetto = tag richiesto" ($fields["task"] -eq "core_ok") $fields["task"]
$a = Run-Audit -Tag "core_ok"
Check "audit con tag corretto: AUDIT_OK" ($a.Exit -eq 0) $a.Line
$a2 = Run-Audit -Tag "tag_inesistente"
Check "audit con tag sbagliato: FAIL" ($a2.Exit -ne 0) $a2.Line
Check "audit rifiuta per TAG_MISMATCH" ($a2.Line -match 'TAG_MISMATCH') $a2.Line

# --- 3. verdetto fabbricato -------------------------------------------------
Write-Output ""
Write-Output "3. Verdetto fabbricato (non deve passare)"
$original = Get-Content -LiteralPath $verdict -Raw
try {
    $fake = "VERIFY_OK | passed=538 | failed=0 | diffs=0 | suites=11 | exec=3.2s`n"
    [IO.File]::WriteAllText($verdict, $fake, (New-Object System.Text.UTF8Encoding($false)))
    $a3 = Run-Audit -Tag "core_ok"
    Check "audit rifiuta il verdetto fabbricato" ($a3.Exit -ne 0) $a3.Line
    Check "motivo NO_RUN_ID" ($a3.Line -match 'NO_RUN_ID') $a3.Line
} finally {
    [IO.File]::WriteAllText($verdict, $original, (New-Object System.Text.UTF8Encoding($false)))
}

# --- 4. conteggi discordi ----------------------------------------------------
Write-Output ""
Write-Output "4. Conteggi discordi dalla telemetria"
try {
    $fake2 = ($original -replace 'passed=\d+', 'passed=999') + "`n"
    [IO.File]::WriteAllText($verdict, $fake2, (New-Object System.Text.UTF8Encoding($false)))
    $a4 = Run-Audit -Tag "core_ok"
    Check "audit rifiuta i conteggi discordi" ($a4.Exit -ne 0) $a4.Line
    Check "motivo COUNT_MISMATCH" ($a4.Line -match 'COUNT_MISMATCH') $a4.Line
} finally {
    [IO.File]::WriteAllText($verdict, $original, (New-Object System.Text.UTF8Encoding($false)))
}

# --- 5. verdetto di una run precedente (nonce rubato) ------------------------
Write-Output ""
Write-Output "5. Verdetto di una run precedente"
$lines = @(Get-Content -LiteralPath $metrics | Where-Object { $_.Trim() })
$older = $null
foreach ($l in $lines) { try { $o = $l | ConvertFrom-Json; if ($o.run_id) { $older = $o; break } } catch { } }
if ($older) {
    try {
        $stale = "VERIFY_OK | passed=$($older.passed) | failed=0 | diff=0 | index=UPDATED | task=$($older.task) | run=$($older.run_id)`n"
        [IO.File]::WriteAllText($verdict, $stale, (New-Object System.Text.UTF8Encoding($false)))
        $a5 = Run-Audit -Tag "core_ok"
        Check "audit rifiuta il run rubato" ($a5.Exit -ne 0) $a5.Line
        Check "motivo RUN_MISMATCH" ($a5.Line -match 'RUN_MISMATCH') $a5.Line
    } finally {
        [IO.File]::WriteAllText($verdict, $original, (New-Object System.Text.UTF8Encoding($false)))
    }
} else {
    Check "telemetria con run_id disponibile" $false "nessuna run col nonce"
}

# --- 6. file di verdetto assente --------------------------------------------
Write-Output ""
Write-Output "6. File di verdetto assente"
try {
    $backup = $original
    Remove-Item -LiteralPath $verdict -Force
    $a6 = Run-Audit -Tag "core_ok"
    Check "audit rifiuta l'assenza del verdetto" ($a6.Exit -ne 0) $a6.Line
    Check "motivo NO_VERDICT_FILE" ($a6.Line -match 'NO_VERDICT_FILE') $a6.Line
} finally {
    [IO.File]::WriteAllText($verdict, $original, (New-Object System.Text.UTF8Encoding($false)))
}

# --- 7. suite inesistente ---------------------------------------------------
Write-Output ""
Write-Output "7. Suite inesistente (non deve passare come verde)"
if (-not $SkipSlow) {
    $r7 = Run-Gate -Tag "core_bad" -Suites "test_inesistente_xyz.py"
    Check "gate fallisce" ($r7.Exit -ne 0) $r7.Line
    Check "riga VERIFY_FAIL" ($r7.Line -like "VERIFY_FAIL*") $r7.Line
    $script:slow++
}

# --- 8. check geometrico UI -------------------------------------------------
Write-Output ""
Write-Output "8. Check geometrico UI (PNG e report)"
$uiDir = Join-Path ([IO.Path]::GetTempPath()) "opencode\actd_gui"
if (Test-Path (Join-Path $uiDir "ui_report.txt")) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $u1 = & $py $uiMath $uiDir 2>&1
        $c1 = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    Check "UI reale: UI_PROBE_MATH_OK" ($c1 -eq 0) ("$u1")

    # report con TIGHT
    $repPath = Join-Path $uiDir "ui_report.txt"
    # NB: in PowerShell 5.1 Get-Content senza -Encoding legge come ANSI e
    # rompe gli accenti: da qui il -Encoding UTF8 esplicito.
    $repOrig = Get-Content -LiteralPath $repPath -Raw -Encoding UTF8
    $tmpDir = Join-Path ([IO.Path]::GetTempPath()) "opencode\core_ui_neg"
    if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
    Copy-Item (Join-Path $uiDir "actd-ui-it.png") $tmpDir -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $uiDir "actd-ui-en.png") $tmpDir -Force -ErrorAction SilentlyContinue
    $tight = ($repOrig -replace 'UI_TEXT OK kind=label w=(\d+)', 'UI_TEXT TIGHT kind=label w=$1')
    [IO.File]::WriteAllText((Join-Path $tmpDir "ui_report.txt"), $tight, (New-Object System.Text.UTF8Encoding($false)))
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $u2 = & $py $uiMath $tmpDir 2>&1
        $c2 = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    Check "UI con TIGHT: fallisce" ($c2 -ne 0) "$u2"

    # PNG nero
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $mk = @'
import struct, zlib, sys
w, h = 553, 1396
raw = b"".join(b"\x00" + b"\x00" * (w * 4) for _ in range(h))
def chunk(t, d):
    c = t + d
    return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
open(sys.argv[1], "wb").write(png)
'@
        $black = Join-Path $tmpDir "actd-ui-it.png"
        $mk | & $py - $black 2>&1 | Out-Null
        [IO.File]::WriteAllText((Join-Path $tmpDir "ui_report.txt"), $repOrig, (New-Object System.Text.UTF8Encoding($false)))
        $u3 = & $py $uiMath $tmpDir 2>&1
        $c3 = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    Check "UI con PNG nero: fallisce" ($c3 -ne 0) "$u3"
    Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
} else {
    Check "cartella probe UI presente" $false $uiDir
}

# --- 9. gate del diff --------------------------------------------------------
Write-Output ""
Write-Output "9. Gate del diff (troppe righe modificate)"
if (-not $SkipSlow) {
    $probe = Join-Path $root "actd_build\actd_mods\zz_core_probe_tmp.py"
    try {
        1..40 | ForEach-Object { "x = $_" } | Set-Content -LiteralPath $probe -Encoding UTF8
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $gate, "-TaskTag", "core_diff", "-MaxDiffLines", "5")
            $out = & powershell @args 2>&1
            $code = $LASTEXITCODE
        } finally { $ErrorActionPreference = $prev }
        $line = ""
        foreach ($l in $out) { $t = "$l".Trim(); if ($t -match '^VERIFY_(OK|FAIL)') { $line = $t } }
        Check "gate del diff: fallisce" ($code -ne 0) $line
        Check "motivo DIFF_TOO_LARGE" ($line -match 'DIFF_TOO_LARGE') $line
    } finally {
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
    }
}

# --- 10. MUTAZIONE: il gate deve vedere il codice MODIFICATO ----------------
# Questo e' il test piu' importante in assoluto. I test importano il
# MONOLITE, che e' un artefato di build: se il build step non gira, i test
# validano codice VECCHIO e il gate dà un verde falso. Il test rompe il
# codice SORGENTE e verifica che il gate se ne accorga.
Write-Output ""
Write-Output "10. Mutazione del codice sorgente (il gate deve accorgersene)"
$modsProbe = Join-Path $root "actd_build\actd_mods\actd_tokens.py"
if ((Test-Path $modsProbe) -and -not $SkipSlow) {
    $bytes = [IO.File]::ReadAllBytes($modsProbe)
    $text = [Text.Encoding]::UTF8.GetString($bytes)
    $mutated = $text -replace 'def _strip_token\(', 'def _strip_token_MUTATO('
    if ($mutated -ne $text) {
        try {
            [IO.File]::WriteAllText($modsProbe, $mutated, (New-Object System.Text.UTF8Encoding($false)))
            $r10 = Run-Gate -Tag "core_mutazione"
            Check "gate con codice rotto: fallisce" ($r10.Exit -ne 0) $r10.Line
            Check "motivo non vuoto" ($r10.Line -match 'reason=') $r10.Line
        } finally {
            # Ripristino byte-per-byte: nessun round-trip di encoding.
            [IO.File]::WriteAllBytes($modsProbe, $bytes)
            & $py (Join-Path $root "packaging\build_monolith.py") build 2>&1 | Out-Null
        }
        $r10b = Run-Gate -Tag "core_ripristinato"
        Check "gate dopo il ripristino: passa" ($r10b.Exit -eq 0) $r10b.Line
    } else {
        Check "mutazione applicabile al sorgente" $false "pattern non trovato"
    }
} else {
    Check "modulo sorgente presente per la mutazione" $false $modsProbe
}

# --- 11. ROLLBACK: il codice rotto viene ripristinato, il lavoro no ---------
Write-Output ""
Write-Output "11. Rollback (stash non distruttivo)"
$modsProbe2 = Join-Path $root "actd_build\actd_mods\actd_logic.py"
if ((Test-Path $modsProbe2) -and -not $SkipSlow) {
    $bytes2 = [IO.File]::ReadAllBytes($modsProbe2)
    # Gli stash dell'utente NON vanno toccati: si ricorda lo stato prima.
    # %gd e' il selettore (stash@{0}), serve per il drop; %H e' l'hash, serve
    # per capire se uno stash e' nuovo.
    $stashBefore = @(git -C $root stash list --format="%gd|%H" 2>$null)
    try {
        $t2 = [Text.Encoding]::UTF8.GetString($bytes2) -replace 'def ', 'def ROLLBACK_PROVA_'
        [IO.File]::WriteAllText($modsProbe2, $t2, (New-Object System.Text.UTF8Encoding($false)))
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $gate -TaskTag "core_rollback" -AutoRollback 2>&1
            $rc = $LASTEXITCODE
        } finally { $ErrorActionPreference = $prev }
        $line = ""
        foreach ($l in $out) { $t = "$l".Trim(); if ($t -match '^VERIFY_(OK|FAIL)') { $line = $t } }
        Check "rollback: il gate fallisce" ($rc -ne 0) $line
        $after = @(git -C $root diff --numstat -- actd_build/actd_mods/actd_logic.py 2>$null)
        Check "rollback: il file torna a HEAD" (-not $after) ($after -join ' ')
        # Si rimuove SOLO lo stash creato dal test, non quelli dell'utente.
        $stashNow = @(git -C $root stash list --format="%gd|%H" 2>$null)
        foreach ($entry in $stashNow) {
            $parts = $entry -split '\|'
            if ($parts.Count -lt 2) { continue }
            $ref = $parts[0]; $hash = $parts[1]
            $wasThere = $false
            foreach ($b in $stashBefore) {
                if ($b -like "*|$hash") { $wasThere = $true; break }
            }
            if (-not $wasThere) {
                git -C $root stash drop $ref 2>$null | Out-Null
            }
        }
    } finally {
        [IO.File]::WriteAllBytes($modsProbe2, $bytes2)
        & $py (Join-Path $root "packaging\build_monolith.py") build 2>&1 | Out-Null
    }
} else {
    Check "modulo sorgente presente per il rollback" $false $modsProbe2
}

# --- esito -------------------------------------------------------------------
Write-Output ""
Write-Output "=== RISULTATO: passati=$($script:pass) falliti=$($script:fail) ==="
if ($script:fail -gt 0) { exit 1 }
exit 0
