# -*- coding: utf-8 -*-
"""Lettura **diretta** e deterministica della UI A.C.T.D. dentro Blender (via bridge TCP).

Il file viene exec-ato DENTRO Blender dal bridge (`__name__ == "__bridge__"`).

Perche' non si intercettano i draw: in Blender 5.2 i metodi di disegno di
`UILayout` non sono piu' esposti come attributi di classe, quindi non e'
patchabili. La via usata e' deterministica:

  1. si carica l'addon, si imposta la lingua, si prepara la scena neutra;
  2. si misura la larghezza **reale** della regione UI (dalla sidebar viva);
  3. si estraggono dal sorgente dell'addon le etichette realmente disegnate
     (AST: `label(text=...)`, `prop(..., text=...)`) e i nomi UI delle property;
  4. ogni testo viene misurato in pixel con `blf.dimensions` e confrontato con
     lo spazio disponibile -> il **troncamento diventa un dato**, non un'ipotesi;
  5. si calcola la **larghezza minima sicura** della sidebar;
  6. si ritaglia la sidebar dagli screenshot e si scala a max 1024 px (IT + EN).

Nessuna dipendenza esterna: solo `bpy`, `blf` e `numpy` (fornito da Blender).
"""

import ast
import importlib
import os
import sys
import tempfile
from pathlib import Path

import bpy

