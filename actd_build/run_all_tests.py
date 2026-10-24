#!/usr/bin/env python3
"""Runner portatile delle suite di regressione ACTD.

Equivalente multi-piattaforma (Linux/macOS/Windows) di
actd_build\\run_all_tests.ps1, scritto con la sola libreria standard di Python
(nessuna dipendenza esterna). Esegue le suite headless tramite
``blender --background --factory-startup --python`` (fino a 8 istanze in
parallelo, come il wrapper Windows), scrive la diagnostica concatenata in
``actd_build/test_out.txt``, stampa la tabella dei risultati e restituisce
exit code 0 (tutto SUPERATO) oppure 1 (fallimenti o divergenze).

Opzioni:
  -Blender <percorso>  eseguibile Blender. Default: variabile d'ambiente
                       BLENDER_EXE, altrimenti ``blender`` cercato nel PATH.
  -Suites <elenco>     suite separate da virgola (default: tutte). Si possono
                       usare i nomi di file, i nomi di modulo (test_x.py -> x)
                       o gli alias brevi (types, autoprefix, learn).
"""

import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys

# Cartella di questo script (actd_build) e radice del progetto (cartella padre).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
LOG_PATH = os.path.join(SCRIPT_DIR, 'test_out.txt')

# Elenco canonico delle suite con i controlli attesi per ciascuna:
# deve essere tenuto in sincronia con run_all_tests.ps1.
ALL_SUITES = [
    ('test_mod1.py', 40),
    ('test_mod2.py', 18),
    ('test_mod3.py', 24),
    ('test_mod4.py', 43),
    ('test_func1.py', 5),
    ('test_actd.py', 106),
    ('test_mod_types.py', 49),
    ('test_mod_autoprefix.py', 35),
    ('test_mod_learn.py', 40),
    ('test_mod6.py', 169),
    ('test_i18n.py', 65),
    ('test_mod7.py', 50),
]

# Totale atteso del full-run: il runner rifiuta di partire se la somma dei
# conteggi attesi non torna (autocontrollo, come nel wrapper PowerShell).
EXPECTED_TOTAL_ALL = 644

# Parallelo massimo, in parita' con il default -MaxParallel 8 del runner Windows.
MAX_PARALLEL = 8


def build_suite_aliases():
    """Costruisce la mappa degli alias accettati da -Suites."""
    aliases = {}
    for name, _expected in ALL_SUITES:
        # Nome di file completo.
        aliases[name] = name
        # Nome di modulo (test_mod1.py -> mod1).
        match = re.match(r'^test_(.+)\.py$', name)
        if match:
            aliases[match.group(1)] = name
    # Alias brevi espliciti, come nel runner PowerShell.
    aliases['types'] = 'test_mod_types.py'
    aliases['autoprefix'] = 'test_mod_autoprefix.py'
    aliases['learn'] = 'test_mod_learn.py'
    return aliases


def resolve_blender(path):
    """Restituisce il percorso dell'eseguibile Blender, o None se irraggiungibile."""
    if os.path.isfile(path):
        return path
    # Fallback: ricerca nel PATH (utile su Linux/macOS con 'blender' nudo).
    return shutil.which(path)


def run_suite(blender, suite_name):
    """Lancia una suite con Blender in background e cattura stdout/stderr."""
    suite_path = os.path.join(SCRIPT_DIR, suite_name)
    command = [blender, '--background', '--factory-startup', '--python', suite_path]
    try:
        proc = subprocess.run(
            command, cwd=PROJECT_ROOT, capture_output=True, text=True,
            encoding='utf-8', errors='replace')
        output = proc.stdout + '\n' + proc.stderr
        return suite_name, output, proc.returncode
    except OSError as exc:
        # Eseguibile non avviabile: la diagnostica finisce nel log e la
        # suite risulta non valida (DIVERGENZA) in fase di valutazione.
        return suite_name, str(exc), 1


def parse_args():
    """Interfaccia a riga di comando (equivalenti di -Blender e -Suites)."""
    parser = argparse.ArgumentParser(
        description='Runner portatile delle suite di regressione ACTD '
                    '(equivalente di actd_build/run_all_tests.ps1).')
    parser.add_argument(
        '-Blender', default=os.environ.get('BLENDER_EXE') or 'blender',
        help='Percorso dell\'eseguibile Blender (default: variabile d\'ambiente '
             'BLENDER_EXE, altrimenti "blender" cercato nel PATH).')
    parser.add_argument(
        '-Suites', default=None,
        help='Suite separate da virgola (default: tutte). Ammesse nomi di file, '
             'nomi di modulo o alias (types, autoprefix, learn).')
    return parser.parse_args()


def select_suites(suites_option):
    """Risolve -Suites nell'elenco canonico, applicando alias e de-duplica."""
    aliases = build_suite_aliases()
    if suites_option is None or not suites_option.strip():
        return list(ALL_SUITES), True
    selected = []
    selected_names = set()
    for raw in suites_option.split(','):
        name = raw.strip()
        if not name or name not in aliases:
            print("Suite sconosciuta o vuota: '{0}'".format(name), file=sys.stderr)
            return None, False
        suite_name = aliases[name]
        if suite_name not in selected_names:
            selected_names.add(suite_name)
            selected.append(
                next(suite for suite in ALL_SUITES if suite[0] == suite_name))
    return selected, False


