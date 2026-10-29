# Auto Copy Transforms DEF

[![XERJ Corpus Hub contributor](https://hub.xerj.org/contributors/PieroFra/badge.svg)](https://hub.xerj.org/contributors/PieroFra)
[![CI](https://github.com/PieroFra/auto-copy-transforms-def/actions/workflows/tests.yml/badge.svg)](https://github.com/PieroFra/auto-copy-transforms-def/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/PieroFra/auto-copy-transforms-def)](https://github.com/PieroFra/auto-copy-transforms-def/releases/latest)
[![License](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Blender](https://img.shields.io/badge/Blender-4.2%2B-blue)](https://www.blender.org/)
[![Version](https://img.shields.io/badge/version-1.3.0-green.svg)](https://github.com/PieroFra/auto-copy-transforms-def/releases/tag/v1.3.0)
[![Blender Extensions](https://img.shields.io/badge/Blender_Extensions-auto--copy--transforms--def-orange?logo=blender)](https://extensions.blender.org/add-ons/auto-copy-transforms-def/)

**Automatic Copy Transforms constraints for Blender rigs.**  
Automate the creation of Copy Transforms constraints between armatures in a
few clicks and save hours of repetitive rigging work.

Map source bones (`MCH_`) to destination bones (`DEF_`, `ORG_`, ...) and build
the constraint stack in a few clicks.

[Download v1.3.0](https://github.com/PieroFra/auto-copy-transforms-def/releases/tag/v1.3.0) · [Issues](https://github.com/PieroFra/auto-copy-transforms-def/issues)

![Info popup](docs/info-popup-en.png)

---

## Why this add-on

Rigging often means repeating the same operation dozens of times: create a
Copy Transforms constraint on every destination bone, point it at the matching
source bone, then fix spaces, influence and stack order.

**Auto Copy Transforms DEF** does the repetitive part for you, while keeping
the result inspectable and reversible.

- deterministic name mapping
- preview before applying
- generated constraints tracked in a JSON registry
- cleanup that never touches manual constraints

---

## Which file should I download?

Everything is published on the [release page](https://github.com/PieroFra/auto-copy-transforms-def/releases/latest):

| File | What it is | Use it when |
|---|---|---|
| `auto_copy_transforms_def-1.3.0.zip` | Blender Extension package | **Recommended**: install it as an extension (**Edit → Preferences → Get Extensions → Install from Disk...**) |
| `Auto_Copy_Transforms_DEF_1.3.0.rar` | Complete package | You want everything in one archive: the extension ZIP, the legacy classic add-on package (`legacy/auto_copy_transforms_def/`), the documentation (`README.txt`, `README.it.txt`, `LEGGIMI.txt`) and the license (`LICENSE.txt`) |
| `SHA256.txt` | Integrity check | Verify the download before installing: compare the SHA256 of the ZIP/RAR with the hashes listed in the file |
| `legacy/auto_copy_transforms_def/` (inside the RAR) | Classic add-on package | Manual use only, only if you do not use the ZIP: copy the folder into Blender's `scripts/addons` directory and restart Blender |

- **Recommended Blender version: 5.2 LTS** — the only version officially tested (see the compatibility matrix below).
- **Updating from a previous version:** uninstall the previous version before installing the new one. The constraint registry is saved on every armature, so your data is preserved across updates.
- **Registry location:** the JSON registry of the generated constraints is saved as a custom property (ID property `actd_generated`) on the armature object, inside your `.blend` file — not as an external file. It travels with the `.blend` and needs no separate management (see the add-on documentation in the **Info** popup).

---

## Features

| Area | What you get |
|---|---|
| Mapping | Prefix/suffix tokens, custom templates, regex, automatic side detection (`L`/`R`) |
| Source rig | Use the same armature or a separate source armature |
| Constraint types | `COPY_TRANSFORMS`, `COPY_ROTATION`, `COPY_LOCATION`, `COPY_SCALE` |
| Fine control | Mix mode, target/owner space, influence, offset, stack position, remove shear |
| Filters | Bone collections and deform-only bones |
| Diagnostics | Pre-flight checks for missing targets, rest orientation, drivers, collections |
| Auto-prefix | Guesses likely prefixes such as `DEF_` / `MCH_` / `ORG_` from bone names, never silently changing defaults |
| Learn pattern | Reads an existing copy constraint and reuses its rule on the rest of the rig |
| Maintenance | Convert generated constraints to manual, clean the registry, mute/unmute generated constraints |
| Export | Mapping/registry export to CSV or JSON |

The installable add-on is a Python package generated from modular sources; it has no external dependencies.

---

## Installation

### Blender 4.2+ / 5.x — Extension (recommended)

1. Download `auto_copy_transforms_def-1.3.0.zip`.
2. Open **Edit → Preferences → Get Extensions**.
3. Click the arrow in the top-right corner and choose **Install from Disk...**
4. Select the ZIP and enable **Auto Copy Transforms DEF**.

### Blender 4.2+ / 5.x — Legacy add-on

1. Extract the `legacy/auto_copy_transforms_def/` folder from the companion RAR.
2. Copy it into Blender's `scripts/addons` directory.
3. Restart Blender and enable **Rigging: Auto Copy Transforms DEF** in
   **Edit → Preferences → Add-ons**.

The classic add-on package ships in the companion RAR under `legacy/`; it is
not included in the extension ZIP.

### Where to find it

Open the 3D View, press `N`, and select the **Auto Copy Transforms** tab.

### Updating from a previous version

1. Download the new ZIP from the latest release.
2. Install it as an extension (**Edit → Preferences → Get Extensions → Install from Disk...**): Blender replaces the previous version and keeps your settings.
3. Legacy add-on users: replace the old `legacy/auto_copy_transforms_def` folder with the one extracted from the new RAR and restart Blender if prompted.
4. Nothing to redo on existing rigs: the registry stays on the armature object (`actd_generated` ID property) inside each `.blend`, so generated constraints remain tracked after the update.

### Uninstalling

1. Disable the add-on first (extension: menu of the entry in **Get Extensions** → disable; legacy add-on: entry in **Add-ons** → uncheck).
2. Remove it from the same panel (extension: entry menu → **Uninstall**; legacy add-on: entry menu → **Remove**).
3. Your rigs are untouched: constraints stay on the bones and the registry remains as the `actd_generated` ID property on the armature object inside the `.blend` (harmless leftover; removable with **Maintenance → Clean registry** if you reinstall). Replace backups (`actd_replace_backup_*.json`) stay in the folder of the `.blend`.

---

## Quick start

1. Select the destination armature and enter **Pose Mode**.
2. Open the sidebar: `N → Auto Copy Transforms`.
3. Set the source token (`MCH_`) and destination token (`DEF_`).
4. Click **Preview** to inspect the mapping.
5. Click **Apply constraints**.
6. Use **Remove generated constraints** to undo the operation.

> Defaults: `COPY_TRANSFORMS`, tokens `MCH_` / `DEF_`.

---

## How it works

### 1. Choose the tokens

![Main panel](docs/demo-panel.png)

The main panel is organized in three steps: tokens, constraint options and
actions. The quick-start box always shows the flow: **choose tokens → preview →
apply**.

![Demo](docs/demo-ui.gif)

### 2. Check the mapping

![Mapping preview](docs/demo-preview.png)

The preview lists every `MCH_` → `DEF_` pair with its status. Nothing is
applied until you click **Apply constraints**.

### 3. Apply and verify

The preview report confirms the number of valid pairs and the generated
constraints are tracked in the JSON registry. The regression suite verifies
the same behavior on Blender 5.2 (see below).

---

## Constraint types

| Type | Copies | Notes |
|---|---|---|
| `COPY_TRANSFORMS` | Location, rotation, scale | Default; supports mix and remove shear |
| `COPY_ROTATION` | Rotation only | Common for deform bones; supports mix/offset |
| `COPY_LOCATION` | Location only | Supports `use_offset` |
| `COPY_SCALE` | Scale only | Supports `use_offset` |

`use_offset` is exposed only where it is independent from the mix setting
(Copy Location and Copy Scale). Copy Rotation uses its native `OFFSET` mix
mode; Copy Transforms ignores the option with a clear warning.

---

## Maintenance panel

The **Maintenance** sub-panel keeps the generated constraints under control:

- **Convert to manual** — remove constraints from the registry without touching them.
- **Clean registry** — drop orphan entries, type mismatches and missing subtargets.
- **Mute/Unmute generated** — global toggle, manual constraints are never touched.
- **Export CSV / JSON** — one row per registry entry, saved next to the `.blend`
  (or in the current working directory if the file is not saved yet).

Generated constraints are tracked through a JSON registry stored on the
armature object, because Blender constraints do not support ID properties.

---

## Compatibility

| Blender version | Status |
|---|---|
| 4.2 LTS | Declared, not verified |
| 4.3 | Declared, not verified |
| 4.4 | Declared, not verified |
| 5.0 | Declared, not verified |
| 5.1 | Declared, not verified |
| 5.2 LTS | **Officially tested** |

- **Tested officially: Blender 5.2 LTS only.**
- **Declared compatibility: Blender 4.2+** for both installation paths (legacy
  add-on and extension manifest). Blender 4.2–5.1 are declared compatible but
  have not been tested with the full regression suite.
- **UI language:** Italian and English, following Blender's interface language.
- **Documentation:** English and Italian.

The test suite covers operators, mapping, constraint types, diagnostics,
auto-prefix, pattern learning, maintenance and exports. GUI drawing is tested
manually because headless tests cannot click the interface.

---

## Known limitations

- **Blender 4.2–5.1 are declared compatible but have not been tested
  officially.** The official regression environment is Blender 5.2 LTS.
- **Headless tests do not replace a full interactive GUI check:** the
  regression suites verify behavior and logic, but the interface has been
  verified manually on Blender 5.2 only.
- **Generated constraints use an internal JSON registry:** Blender constraints
  do not support ID properties, so generated constraints are tracked via a
  registry stored on the armature object. Removing or renaming them manually
  outside the Maintenance panel can leave orphan entries (removable via
  **Clean registry**).

---

## Development

The installable add-on is a Python package generated from modular sources.
The source of truth is the set of modules in `actd_build/actd_mods/`; the
build step assembles the installable package. The full development
architecture (modified files, generated files, rebuild, tests, versioning)
is documented in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

Regression suites live in `actd_build/`:

```text
test_mod1.py            source armature
test_mod2.py            mix mode and stack position
test_mod3.py            bone-collection filter
test_mod4.py            diagnostics
test_actd.py            historical end-to-end suite
test_mod_types.py       constraint types and use_offset
test_mod_autoprefix.py  automatic token detection
test_mod_learn.py       learn pattern from a constraint
test_mod6.py            maintenance and exports
test_i18n.py            Italian/English UI translations
test_func1.py           functional copy check
test_mod7.py            replace backups and registry classification
```

Run the canonical audit (all 12 suites, with each `test_out.txt`
checked and the expected per-suite counts enforced):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File actd_build\run_all_tests.ps1
```

The same audit runs on Linux, macOS and Windows with the portable runner
(Python standard library only, no PowerShell):

```bash
python actd_build/run_all_tests.py
```

It accepts `-Blender <path>` (default: `BLENDER_EXE` env var, else `blender`
in `PATH`) and `-Suites <comma-separated list>` (default: all suites); it
writes the same `test_out.txt`, enforces the same expected per-suite counts
and exits 0/1 like the Windows wrapper. The PowerShell wrapper uses
`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`
by default; pass `-Blender <path>` to use another executable. For one suite,
invoke Blender directly, for example:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup --python actd_build\test_actd.py
```

Audit status: **644/644 checks passed, 0 failures** on Blender 5.2. The runner
expects: `test_mod1.py` 40, `test_mod2.py` 18, `test_mod3.py` 24,
`test_mod4.py` 43, `test_func1.py` 5, `test_actd.py` 106,
`test_mod_types.py` 49, `test_mod_autoprefix.py` 35,
`test_mod_learn.py` 40, `test_mod6.py` 169, `test_i18n.py` 65 and
`test_mod7.py` 50. The suites report `SUPERATO` (the historical
`test_actd.py` reports `TUTTI I TEST SUPERATI`). The first four suites total
125/125.

![Test results](docs/test-results.png)

Full results table: [docs/TEST_RESULTS.md](docs/TEST_RESULTS.md). The image
above is a graphical summary, not raw test output.  
Release checklist: [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).

### Build the extension

The `packaging` folder contains the manifest, package READMEs and the ZIP
builder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File packaging\build_extension.ps1
```

It creates `dist/auto_copy_transforms_def-1.3.0.zip` and runs Blender's
extension validator. Pass `-Blender <path>` to use a different Blender
executable. To assemble the ZIP, RAR and SHA256 sidecars locally, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File packaging\build_release.ps1
```

The release script invokes the ZIP builder and requires a RAR command-line
tool (`rar.exe` or `WinRAR.exe`; use `-Rar <path>` if it is elsewhere). It only
creates local files in `dist/`: it does not publish, create tags, or use Git.

---

## AI disclosure

This add-on and its documentation were developed with **AI assistance**
(OpenCode agent), under the direction and review of **Pierfrancesco Diodato**.
The author remains responsible for the code, tests, and licensing.

---

## License

This project is free software, licensed under the
**GNU General Public License v3.0 or later**.

See [LICENSE](LICENSE) for the full text.

Copyright (C) 2026 **Pierfrancesco Diodato**.

---

## Author

**Pierfrancesco Diodato**

- Discord: [1176582483165327382](https://discord.com/users/1176582483165327382)

If you use the add-on in a production rig, feedback and bug reports are
welcome.
