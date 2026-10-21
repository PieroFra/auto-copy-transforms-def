# Test results

Environment: **Blender 5.2 LTS**, headless mode.

Command used for every suite:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup --python actd_build\<test>.py
```

| Suite | Checks | Result |
|---|---:|---|
| `test_mod1.py` | 40/40 | PASS |
| `test_mod2.py` | 18/18 | PASS |
| `test_mod3.py` | 16/16 | PASS |
| `test_mod4.py` | 18/18 | PASS |
| `test_func1.py` | 5/5 | PASS |
| `test_actd.py` | 106/106 | PASS |
| `test_mod_types.py` | 49/49 | PASS |
| `test_mod_autoprefix.py` | 35/35 | PASS |
| `test_mod_learn.py` | 40/40 | PASS |
| `test_mod6.py` | 48/48 | PASS |
| `test_i18n.py` | 14/14 | PASS |

**Total: 389/389 passed.**

The test image in `docs/test-results.png` is a summary generated from these
results. The GUI screenshots in this folder were captured from a real Blender
5.2 session through a local bridge, not mocked.
