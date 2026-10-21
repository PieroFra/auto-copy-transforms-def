# Test results

Environment recorded by the completed audit: **Blender 5.2 LTS**, headless mode.
These are documented audit results; this document-alignment task did not rerun
tests or build the extension.

Command used for every suite:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup --python actd_build\<test>.py
```

| Suite | Checks | Result |
|---|---:|---|
| `test_mod1.py` | 40/40 | SUPERATO |
| `test_mod2.py` | 18/18 | SUPERATO |
| `test_mod3.py` | 16/16 | SUPERATO |
| `test_mod4.py` | 18/18 | SUPERATO |
| `test_func1.py` | 5/5 | SUPERATO |
| `test_actd.py` | 106/106 | SUPERATO |
| `test_mod_types.py` | 49/49 | SUPERATO |
| `test_mod_autoprefix.py` | 35/35 | SUPERATO |
| `test_mod_learn.py` | 40/40 | SUPERATO |
| `test_mod6.py` | 48/48 | SUPERATO |
| `test_i18n.py` | 14/14 | SUPERATO |

**Total: 389/389 passed (SUPERATO), 0 failures.**

Le suite stampano `Passati`, `Falliti` e `RISULTATO: SUPERATO/FALLITO`; la
suite storica `test_actd.py` riporta `TUTTI I TEST SUPERATI`.

The test image in `docs/test-results.png` is a summary generated from these
results. The GUI screenshots in this folder were captured from a real Blender
5.2 session through a local bridge, not mocked.
