# Auto Copy Transforms DEF

[![Blender](https://img.shields.io/badge/Blender-4.2%2B%20%7C%205.x-orange)](https://www.blender.org/)
[![License](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-green.svg)]()

**Automatic Copy Transforms constraints for Blender rigs.**  
Map source bones (`DEF-`) to destination bones (`MCH-`, `ORG-`, ...) and build
the constraint stack in a few clicks.

![Info popup](docs/info-popup.png)

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

## Features

| Area | What you get |
|---|---|
| Mapping | Prefix/suffix tokens, custom templates, regex, automatic side detection (`L`/`R`) |
| Source rig | Use the same armature or a separate source armature |
| Constraint types | `COPY_TRANSFORMS`, `COPY_ROTATION`, `COPY_LOCATION`, `COPY_SCALE` |
| Fine control | Mix mode, target/owner space, influence, offset, stack position, remove shear |
| Filters | Bone collections and deform-only bones |
| Diagnostics | Pre-flight checks for missing targets, rest orientation, drivers, collections |
| Auto-prefix | Guesses `DEF-` / `MCH-` / `ORG-` from bone names, never silently changing defaults |
| Learn pattern | Reads an existing copy constraint and reuses its rule on the rest of the rig |
| Maintenance | Convert generated constraints to manual, clean the registry, mute/unmute generated constraints |
| Export | Mapping/registry export to CSV or JSON |

The add-on is a **single Python file** and has no external dependencies.

---

## Installation

### Blender 4.2+ / 5.x — Extension (recommended)

1. Download `auto_copy_transforms_def-1.1.0.zip`.
2. Open **Edit → Preferences → Get Extensions**.
3. Click the arrow in the top-right corner and choose **Install from Disk...**
4. Select the ZIP and enable **Auto Copy Transforms DEF**.

### Blender 3.6 / 4.x — Legacy add-on

1. Open **Edit → Preferences → Add-ons**.
2. Use **Install from Disk...** and select `auto_copy_transforms_def.py`.
3. Enable **Rigging: Auto Copy Transforms DEF**.

### Where to find it

Open the 3D View, press `N`, and select the **Auto Copy Transforms** tab.

---

## Quick start

1. Select the destination armature and enter **Pose Mode**.
2. Open the sidebar: `N → Auto Copy Transforms`.
3. Set the source token (`DEF-`) and destination token (`MCH-`).
4. Click **Preview** to inspect the mapping.
5. Click **Apply constraints**.
6. Use **Remove generated constraints** to undo the operation.

> The defaults are intentionally unchanged from version 1.0.0:
> `COPY_TRANSFORMS`, `DEF-` / `MCH-`.

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

- **Tested:** Blender 5.2 LTS.
- **Fallbacks present but untested:** Blender 3.6 / 4.x.
- **UI language:** Italian. Documentation: English and Italian.

The test suite covers operators, mapping, constraint types, diagnostics,
auto-prefix, pattern learning, maintenance and exports. GUI drawing is tested
manually because headless tests cannot click the interface.

---

## Development

The project keeps the add-on in a single file:

```text
actd_build/auto_copy_transforms_def.py
```

Regression suites live next to it:

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
test_func1.py           functional copy check
```

Run a suite with the full Blender executable:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup --python actd_build\test_actd.py
```

Current status: **370 checks, 0 failures** on Blender 5.2.

### Build the extension

The `packaging` folder contains the manifest, the package READMEs and a
one-command build script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File packaging\build_extension.ps1
```

It creates `dist/auto_copy_transforms_def-1.1.0.zip` and runs Blender's
extension validator. Pass `-Blender <path>` to use a different Blender
executable.

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
