# Development architecture

The repository separates the **source modules** from the **generated
package**. What you edit and what ships are two different layers, kept in
sync by the build step.

## Modified files (source of truth)

- `actd_build/actd_mods/*.py` — the nine add-on modules (header, tokens,
  registry, properties, logic, operators, UI, i18n, main). Every change to
  the add-on happens here, one module at a time.
- `actd_build/test_*.py` — the twelve regression suites executed by the
  runner (`actd_build/run_all_tests.ps1` on Windows, `run_all_tests.py`
  portable, same counts enforced).

## Generated files (build output — do not edit by hand)

- `actd_build/auto_copy_transforms_def/` — the installable package: the
  nine modules copied from `actd_mods/` plus a generated `__init__.py`.
  This is the only artifact Blender loads.
- `actd_build/INDEX.md` — AST map of the package symbols, regenerated at
  every verification run.
- `dist/` — release ZIP/RAR archives with their SHA256 sidecars.

## Regenerating the package

After editing any module, rebuild the package:

```bash
python packaging/build_package.py build
```

The build copies the modules and generates `__init__.py`. CI re-runs the
build and fails if the committed package differs from the regenerated one.

## Tests

- Full regression (12 suites, 644 checks):
  `powershell -NoProfile -ExecutionPolicy Bypass -File actd_build\run_all_tests.ps1`
- Deterministic gate (build step + py_compile + suites + telemetry audit):
  `powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\gate.ps1`

The suites import the generated package, never the sources directly: a
stale package means the tests run on old code.

## Version

`packaging/version.json` is the single source of truth. From it derive, in
this order: the `bl_info` header (`actd_mods/actd_header.py`), the extension
manifest (`packaging/blender_manifest.toml`) and the version shown in the
READMEs. The build script (`packaging/build_package.py`) verifies the
coherence of all of them and fails on mismatch.
