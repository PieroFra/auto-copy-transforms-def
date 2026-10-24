# verify.ps1 — verifica deterministica, riusabile in ogni progetto addon.
#
# Un solo punto di verita': compila, controlla l'ampiezza del diff, rigenera
# l'indice AST, lancia i test e scrive la telemetria. Il verdetto e' deciso
# dal codice (exit code + riga finale), mai da un modello.
#
# Configurazione per progetto: .opencode\verify.config.psd1
#   Monolith       string   percorso del file sorgente principale (relativo)
#   Sources        string[] altri sorgenti da compilare (relativi)
#   Runner         string   script PowerShell che lancia i test
#   RunnerArgs     string[] argomenti aggiuntivi per il runner
#   ExpectedTotal  int      attesi totali (0 = non controllare)
#   DiffPaths      string[] path sui quali misurare il diff
#   IndexOutput    string   dove scrivere l'indice AST ("" = disabilitato)
#
# Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\verify.ps1
#   ... -TaskTag d1 -Suites test_a.py,test_b.py -MaxDiffLines 150
#
# Exit code: 0 = VERIFY_OK, 1 = VERIFY_FAIL, 2 = DIFF_TOO_LARGE
param(
    [string]$TaskTag = "manual",
    [string]$Suites = "",
    # Soglia del diff: 150 era la soglia storica (anti-refactoring a tappeto),
    # poi 250, poi 600: la fase REPLACE (f4a) ha un diff legittimo di ~457
    # righe (operatori + test_mod6 + monolite generato).
    [int]$MaxDiffLines = 600,
    [switch]$AutoRollback,
    [switch]$SkipTests,
    [switch]$SkipIndex,
    [string]$Agent = "",
    [string]$Config = "",
    [string]$Build = ""
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$root = (Get-Item "$PSScriptRoot\..\..").FullName
if (-not $Config) { $Config = Join-Path $root ".opencode\verify.config.psd1" }

# --- configurazione ----------------------------------------------------------
$cfg = $null
if (Test-Path -LiteralPath $Config) {
    $cfg = Import-PowerShellDataFile -LiteralPath $Config -ErrorAction SilentlyContinue
    if (-not $cfg) {
        # Import-PowerShellDataFile non e' disponibile o il file ha un errore:
        # si ripiega su un parser minimale, cosi' la verifica non si blocca.
        $raw = Get-Content -LiteralPath $Config -Raw
        $map = @{}
        foreach ($m in [regex]::Matches($raw, "(?m)^\s*(\w+)\s*=\s*(.+?)\s*$")) {
            $key = $m.Groups[1].Value
            $val = $m.Groups[2].Value.Trim().Trim("'").Trim('"')
            if ($val -match '^\[.*\]$') {
                $items = @()
                $pat = "'([^']*)'|""([^""]*)"""
                foreach ($i in [regex]::Matches($val, $pat)) {
                    $items += $(if ($i.Groups[1].Success) { $i.Groups[1].Value } else { $i.Groups[2].Value })
                }
                $map[$key] = $items
            } elseif ($val -match '^\d+$') {
                $map[$key] = [int]$val
            } else {
                $map[$key] = $val
            }
        }
        $cfg = $map
    }
}
if (-not $cfg) { $cfg = @{} }

function Get-Cfg {
    param($Key, $Default)
    if ($cfg -and $cfg.ContainsKey($Key) -and $null -ne $cfg[$Key]) { return $cfg[$Key] }
    return $Default
}

$monolithRel = Get-Cfg "Monolith" ""
$runnerRel = Get-Cfg "Runner" ""
$indexRel = Get-Cfg "IndexOutput" ""
$buildRel = Get-Cfg "Build" ""
$expectedCfg = [int](Get-Cfg "ExpectedTotal" 0)
$sourceRels = @(Get-Cfg "Sources" @())
$diffRels = @(Get-Cfg "DiffPaths" @())
$runnerArgs = @(Get-Cfg "RunnerArgs" @())

# Il parametro -Build sovrascrive la config; se non e' dato, si usa la config.
if (-not $Build -and $buildRel) { $Build = $buildRel }

$monolith = if ($monolithRel) { Join-Path $root $monolithRel } else { "" }
$runner = if ($runnerRel) { Join-Path $root $runnerRel } else { "" }
$indexFile = if ($indexRel) { Join-Path $root $indexRel } else { "" }
$metricsFile = Join-Path $root ".opencode\metrics.jsonl"
$verdictFile = Join-Path $root ".opencode\verdict.txt"

# 'python' nel PATH e' la stub del Microsoft Store: serve il Python di Blender.
$py = "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe"
if (-not (Test-Path $py)) { throw "Python di Blender non trovato: $py" }

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Nonce di run: lega il verdetto alla telemetria che lo ha prodotto. Un
# verdetto scritto a mano (fuori da questo script) non puo' conoscere il
# nonce, quindi l'audit lo rifiuta.
$runId = "{0}-{1}" -f (Get-Date).ToString("yyyyMMddHHmmss"), ([guid]::NewGuid().ToString("N").Substring(0, 8))

function Write-Verdict {
    param([string]$Line, [int]$ExitCode)
    $dir = Split-Path -Parent $verdictFile
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [IO.File]::WriteAllText($verdictFile, $Line + [Environment]::NewLine, $utf8NoBom)
    Write-Output $Line
    exit $ExitCode
}

function Write-Metric {
    param($Status, $Passed, $Failed, $DiffLines, $Reason)
    $sw.Stop()
    $entry = [ordered]@{
        ts         = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
        run_id     = $runId
        task       = $TaskTag
        agent      = $Agent
        suites     = $(if ($Suites) { $Suites } else { "ALL" })
        status     = $Status
        passed     = $Passed
        failed     = $Failed
        diff_lines = $DiffLines
        duration_s = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        reason     = $Reason
    } | ConvertTo-Json -Compress
    $dir = Split-Path -Parent $metricsFile
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    # Append senza BOM: un BOM in mezzo al jsonl romperebbe il parsing.
    [IO.File]::AppendAllText($metricsFile, $entry + [Environment]::NewLine, $utf8NoBom)
}

# Invoca git senza far esplodere lo script: git scrive warning su stderr
# (autocrlf, LF/CRLF, safe.directory...) e con ErrorActionPreference=Stop
# PowerShell 5.1 li trasformerebbe in errori fatali. Il rumore non conta:
# conta solo il codice di uscita e lo stdout.
function Invoke-Git {
    param([string[]]$GitArgs)
    $prevEA = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $out = & git -C $root @GitArgs 2>&1
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEA
    }
    return [pscustomobject]@{ Output = @($out); Exit = $code }
}

