# -*- coding: utf-8 -*-
"""Verifica visiva A.C.T.D.: scena neutra + cattura dell'N-panel.

Il file viene exec-ato DENTRO Blender dal bridge TCP (niente socket/json qui):
usa solo `bpy`, nessuna dipendenza esterna. Config = costanti qui sotto.
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import bpy

# Configurazione -------------------------------------------------------------
_SCRIPT_FILENAME = "actd_gui_check.py"


def _resolve_scripts_dir():
    """Cartella degli script, derivata dal percorso del file (nessun path assoluto).

    Ordine di risoluzione:
      1. variabile d'ambiente ACTD_SCRIPTS_DIR (impostata dal runner);
      2. `__file__` (script eseguito come file o importato come modulo);
      3. `sys.modules['__main__'].__file__`: il bridge viene avviato con
         `--python <scripts>/blender_bridge.py`, quindi sta nella stessa cartella;
      4. ricerca del file in `sys.path`;
      5. cartella di lavoro come ultima risorsa.
    """
    override = os.environ.get("ACTD_SCRIPTS_DIR")
    if override:
        return Path(override).resolve()
    here = globals().get("__file__")
    if here:
        return Path(here).resolve().parent
    main_file = getattr(sys.modules.get("__main__"), "__file__", None)
    if main_file:
        return Path(main_file).resolve().parent
    for entry in sys.path:
        try:
            candidate = Path(entry).resolve() / _SCRIPT_FILENAME
        except Exception:
            continue
        if candidate.is_file():
            return candidate.parent
    return Path.cwd().resolve()


def _project_root(scripts_dir):
    """Radice del progetto: la cartella che contiene `actd_build/`."""
    for candidate in (scripts_dir, *scripts_dir.parents):
        if (candidate / "actd_build" / "auto_copy_transforms_def.py").is_file():
            return candidate
    # Fallback esplicito: scripts -> blender-bridge -> skills -> .opencode -> root
    parents = scripts_dir.parents
    return parents[3] if len(parents) > 3 else scripts_dir


_SCRIPTS_DIR = _resolve_scripts_dir()
_PROJECT_ROOT = _project_root(_SCRIPTS_DIR)
ADDON_PATH = str(_PROJECT_ROOT / "actd_build" / "auto_copy_transforms_def.py")
# Output in area temporanea; sovrascrivibile con ACTD_GUI_OUT.
OUT_DIR = os.environ.get("ACTD_GUI_OUT") or str(
    Path(tempfile.gettempdir()) / "opencode" / "actd_gui")
LANGS = ("it", "en")

_MOD_NAME = "actd_gui_addon"  # nome modulo isolato per l'import fresco
_LANG_CODES = {"it": "it_IT", "en": "en_US"}
_BONES = ("DEF_Hand.L", "DEF_Hand.R", "DEF_Spine",
          "MCH_Hand.L", "MCH_Hand.R", "MCH_Spine")
_PANEL_MIN_WIDTH = 520  # larghezza desiderata della sidebar

def _load_addon():
    """Importa il file addon come modulo nuovo e lo registra."""
    if _MOD_NAME in sys.modules:
        try:
            sys.modules[_MOD_NAME].unregister()
        except Exception:
            pass
        del sys.modules[_MOD_NAME]
    spec = importlib.util.spec_from_file_location(_MOD_NAME, ADDON_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        mod.register()
    except Exception:
        # Classi gia' registrate da una sessione precedente: si usa la UI attiva
        pass
    return mod

def _clear_objects():
    # Svuota la scena dagli oggetti preesistenti
    if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

def _build_rig():
    # Armatura neutra 'Rig' con le ossa usate dai test di mappatura
    data = bpy.data.armatures.new("RigData")
    rig = bpy.data.objects.new("Rig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    override = dict(active_object=rig, object=rig,
                    selected_objects=[rig], selected_editable_objects=[rig])
    with bpy.context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')
        for index, name in enumerate(_BONES):
            bone = data.edit_bones.new(name)
            bone.head = (0.0, 0.0, index * 0.1)
            bone.tail = (0.0, 0.0, index * 0.1 + 0.08)
        bpy.ops.object.mode_set(mode='POSE')
    return rig

def prepare(lang):
    """Addon + lingua + scena neutra + anteprima popolata."""
    _load_addon()
    view = bpy.context.preferences.view
    view.language = _LANG_CODES.get(lang, "en_US")
    view.use_translate_interface = True

    _clear_objects()
    rig = _build_rig()
    settings = bpy.context.scene.actd_settings
    settings.source_token = "DEF_"
    settings.dest_token = "MCH_"
    settings.source_object = None

    override = dict(active_object=rig, object=rig,
                    selected_objects=[rig], selected_editable_objects=[rig])
    with bpy.context.temp_override(**override):
        bpy.ops.actd.preview()  # popola UIList e report del pannello
    # Osso attivo/selezionato in Pose Mode
    _select_active_bone(rig, "MCH_Hand.L")
    bpy.context.view_layer.update()
    return rig

def _select_active_bone(rig, bone_name):
    """Seleziona e attiva un osso in Pose Mode senza far fallire la cattura.

    In Blender 5.x la selezione vive sui PoseBone (rig.pose.bones), mentre
    rig.data.bones[i].select non esiste piu'. Si prova il percorso pose e, se
    non disponibile, si ripiega sui dati dell'armatura.
    """
    try:
        pose = getattr(rig, "pose", None)
        if pose is not None:
            try:
                for pb in pose.bones:
                    try:
                        pb.select = (pb.name == bone_name)
                    except Exception:
                        pass
            except Exception:
                pass
            # Osso attivo: prima rig.pose.bones.active, poi rig.data.bones.active
            try:
                pose.bones.active = pose.bones[bone_name]
            except Exception:
                try:
                    rig.data.bones.active = rig.data.bones[bone_name]
                except Exception:
                    pass
        else:
            try:
                for bone in rig.data.bones:
                    bone.select = (bone.name == bone_name)
            except Exception:
                pass
            try:
                rig.data.bones.active = rig.data.bones[bone_name]
            except Exception:
                pass
    except Exception:
        pass

def _ui_width(ui):
    """Larghezza corrente della regione UI (0 se non disponibile)."""
    if ui is None:
        return 0
    try:
        return int(getattr(ui, "width", 0) or 0)
    except Exception:
        return 0

def _set_sidebar_width(ui, area):
    """Impone una larghezza utile alla sidebar; restituisce quella ottenuta.

    `Region.width` e' read-only su molte versioni: in quel caso si usa la
    preferenza esplicita "Region Width" dell'interfaccia (ui_region_width).
    """
    target = _PANEL_MIN_WIDTH
    limit = 320
    if area is not None:
        try:
            limit = max(320, int(area.width) - 200)
        except Exception:
            limit = 320
    # 1) Setter diretto sulla regione (funziona solo dove non e' read-only)
    if ui is not None:
        try:
            ui.width = min(max(_ui_width(ui), target), limit)
        except Exception:
            pass
    width = _ui_width(ui)
    if width < target:
        # 2) Fallback esplicito: preferenza "Region Width" (sidebar piu' larga)
        try:
            view = bpy.context.preferences.view
            current = int(getattr(view, "ui_region_width", 0) or 0)
            if current > 0:
                view.ui_region_width = min(max(current, target), 320)
                try:
                    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                except Exception:
                    pass
                width = _ui_width(ui) or width
        except Exception:
            pass
    return width

def _view3d():
    """Restituisce (window, area 3D View, region UI) e apre la sidebar."""
    win = bpy.context.window_manager.windows[0]
    for area in win.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        if area.spaces.active is not None:
            area.spaces.active.show_region_ui = True
        ui = next((reg for reg in area.regions if reg.type == 'UI'), None)
        return win, area, ui
    return win, None, None

def _shot(path, win, area, region):
    """Salva un PNG della region/area; fallback alla finestra intera."""
    if area is not None:
        try:
            ctx = dict(window=win, screen=win.screen, area=area)
            if region is not None:
                ctx["region"] = region
            with bpy.context.temp_override(**ctx):
                bpy.ops.screen.screenshot_area(filepath=path)
            if os.path.exists(path):
                return path
        except Exception:
            pass
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.screen.screenshot(filepath=path)
    return path

def capture(lang):
    """Cattura sidebar (panel) e area 3D completa (preview)."""
    os.makedirs(OUT_DIR, exist_ok=True)
    win, area, ui = _view3d()
    try:
        # Senza redraw la lingua tradotta non arriva a schermo
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=2)
    except Exception:
        pass
    width = _set_sidebar_width(ui, area)
    try:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=2)
    except Exception:
        pass
    width = _ui_width(ui) or width
    paths = [os.path.join(OUT_DIR, "actd-panel-{0}.png".format(lang)),
             os.path.join(OUT_DIR, "actd-preview-{0}.png".format(lang))]
    _shot(paths[0], win, area, ui)
    _shot(paths[1], win, area, None)
    sizes = []
    for path in paths:
        with open(path, "rb") as handle:
            head = handle.read(24)  # header IHDR del PNG
        ok = len(head) >= 24 and head[:8] == b"\x89PNG\r\n\x1a\n"
        sizes.append((int.from_bytes(head[16:20], "big"),
                      int.from_bytes(head[20:24], "big")) if ok else (0, 0))
    return sizes[0], sizes[1], width

def main():
    for lang in LANGS:
        try:
            prepare(lang)
            panel, preview, width = capture(lang)
            print("SHOT {0} panel={1}x{2} preview={3}x{4} SIDEBAR_WIDTH={5}".format(
                lang, panel[0], panel[1], preview[0], preview[1], width))
        except Exception as exc:
            print("ERROR {0} {1}".format(lang, type(exc).__name__))
    print("DONE")

# Il bridge exec-a il file con __name__ = "__bridge__".
if __name__ in {"__main__", "__bridge__"}:
    main()