_SCRIPT_FILENAME = "actd_ui_probe.py"


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
SCRIPTS_DIR = str(_SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
_PROJECT_ROOT = _project_root(_SCRIPTS_DIR)
ADDON_PATH = str(_PROJECT_ROOT / "actd_build" / "auto_copy_transforms_def.py")
# Output in area temporanea; sovrascrivibile con ACTD_GUI_OUT.
OUT_DIR = os.environ.get("ACTD_GUI_OUT") or str(
    Path(tempfile.gettempdir()) / "opencode" / "actd_gui")
LANGS = ("it", "en")

MARGIN = 24.0          # px di margine laterale della regione UI
MAX_WIDTH = 1024       # larghezza massima dei PNG finali
# In Blender 5.x i pannelli senza bl_category finiscono in un tab col nome del
# bl_label: il tab di A.C.T.D. e' quindi "Auto Copy Transforms".
PANEL_CATEGORIES = ("Auto Copy Transforms", "Rigging")


# --- estrazione delle etichette disegnate -------------------------------------
def _drawn_labels():
    """Etichette letteralmente disegnate dal pannello, con il loro tipo."""
    out = []
    try:
        with open(ADDON_PATH, "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
    except Exception as exc:
        print("UI_PARSE_ERROR {0}".format(type(exc).__name__))
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = getattr(node.func, "attr", "")
        if fname not in ("label", "prop", "operator"):
            continue
        text = None
        for kw in node.keywords:
            if kw.arg == "text" and isinstance(kw.value, ast.Constant):
                if isinstance(kw.value.value, str) and kw.value.value:
                    text = kw.value.value
        if fname == "prop" and text is None:
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                text = "\x00PROP:" + str(node.args[1].value)
        if text:
            out.append((fname, text))
    # de-duplica mantenendo l'ordine
    seen = set()
    uniq = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    return uniq


def _prop_ui_name(prop_name):
    """Nome UI (non tradotto) della property, se raggiungibile."""
    try:
        settings = bpy.context.scene.actd_settings
        return settings.bl_rna.properties[prop_name].name
    except Exception:
        return None


# --- misure -------------------------------------------------------------------
def _text_width(text, scale):
    """Larghezza del testo in pixel di schermo (font UI di default, dpi 72)."""
    try:
        import blf
        width, _height = blf.dimensions(0, text)
    except Exception:
        return 0.0
    return float(width) * scale


def _ui_scale():
    try:
        return float(getattr(bpy.context.preferences.view, "ui_scale", 1.0) or 1.0)
    except Exception:
        return 1.0


# --- regione UI ---------------------------------------------------------------
def _sidebar_region():
    """(window, area, region) della sidebar della vista 3D, col tab A.C.T.D. attivo."""
    win = bpy.context.window_manager.windows[0]
    for area in win.screen.areas:
        if area.type != "VIEW_3D":
            continue
        try:
            area.spaces.active.show_region_ui = True
        except Exception:
            pass
        region = None
        for reg in area.regions:
            if reg.type == "UI":
                region = reg
        if region is not None:
            for category in PANEL_CATEGORIES:
                try:
                    region.active_panel_category = category
                    break
                except Exception:
                    continue
        return win, area, region
    return win, None, None


def _region_box(region, area=None):
    """(x, y, w, h) della regione in coordinate finestra (origine in basso)."""
    if region is None:
        return None
    try:
        x = int(region.x)
        y = int(region.y)
        if area is not None:
            x += int(area.x)
            y += int(area.y)
        return (x, y, int(region.width), int(region.height))
    except Exception:
        return None


# --- ritaglio e scala degli screenshot ----------------------------------------
def _crop_and_scale(src_png, dst_png, box, max_width=MAX_WIDTH):
    """Ritaglia il riquadro dalla finestra e scala a max_width. Ritorna (w, h)."""
    try:
        import numpy as np
    except Exception:
        return (0, 0)
    if not os.path.exists(src_png):
        return (0, 0)
    try:
        image = bpy.data.images.load(src_png, check_existing=False)
        width, height = image.size
        pixels = np.array(image.pixels[:], dtype=np.float32).reshape(height, width, 4)
        bpy.data.images.remove(image)
    except Exception:
        return (0, 0)
    if box is not None:
        x0, y0, w, h = box
        x0 = max(0, min(x0, width - 1))
        y0 = max(0, min(y0, height - 1))
        w = max(1, min(w, width - x0))
        h = max(1, min(h, height - y0))
        pixels = pixels[y0:y0 + h, x0:x0 + w, :]
    ch, cw = pixels.shape[0], pixels.shape[1]
    if cw > max_width:
        factor = int(cw // max_width) + 1
        nh, nw = ch // factor, cw // factor
        pixels = pixels[:nh * factor, :nw * factor, :].reshape(nh, factor, nw, factor, 4).mean(axis=(1, 3))
    ch, cw = pixels.shape[0], pixels.shape[1]
    try:
        out = bpy.data.images.new("actd_crop", width=cw, height=ch, alpha=True)
        out.pixels = pixels.ravel().tolist()
        os.makedirs(os.path.dirname(dst_png), exist_ok=True)
        out.filepath_raw = dst_png
        out.file_format = "PNG"
        out.save()
        bpy.data.images.remove(out)
    except Exception:
        return (0, 0)
    return (cw, ch)


# --- flusso principale --------------------------------------------------------
def probe(lang):
    """Prepara la scena, misura la regione e valuta ogni etichetta."""
    gui = importlib.import_module("actd_gui_check")
    gui.prepare(lang)

    win, area, region = _sidebar_region()
    try:
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
    except Exception:
        pass

    box = _region_box(region, area)
    width = box[2] if box else 0
    scale = _ui_scale()
    available = max(0.0, float(width) - MARGIN)

    print("UI_REGION width={0} available={1:.0f} scale={2:g}".format(width, available, scale))

    labels = _drawn_labels()
    flagged = 0
    widest = 0.0
    for kind, text in labels:
        if text.startswith("\x00PROP:"):
            name = _prop_ui_name(text[6:])
            if not name:
                continue
            text = name
        w = _text_width(text, scale)
        widest = max(widest, w)
        if available <= 0:
            status = "NOWIDTH"
        elif w > available:
            status = "TRUNC?"
            flagged += 1
        elif w > available * 0.85:
            status = "TIGHT"
        else:
            status = "OK"
        print('UI_TEXT {0} kind={1} w={2:.0f} avail={3:.0f} "{4}"'.format(
            status, kind, w, available, text))

    min_safe = widest + MARGIN
    print("UI_SUMMARY labels={0} flagged={1} region_width={2} min_safe_width={3:.0f}".format(
        len(labels), flagged, width, min_safe))
    # screenshot nella stessa sessione: niente doppia preparazione
    try:
        capture(lang, box)
    except Exception as exc:
        print("SHOT_ERROR {0} {1}: {2}".format(lang, type(exc).__name__, exc))
    return width, len(labels), flagged, min_safe


def capture(lang, box):
    """Screenshot della finestra + ritaglio della sidebar (max 1024 px).

    Non riprepara la scena: va chiamata subito dopo probe() (stessa sessione,
    stessa regione) per non raddoppiare il tempo di preparazione.
    """
    gui = importlib.import_module("actd_gui_check")
    gui.capture(lang)          # scrive actd-panel-<lang>.png / actd-preview-<lang>.png
    os.makedirs(OUT_DIR, exist_ok=True)
    full = os.path.join(OUT_DIR, "actd-panel-{0}.png".format(lang))
    crop = os.path.join(OUT_DIR, "actd-ui-{0}.png".format(lang))
    size = _crop_and_scale(full, crop, box)
    print("SHOT {0} full={1} crop={2} {3}x{4}".format(
        lang, os.path.basename(full), os.path.basename(crop), size[0], size[1]))
    return crop


def main():
    for lang in LANGS:
        try:
            width, labels, flagged, min_safe = probe(lang)
            print("PROBE {0} region_width={1} labels={2} flagged={3} min_safe={4:.0f}".format(
                lang, width, labels, flagged, min_safe))
        except Exception as exc:
            print("PROBE_ERROR {0} {1}: {2}".format(lang, type(exc).__name__, exc))
    print("DONE")


if __name__ in {"__main__", "__bridge__"}:
    main()
