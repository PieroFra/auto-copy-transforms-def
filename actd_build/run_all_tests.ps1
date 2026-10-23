param(
    [string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe',
    [string]$Suites,
    [int]$MaxParallel = 8
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$log = Join-Path $PSScriptRoot 'test_out.txt'
$allSuites = @(
    @{ Name = 'test_mod1.py'; Expected = 40 },
    @{ Name = 'test_mod2.py'; Expected = 18 },
    @{ Name = 'test_mod3.py'; Expected = 24 },
    @{ Name = 'test_mod4.py'; Expected = 43 },
    @{ Name = 'test_func1.py'; Expected = 5 },
    @{ Name = 'test_actd.py'; Expected = 106 },
    @{ Name = 'test_mod_types.py'; Expected = 49 },
    @{ Name = 'test_mod_autoprefix.py'; Expected = 35 },
    @{ Name = 'test_mod_learn.py'; Expected = 40 },
    @{ Name = 'test_mod6.py'; Expected = 169 },
    @{ Name = 'test_i18n.py'; Expected = 65 }
)
# Totale atteso delle 11 suite: 594 controlli.
$expectedTotalAll = 0
foreach ($suite in $allSuites) { $expectedTotalAll += $suite.Expected }
if ($expectedTotalAll -ne 594) {
    throw "Totale atteso del full-run non valido: $expectedTotalAll (attesi 594)"
}
$validateAll = -not $PSBoundParameters.ContainsKey('Suites') -or [string]::IsNullOrWhiteSpace($Suites)
$selectedSuites = @()
$suiteAliases = @{}
foreach ($suite in $allSuites) {
    $suiteAliases[$suite.Name] = $suite.Name
    if ($suite.Name -match '^test_(.+)\.py$') { $suiteAliases[$Matches[1]] = $suite.Name }
}
$suiteAliases['types'] = 'test_mod_types.py'
$suiteAliases['autoprefix'] = 'test_mod_autoprefix.py'
$suiteAliases['learn'] = 'test_mod_learn.py'
if ($validateAll) {
    $selectedSuites = $allSuites
} else {
    foreach ($name in ($Suites -split ',')) {
        $name = $name.Trim()
        if (-not $name -or -not $suiteAliases.ContainsKey($name)) {
            throw "Suite sconosciuta o vuota: '$name'"
        }
        $suiteName = $suiteAliases[$name]
        if (-not ($selectedSuites | Where-Object { $_.Name -eq $suiteName })) {
            $selectedSuites += $allSuites | Where-Object { $_.Name -eq $suiteName }
        }
    }
}

if (-not (Test-Path -LiteralPath $Blender -PathType Leaf)) {
    throw "Eseguibile Blender non trovato: $Blender"
}
if ($MaxParallel -lt 1) { $MaxParallel = 1 }

Push-Location $root
try {
    # Preparazione slot: ogni suite ha i propri file temporanei isolati, così
    # fino a $MaxParallel istanze di Blender possono girare insieme senza
    # contendersi test_out.txt.
    $workItems = @()
    for ($idx = 0; $idx -lt $selectedSuites.Count; $idx++) {
        $s = $selectedSuites[$idx]
        $suitePath = Join-Path $PSScriptRoot $s.Name
        $uid = [guid]::NewGuid().ToString('N')
        $workItems += [pscustomobject]@{
            Index      = $idx
            Suite      = $s.Name
            Expected   = $s.Expected
            SuitePath  = $suitePath
            Exists     = (Test-Path -LiteralPath $suitePath -PathType Leaf)
            StdoutPath = Join-Path ([IO.Path]::GetTempPath()) ("actd_{0}_{1}.stdout" -f $s.Name, $uid)
            StderrPath = Join-Path ([IO.Path]::GetTempPath()) ("actd_{0}_{1}.stderr" -f $s.Name, $uid)
            Process    = $null
            ExitCode   = -1
            Output     = ''
        }
    }

    # Pool di processi paralleli (fino a $MaxParallel contemporanei).
    $queue = New-Object System.Collections.Queue
    foreach ($item in $workItems) {
        if ($item.Exists) { $queue.Enqueue($item) }
    }
    $running = New-Object System.Collections.ArrayList

    while ($queue.Count -gt 0 -or $running.Count -gt 0) {
        while ($queue.Count -gt 0 -and $running.Count -lt $MaxParallel) {
            $item = $queue.Dequeue()
            $pythonArgument = '"{0}"' -f $item.SuitePath
            $item.Process = Start-Process -FilePath $Blender -ArgumentList @(
                '--background', '--factory-startup', '--python', $pythonArgument
            ) -PassThru -WindowStyle Hidden -RedirectStandardOutput $item.StdoutPath -RedirectStandardError $item.StderrPath
            [void]$running.Add($item)
        }
        Start-Sleep -Milliseconds 80
        for ($i = $running.Count - 1; $i -ge 0; $i--) {
            $cur = $running[$i]
            if ($cur.Process.HasExited) {
                $cur.Process.WaitForExit()
                $cur.ExitCode = $cur.Process.ExitCode
                $stdout = ''
                $stderr = ''
                for ($retry = 0; $retry -lt 10; $retry++) {
                    try {
                        if (Test-Path -LiteralPath $cur.StdoutPath) { $stdout = [IO.File]::ReadAllText($cur.StdoutPath) }
                        if (Test-Path -LiteralPath $cur.StderrPath) { $stderr = [IO.File]::ReadAllText($cur.StderrPath) }
                        break
                    } catch {
                        Start-Sleep -Milliseconds 50
                    }
                }
                $cur.Output = $stdout + [Environment]::NewLine + $stderr
                Remove-Item -LiteralPath $cur.StdoutPath, $cur.StderrPath -Force -ErrorAction SilentlyContinue
                $running.RemoveAt($i)
            }
        }
    }

    # Valutazione in ordine canonico e scrittura di test_out.txt (log completo
    # concatenato, con eventuali suite fallite messe in coda per ispezione rapida).
    $results = @()
    $stopAfterSuite = $false
    $combinedLog = New-Object System.Text.StringBuilder
    $failedLogs = New-Object System.Text.StringBuilder

    foreach ($item in ($workItems | Sort-Object Index)) {
        if (-not $item.Exists) {
            $results += [pscustomobject]@{
                Suite = $item.Suite; Attesi = $item.Expected
                Passati = 'n/d'; Falliti = 'n/d'; Esito = 'FILE ASSENTE'
            }
            continue
        }
        $output = $item.Output
        [void]$combinedLog.AppendLine("===== SUITE: $($item.Suite) =====")
        [void]$combinedLog.AppendLine($output)

        if ([string]::IsNullOrWhiteSpace($output)) {
            $results += [pscustomobject]@{
                Suite = $item.Suite; Attesi = $item.Expected
                Passati = 'n/d'; Falliti = 'n/d'; Esito = 'LOG VUOTO'
            }
            [void]$failedLogs.AppendLine("===== FAIL SUITE: $($item.Suite) (LOG VUOTO) =====")
            continue
        }

        if ($output -match '(?m)\b(SyntaxError|ImportError)\b') {
            $results += [pscustomobject]@{
                Suite = $item.Suite; Attesi = $item.Expected
                Passati = 'n/d'; Falliti = 'n/d'; Esito = "ERRORE $($Matches[1])"
            }
            $stopAfterSuite = $true
            [void]$failedLogs.AppendLine("===== FAIL SUITE: $($item.Suite) =====")
            [void]$failedLogs.AppendLine($output)
            continue
        }

        $passed = $null
        $failed = $null
        $validSummary = $false
        $modularPassed = [regex]::Matches($output, '(?mi)^Passati:\s*(\d+)\s*$')
        $modularFailed = [regex]::Matches($output, '(?mi)^Falliti:\s*(\d+)\s*$')
        $legacySummary = [regex]::Matches($output, '(?mi)^Superati:\s*(\d+)\s*/\s*(\d+)\s*$')

        if ($modularPassed.Count -gt 0 -and $modularFailed.Count -gt 0) {
            $passed = [int]$modularPassed[$modularPassed.Count - 1].Groups[1].Value
            $failed = [int]$modularFailed[$modularFailed.Count - 1].Groups[1].Value
            $validSummary = $output -match '(?m)^RISULTATO:\s*SUPERATO\s*\r?$'
        } elseif ($legacySummary.Count -gt 0) {
            $summary = $legacySummary[$legacySummary.Count - 1]
            $passed = [int]$summary.Groups[1].Value
            $total = [int]$summary.Groups[2].Value
            $failed = $total - $passed
            $validSummary = $output -match '(?m)^TUTTI I TEST SUPERATI\s*\r?$'
        }

        $expectedTotal = if ($null -ne $passed -and $null -ne $failed) { $passed + $failed } else { -1 }
        $exitOk = ($item.ExitCode -eq 0) -or ($null -eq $item.ExitCode)
        $success = $exitOk -and $validSummary -and
            $passed -eq $item.Expected -and $failed -eq 0 -and
            $expectedTotal -eq $item.Expected
        if (-not $success) {
            [void]$failedLogs.AppendLine("===== FAIL SUITE: $($item.Suite) =====")
            [void]$failedLogs.AppendLine($output)
        }
        $results += [pscustomobject]@{
            Suite = $item.Suite; Attesi = $item.Expected
            Passati = $(if ($null -eq $passed) { 'n/d' } else { $passed })
            Falliti = $(if ($null -eq $failed) { 'n/d' } else { $failed })
            Esito = $(if ($success) { 'SUPERATO' } else { 'DIVERGENZA' })
        }
    }

    $finalLog = if ($failedLogs.Length -gt 0) {
        $combinedLog.ToString() + [Environment]::NewLine + $failedLogs.ToString()
    } else {
        $combinedLog.ToString()
    }
    [IO.File]::WriteAllText($log, $finalLog, (New-Object System.Text.UTF8Encoding($false)))
} finally {
    Pop-Location
}

$results | Format-Table -AutoSize | Out-Host
$totalPassed = 0
foreach ($result in $results) {
    if ($result.Passati -match '^\d+$') { $totalPassed += [int]$result.Passati }
}
$allTotalValid = -not $validateAll -or ($results.Count -eq $allSuites.Count -and $totalPassed -eq $expectedTotalAll)
if ($stopAfterSuite -or $results.Count -ne $selectedSuites.Count -or -not $allTotalValid -or
    @($results | Where-Object { $_.Esito -ne 'SUPERATO' }).Count -gt 0) {
    exit 1
}
exit 0