def main():
    args = parse_args()

    # Autocontrollo: il totale dei controlli attesi deve essere 644.
    expected_total_all = sum(expected for _name, expected in ALL_SUITES)
    if expected_total_all != EXPECTED_TOTAL_ALL:
        print('Totale atteso del full-run non valido: {0} (attesi {1})'.format(
            expected_total_all, EXPECTED_TOTAL_ALL), file=sys.stderr)
        return 1

    # Risoluzione delle suite richieste.
    selected, validate_all = select_suites(args.Suites)
    if selected is None:
        return 1

    # Precondizione dura: l'eseguibile Blender deve essere raggiungibile.
    blender = resolve_blender(args.Blender)
    if blender is None:
        print('Eseguibile Blender non trovato: {0}'.format(args.Blender),
              file=sys.stderr)
        return 1

    # Preparazione dei work item: le suite con file assente non vengono lanciate
    # (saranno marcate FILE ASSENTE in fase di valutazione).
    work_items = []
    for suite_name, expected in selected:
        suite_path = os.path.join(SCRIPT_DIR, suite_name)
        work_items.append((suite_name, expected, os.path.isfile(suite_path)))

    # Pool di processi paralleli (fino a MAX_PARALLEL istanze di Blender).
    runnable = [(name, _exp) for name, _exp, exists in work_items if exists]
    outputs = {}
    exit_codes = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = {pool.submit(run_suite, blender, name): name
                   for name, _exp in runnable}
        for future in concurrent.futures.as_completed(futures):
            suite_name, output, exit_code = future.result()
            outputs[suite_name] = output
            exit_codes[suite_name] = exit_code

    # Valutazione in ordine canonico e composizione di test_out.txt (log
    # completo concatenato, con le suite fallite messe in coda per ispezione).
    results = []
    stop_after_suite = False
    combined_log = []
    failed_logs = []
    for suite_name, expected, exists in work_items:
        if not exists:
            results.append((suite_name, expected, 'n/d', 'n/d', 'FILE ASSENTE'))
            continue
        output = outputs.get(suite_name, '')
        combined_log.append('===== SUITE: {0} ====='.format(suite_name))
        combined_log.append(output)

        if not output.strip():
            results.append((suite_name, expected, 'n/d', 'n/d', 'LOG VUOTO'))
            failed_logs.append(
                '===== FAIL SUITE: {0} (LOG VUOTO) ====='.format(suite_name))
            continue

        # Errore grave di caricamento: contrassegna il verdetto complessivo.
        syntax_match = re.search(r'(?m)\b(SyntaxError|ImportError)\b', output)
        if syntax_match:
            results.append(
                (suite_name, expected, 'n/d', 'n/d',
                 'ERRORE ' + syntax_match.group(1)))
            stop_after_suite = True
            failed_logs.append('===== FAIL SUITE: {0} ====='.format(suite_name))
            failed_logs.append(output)
            continue

        passed = None
        failed = None
        valid_summary = False
        # Sintassi modulare attesa: "Passati: N" / "Falliti: N" e
        # "RISULTATO: SUPERATO".
        modular_passed = re.findall(r'(?mi)^Passati:\s*(\d+)\s*$', output)
        modular_failed = re.findall(r'(?mi)^Falliti:\s*(\d+)\s*$', output)
        if modular_passed and modular_failed:
            passed = int(modular_passed[-1])
            failed = int(modular_failed[-1])
            valid_summary = bool(
                re.search(r'(?m)^RISULTATO:\s*SUPERATO\s*\r?$', output))
        else:
            # Sintassi legacy: "Superati: N / M" e "TUTTI I TEST SUPERATI".
            legacy = re.findall(
                r'(?mi)^Superati:\s*(\d+)\s*/\s*(\d+)\s*$', output)
            if legacy:
                passed = int(legacy[-1][0])
                total = int(legacy[-1][1])
                failed = total - passed
                valid_summary = bool(
                    re.search(r'(?m)^TUTTI I TEST SUPERATI\s*\r?$', output))

        expected_total = (passed + failed) if (
            passed is not None and failed is not None) else -1
        exit_ok = exit_codes.get(suite_name) in (None, 0)
        success = (exit_ok and valid_summary and passed == expected
                   and failed == 0 and expected_total == expected)
        if not success:
            failed_logs.append('===== FAIL SUITE: {0} ====='.format(suite_name))
            failed_logs.append(output)
        results.append((suite_name, expected,
                        passed if passed is not None else 'n/d',
                        failed if failed is not None else 'n/d',
                        'SUPERATO' if success else 'DIVERGENZA'))

    # Scrittura del log completo (UTF-8 senza BOM), fallite in coda se presenti.
    final_log = '\n'.join(combined_log)
    if failed_logs:
        final_log += '\n' + '\n'.join(failed_logs)
    with open(LOG_PATH, 'w', encoding='utf-8', newline='') as handle:
        handle.write(final_log)

    # Tabella dei risultati (equivalente di Format-Table -AutoSize | Out-Host).
    headers = ['Suite', 'Attesi', 'Passati', 'Falliti', 'Esito']
    rows = [headers] + [[str(cell) for cell in row] for row in results]
    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    for row in rows:
        print('  '.join(cell.ljust(widths[i])
                        for i, cell in enumerate(row)))

    # Verdetto complessivo: conteggio totale valido solo sul full-run.
    total_passed = sum(int(row[2]) for row in results if str(row[2]).isdigit())
    all_total_valid = (not validate_all) or (
        len(results) == len(ALL_SUITES) and total_passed == expected_total_all)
    if (stop_after_suite or len(results) != len(selected) or not all_total_valid
            or any(row[4] != 'SUPERATO' for row in results)):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
