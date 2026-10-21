---
name: Blender Bridge
description: Run Python inside Blender, install the add-on, test it headless or in a GUI, and capture UI screenshots through a local TCP bridge.
---

# Blender Bridge

Use this skill when a task needs **real Blender execution**: testing the
add-on, calling `bpy` operators, inspecting a `.blend`, installing an
extension, or taking a screenshot of Blender's interface.

The bridge is a small TCP server that executes Python in Blender's main
thread. It has no external dependencies and does not require the BlenderMCP
extension.

## Modes

| Mode | Use it for | Window |
|---|---|---|
| **background** (default) | tests, operators, file inspection, install checks | none |
| **GUI** | visual checks, screenshots, panel/popup inspection | opens a window |

Prefer **background** unless the task explicitly needs pixels. Use
`--factory-startup` for the GUI so the user's configuration and unsaved files
are not touched.

## Start the bridge

Set a port first. Use a non-default port if another bridge may be running.

```powershell
$env:BLENDER_BRIDGE_PORT = '9878'
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$bridge = '.opencode\skills\blender-bridge\scripts\blender_bridge.py'

# Headless: no window
$p = Start-Process -FilePath $blender `
  -ArgumentList @('--background', '--factory-startup', '--python', ('"' + $bridge + '"')) `
  -PassThru
$p.Id
```

Wait for `127.0.0.1:9878` to listen before calling it:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 9878
```

For a GUI instance:

```powershell
$p = Start-Process -FilePath $blender `
  -ArgumentList @('--factory-startup', '--no-window-focus', '--python', ('"' + $bridge + '"')) `
  -PassThru
```

`--no-window-focus` opens the test window behind other windows, so it does not
steal focus. Use GUI mode only when pixels are required.

The bridge prints `BRIDGE_MODE background` or `BRIDGE_MODE gui` to stdout.

## Call the bridge

Use Blender's bundled Python (or any Python 3) for the client:

```powershell
$py = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe'
$client = '.opencode\skills\blender-bridge\scripts\bridge_call.py'

& $py $client -c "import bpy; print(bpy.app.version_string)"
```

Or put the code in a file:

```powershell
& $py $client .\probe.py
```

The response contains `OK`, captured stdout, and a traceback on failure.
The bridge executes arbitrary Python with the current Blender session's
privileges. Keep it bound to `127.0.0.1` and stop it when done.

## GUI screenshots

Use Blender's own screenshot operator; it captures the real UI including
popups and is more reliable than OS screen capture:

```python
import bpy

win = bpy.context.window_manager.windows[0]
with bpy.context.temp_override(window=win, screen=win.screen):
    bpy.ops.screen.screenshot(filepath=r"C:\temp\shot.png")
```

For modal popups, invoke the operator first, then call the screenshot from a
second bridge request:

```python
win = bpy.context.window_manager.windows[0]
with bpy.context.temp_override(window=win):
    bpy.ops.actd.show_info('INVOKE_DEFAULT')
```

If a popup is taller than the window it can be clipped. Keep info dialogs
short; put long documentation in files or a web page.

## Install an extension

Build and validate first:

```powershell
& $blender --background --factory-startup --command extension build `
  --source-dir .\extension --output-filepath .\dist\addon.zip
& $blender --background --factory-startup --command extension validate `
  .\dist\addon.zip
```

Install into an **isolated** profile for tests:

```powershell
$env:BLENDER_USER_CONFIG = "$env:TEMP\blender-test\config"
$env:BLENDER_USER_EXTENSIONS = "$env:TEMP\blender-test\extensions"
& $blender --background --command extension install-file `
  -r user_default -e .\dist\addon.zip
```

Install into the real profile only when the user asked for it:

```powershell
& $blender --background --command extension install-file `
  -r user_default -e .\dist\addon.zip
```

The extension is not reloaded in an already-running Blender instance. Save
the user's file and restart Blender, or disable/enable the extension from
Preferences.

## Safety and cleanup

- Never kill or restart a Blender process you did not start. Check the PID and
  the window title first.
- Use `--factory-startup` for GUI tests; do not open the user's startup file.
- Stop only your bridge PID when finished:

```powershell
Stop-Process -Id <bridge_pid> -Force
```

- If the bridge is not needed, do not leave it listening.
- Do not print secrets, tokens, or full user paths in reports.

## Optional: official BlenderMCP

If the `lab_blender_org/mcp` extension is installed, it can run a similar
bridge without this skill:

```powershell
& $blender --background file.blend --command blender_mcp
```

This skill remains the dependency-free option and works entirely from a
single script.