# Se il progetto non e' un repository git, il controllo del diff viene
# saltato: non e' un errore, e' un progetto non ancora versionato.
function Test-GitRepo {
    $r = Invoke-Git @("rev-parse", "--is-inside-work-tree")
    return ($r.Exit -eq 0 -and (($r.Output | Out-String).Trim() -eq "true"))
}

# Artefatti generati dalla build, ESCLUSI dal conteggio MaxDiffLines:
#   - actd_build\auto_copy_transforms_def.py (monolite, output di build_monolith)
#   - actd_build\INDEX.md (indice AST, rigenerato dal passo 4 di questo script)
# Il monolite duplica ~1:1 il diff dei moduli in actd_build\actd_mods: la sua
# differenza segue i moduli 1:1 (es. fase multi-modulo: 363 righe sui moduli
# diventavano 713 contando anche il monolite generato). Contarlo raddoppia
# artificialmente ogni fase multi-modulo. Restano esclusi SOLO questi artefatti:
# il guard anti-refactoring a tappeto resta attivo su tutti i file scritti a
# mano (moduli, test, runner, config).
$generatedArtifacts = @(
    'actd_build/auto_copy_transforms_def.py',
    'actd_build/INDEX.md'
)

# True se il path (relativo alla root, separatori '/' o '\') e' un artefatto
# generato dalla build e quindi non deve pesare sul MaxDiffLines.
function Test-GeneratedArtifact {
    param([string]$RelPath)
    $n = (($RelPath -replace '\\', '/') -replace '^\./', '')
    foreach ($g in $generatedArtifacts) { if ($n -eq $g) { return $true } }
    return $false
}

