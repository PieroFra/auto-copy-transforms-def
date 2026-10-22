# Test results

Environment: **Blender 5.2 LTS**, headless mode. Results recorded by the latest
regression run after the visual-review fixes (all 11 suites rerun).

Command used for every suite:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup --python actd_build\<test>.py
```

Runner canonico (tutte le 11 suite in sequenza, conteggi attesi verificati):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File actd_build\run_all_tests.ps1
```

| Suite | Checks | Result |
|---|---:|---|
| `test_mod1.py` | 40/40 | SUPERATO |
| `test_mod2.py` | 18/18 | SUPERATO |
| `test_mod3.py` | 24/24 | SUPERATO |
| `test_mod4.py` | 43/43 | SUPERATO |
| `test_func1.py` | 5/5 | SUPERATO |
| `test_actd.py` | 106/106 | TUTTI I TEST SUPERATI |
| `test_mod_types.py` | 49/49 | SUPERATO |
| `test_mod_autoprefix.py` | 35/35 | SUPERATO |
| `test_mod_learn.py` | 40/40 | SUPERATO |
| `test_mod6.py` | 113/113 | SUPERATO |
| `test_i18n.py` | 65/65 | SUPERATO |

**Total: 538/538 passed, 0 failures.**

Nell'esecuzione corrente `test_mod1.py`–`test_mod4.py` totalizzano **125/125**.

Esito delle suite: `SUPERATO`; la suite storica `test_actd.py` riporta
`TUTTI I TEST SUPERATI`.

L'immagine `docs/test-results.png` è un riepilogo grafico dei risultati,
non un output grezzo della console. Le schermate GUI in questa cartella sono
state catturate da una sessione Blender 5.2 reale tramite bridge locale, non
simulate.
