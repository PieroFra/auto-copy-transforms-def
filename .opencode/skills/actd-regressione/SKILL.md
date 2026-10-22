---
name: ACTD Regressione
description: Come eseguire e leggere le suite di test del progetto A.C.T.D. (runner canonico, conteggi attesi, interpretazione del log, diagnostica dei fallimenti). Usare quando si eseguono test, quando una suite fallisce, o quando si aggiungono test.
---

# ACTD — Regressione

Skill di procedura per il **Tester** (e per chiunque debba eseguire o valutare i test del progetto
A.C.T.D.). Non contiene i contratti di output degli agenti: quelli stanno nei prompt.

## Il runner canonico

Tutti i test passano **solo** dal runner: esegue ogni suite in Blender headless, verifica il conteggio
atteso e scrive il log.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File actd_build\run_all_tests.ps1 -Suites test_mod1.py,test_mod_types.py
```

- `-Suites` = suite mirate, separate da virgola, **con l'estensione `.py`**.
- `-Suites` omesso = **giro completo** (tutte le 11 suite).
- `-Blender <path>` = eseguibile alternativo (default `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`).
- Il log finisce in `actd_build\test_out.txt` (nella stessa cartella del runner).
- Durata misurata: suite mirata ~10-15 s, giro completo **~35 s**.

Non lanciare Blender a mano, non scrivere script ad hoc: il runner verifica anche i conteggi attesi
e fallisce da solo se il totale non torna.

## Le 11 suite e i conteggi attesi

| Suite | Attesi | Cosa copre |
|---|---:|---|
| `test_mod1.py` | 40 | armatura sorgente |
| `test_mod2.py` | 18 | mix mode e stack position |
| `test_mod3.py` | 24 | filtro bone collection |
| `test_mod4.py` | 43 | diagnostica |
| `test_func1.py` | 5 | controllo funzionale di copia |
| `test_actd.py` | 106 | suite storica end-to-end |
| `test_mod_types.py` | 49 | tipi di constraint e `use_offset` |
| `test_mod_autoprefix.py` | 35 | rilevamento automatico dei token |
| `test_mod_learn.py` | 40 | apprendimento del pattern da un constraint |
| `test_mod6.py` | 113 | manutenzione ed export |
| `test_i18n.py` | 65 | UI italiana/inglese |
| **Totale** | **538** | |

Questi numeri vivono anche in `actd_build\run_all_tests.ps1` (campo `Expected` per suite e il controllo
del totale a 538): **se aggiungi test, aggiorna entrambi**, altrimenti il runner fallisce.

## Leggere il log

Il runner stampa una tabella per suite e lascia in `test_out.txt` l'output delle singole suite:

```
Suite                  Attesi Passati Falliti Esito
test_mod1.py               40      40       0 SUPERATO
```

- `SUPERATO` = esito normale delle suite.
- `TUTTI I TEST SUPERATI` = come riporta la suite storica `test_actd.py` (stesso significato).
- Il totale del giro completo deve essere **538/538, 0 fallimenti**.

## Diagnostica

- **Fast-fail**: su `SyntaxError` o `ImportError` il Tester si ferma e riporta solo
  `ErrorType + File:Linea` dell'ultima riga.
- **Un test che fallisce**: il fallimento è quasi sempre nel log della singola suite in `test_out.txt`
  (asserzione + traceback). Riporta `File:Linea` e **non** proporre la correzione: spetta al Coder.
- **Il runner non parte**: controlla che `test_out.txt` non sia bloccato da un'altra istanza e che
  Blender non sia già aperto con lo stesso profilo.
- **Il totale non torna**: quasi sempre è un `Expected` non aggiornato dopo l'aggiunta di test.

## Gotcha d'ambiente

- `python` nel PATH è la **stub del Microsoft Store** e non funziona: per `py_compile` usare
  `& 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe' -m py_compile actd_build\auto_copy_transforms_def.py`.
- **Blender non è nel PATH**: usare sempre il percorso completo dell'eseguibile.
- `Set-Content -Encoding UTF8` in PowerShell scrive il **BOM**: i file Python eseguiti dal bridge
  falliscono con `SyntaxError: invalid non-printable character U+FEFF`. Scrivere con
  `[IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))`.