# Ampiezza del diff sui path indicati (moduli sorgente, ecc.), con gli artefatti
# generati dalla build esclusi (vedi $generatedArtifacts).
function Get-DiffLines {
    $total = 0
    $paths = @()
    if ($diffRels.Count -gt 0) { $paths = $diffRels } elseif ($monolithRel) { $paths = @($monolithRel) }
    if ($paths.Count -eq 0) { return 0 }
    if (-not (Test-GitRepo)) { return 0 }
    $r = Invoke-Git (@("diff", "--numstat", "--") + $paths)
    foreach ($line in $r.Output) {
        $t = "$line"
        if ($t -notmatch '^\d+\s+\d+\s') { continue }
        $parts = $t -split "`t"
        if ($parts.Count -ge 2) {
            # Artefatto generato dalla build: il suo diff segue 1:1 quello dei
            # moduli e non e' lavoro manuale, quindi non conta ai fini della
            # soglia MaxDiffLines (guard resta attivo sui file scritti a mano).
            if ($parts.Count -ge 3 -and (Test-GeneratedArtifact $parts[2])) { continue }
            $a = 0; $d = 0
            if ([int]::TryParse($parts[0], [ref]$a)) { $total += $a }
            if ([int]::TryParse($parts[1], [ref]$d)) { $total += $d }
        }
    }
    # File nuovi non tracciati: ogni riga e' una riga aggiunta.
    # Anche qui gli artefatti generati dalla build sono esclusi (idem sopra).
    $u = Invoke-Git (@("ls-files", "--others", "--exclude-standard", "--") + $paths)
    foreach ($file in $u.Output) {
        $t = "$file".Trim()
        if (-not $t) { continue }
        if (Test-GeneratedArtifact $t) { continue }
        $full = Join-Path $root $t
        if (Test-Path -LiteralPath $full) { $total += @(Get-Content -LiteralPath $full).Count }
    }
    return $total
}

# Rollback NON distruttivo: le modifiche restano nello stash (recuperabili
# con `git stash pop`), la working tree torna a HEAD.
function Invoke-Rollback {
    if (-not (Test-GitRepo)) { return }
    if ($diffRels.Count -gt 0) {
        [void](Invoke-Git (@("stash", "push", "--quiet", "--") + $diffRels))
    } elseif ($monolithRel) {
        [void](Invoke-Git @("stash", "push", "--quiet", "--", $monolithRel))
    }
}

Push-Location $root
try {
    # --- 1. ampiezza diff -----------------------------------------------------
    $diffLines = Get-DiffLines
    if ($MaxDiffLines -gt 0 -and $diffLines -gt $MaxDiffLines) {
        if ($AutoRollback) { Invoke-Rollback }
        Write-Metric "FAIL" 0 0 $diffLines "DIFF_TOO_LARGE"
        Write-Verdict "VERIFY_FAIL | reason=DIFF_TOO_LARGE | diff=$diffLines | max=$MaxDiffLines | rollback=$($AutoRollback.IsPresent) | task=$TaskTag | run=$runId" 2
    }

    # --- 2. build step: il monolite e' un artefato, i moduli sono la fonte ---
    # I test importano il MONOLITE. Se il Coder ha modificato un modulo e il
    # monolite non viene ricostruito, i test girano su codice VECCHIO e il
    # gate darebbe un verde falso. Il build quindi viene SEMPRE prima dei test.
    #
    # Semantica del build step (build_monolith.py):
    #   exit 0 -> il monolite era gia' allineato ai moduli (IN_SYNC)
    #   exit 1 -> il monolite era DISALLINEATO ed e' stato rigenerato
    #             (REBUILT): e' il caso normale dopo una modifica del Coder
    #   altro  -> guasto reale (FAILED)
    $buildState = "SKIPPED"
    if ($Build) {
        $buildPath = Join-Path $root $Build
        if (Test-Path -LiteralPath $buildPath) {
            $buildOut = & $py $buildPath build 2>&1
            $buildExit = $LASTEXITCODE
            $buildText = ($buildOut | Out-String)
            if ($buildExit -eq 0) {
                $buildState = "IN_SYNC"
            } elseif ($buildExit -eq 1 -and $buildText -match 'Moduli assemblati') {
                $buildState = "REBUILT"
            } else {
                $buildState = "FAILED"
            }
        } else {
            $buildState = "MISSING"
        }
        if ($buildState -eq "FAILED" -or $buildState -eq "MISSING") {
            $detail = ($buildOut | Select-Object -First 3) -join " | "
            Write-Metric "FAIL" 0 0 $diffLines "BUILD_FAILED"
            Write-Verdict "VERIFY_FAIL | reason=BUILD_FAILED | build=$Build | state=$buildState | detail=$detail | task=$TaskTag | run=$runId" 1
        }
    }

    # --- 3. py_compile deterministico ----------------------------------------
    $targets = @()
    if ($monolith -and (Test-Path $monolith)) { $targets += $monolith }
    foreach ($rel in $sourceRels) {
        $full = Join-Path $root $rel
        if (Test-Path $full -PathType Leaf) { $targets += $full }
        elseif (Test-Path $full -PathType Container) {
            $targets += (Get-ChildItem $full -Filter "*.py" -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
        }
    }
    if ($targets.Count -gt 0) {
        $compileOut = & $py -m py_compile @targets 2>&1
        if ($LASTEXITCODE -ne 0) {
            if ($AutoRollback) { Invoke-Rollback }
            Write-Metric "FAIL" 0 0 $diffLines "PY_COMPILE_ERROR"
            $first = ($compileOut | Select-Object -First 3) -join " | "
            Write-Verdict "VERIFY_FAIL | reason=PY_COMPILE_ERROR | rollback=$($AutoRollback.IsPresent) | detail=$first | task=$TaskTag | run=$runId" 1
        }
    }

    # --- 4. indice AST (0 token, sempre sincronizzato) -----------------------
    $indexState = "SKIPPED"
    if (-not $SkipIndex -and $indexFile -and $monolith -and (Test-Path $monolith)) {
        $indexOut = & $py (Join-Path $PSScriptRoot "ast_index.py") $monolith --out $indexFile 2>&1
        if ($LASTEXITCODE -eq 0) { $indexState = "UPDATED" } else { $indexState = "FAILED" }
    }

    # --- 5. test ---------------------------------------------------------------
    # I conteggi si rileggono dal RIEPILOGO del runner. Se ne ammette due
    # forme, si preferisce quella piu' recente:
    #   a) tabella  "suite.py  attesi  passati  falliti  esito"
    #   b) riga     "RISULTATO passati=N falliti=M"
    $passed = 0
    $failed = 0
    $runnerExit = 0
    $expectedTotal = 0
    $summaryFound = $false
    if (-not $SkipTests) {
        if (-not $runner -or -not (Test-Path $runner)) {
            Write-Metric "FAIL" 0 0 $diffLines "NO_RUNNER"
            Write-Verdict "VERIFY_FAIL | reason=NO_RUNNER | runner=$runnerRel | task=$TaskTag | run=$runId" 1
        }
        $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $runner) + $runnerArgs
        if ($Suites) { $args += @("-Suites", $Suites) }
        $prevEA = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $table = & powershell @args 2>&1
            $runnerExit = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $prevEA
        }
        $sumExpected = 0
        foreach ($line in $table) {
            if ("$line" -match '^\s*(\S+\.py)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s*$') {
                $sumExpected += [int]$Matches[2]
                $passed += [int]$Matches[3]
                $failed += [int]$Matches[4]
                $summaryFound = $true
            }
        }
        if ($summaryFound) {
            $expectedTotal = $sumExpected
        } else {
            foreach ($line in $table) {
                if ("$line" -match 'RISULTATO\s+passati=(\d+)\s+falliti=(\d+)') {
                    $passed = [int]$Matches[1]
                    $failed = [int]$Matches[2]
                    $summaryFound = $true
                }
            }
        }
        if (-not $summaryFound) {
            if ($AutoRollback) { Invoke-Rollback }
            Write-Metric "FAIL" 0 0 $diffLines "NO_SUMMARY"
            Write-Verdict "VERIFY_FAIL | reason=NO_SUMMARY | runner=$runnerRel | exit=$runnerExit | task=$TaskTag | run=$runId" 1
        }
        if ($expectedCfg -gt 0 -and -not $Suites) { $expectedTotal = $expectedCfg }
    }

    if ($runnerExit -ne 0 -or $failed -gt 0) {
        if ($AutoRollback) { Invoke-Rollback }
        Write-Metric "FAIL" $passed $failed $diffLines "TESTS_FAILED"
        Write-Verdict "VERIFY_FAIL | reason=TESTS_FAILED | passed=$passed | failed=$failed | expected=$expectedTotal | diff=$diffLines | runner_exit=$runnerExit | rollback=$($AutoRollback.IsPresent) | task=$TaskTag | run=$runId" 1
    }

    # Se il totale atteso e' noto, un conteggio diverso significa che qualcosa
    # non e' stato eseguito: si fallisce invece di dichiarare un verde parziale.
    if ($expectedTotal -gt 0 -and $passed -ne $expectedTotal) {
        Write-Metric "FAIL" $passed $failed $diffLines "INCOMPLETE"
        Write-Verdict "VERIFY_FAIL | reason=INCOMPLETE | passed=$passed | expected=$expectedTotal | failed=$failed | diff=$diffLines | task=$TaskTag | run=$runId" 1
    }

    Write-Metric "OK" $passed 0 $diffLines "OK"
    Write-Verdict "VERIFY_OK | passed=$passed | failed=0 | diff=$diffLines | index=$indexState | build=$buildState | task=$TaskTag | run=$runId" 0
}
finally {
    Pop-Location
}
