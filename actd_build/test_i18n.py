# -*- coding: utf-8 -*-
"""Test headless delle traduzioni italiano/inglese della UI."""

import os
import sys
import traceback

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto_copy_transforms_def as addon  # noqa: E402

OK, FAIL = [], []


def check(name, cond, extra=""):
    (OK if cond else FAIL).append(
        name + ("" if cond else "  [" + str(extra) + "]")
    )
    print(
        ("  OK   " if cond else "  FAIL ") + name
        + ("" if cond else "  [" + str(extra) + "]"),
        flush=True,
    )


print("===== TEST I18N =====", flush=True)
addon.register()
original_language = bpy.context.preferences.view.language

try:
    bpy.context.preferences.view.language = 'en_US'
    check("locale inglese attivo",
          bpy.app.translations.locale.lower().startswith("en"),
          bpy.app.translations.locale)
    check("_is_english_ui() vero", addon._is_english_ui() is True)
    check("traduzione etichetta token",
          bpy.app.translations.pgettext("Token di mappatura") == "Mapping tokens",
          bpy.app.translations.pgettext("Token di mappatura"))
    check("traduzione pulsante Applica",
          bpy.app.translations.pgettext("Applica constraint")
          == "Apply constraints")
    check("traduzione proprietà (contesto Property)",
          bpy.app.translations.pgettext(
              "Token sorgente (Target)", "Property")
          == "Source token (Target)")
    check("traduzione creatore",
          bpy.app.translations.pgettext("Creatore: ") == "Creator: ")
    check("README inglese disponibile",
          bool(addon.README_TEXT_EN.strip())
          and "Creates copy constraints" in addon.README_TEXT_EN)
    check("licenza inglese disponibile",
          bool(addon.LICENSE_NOTICE_EN.strip()))

    bpy.context.preferences.view.language = 'it_IT'
    check("locale italiano attivo",
          not bpy.app.translations.locale.lower().startswith("en"),
          bpy.app.translations.locale)
    check("_is_english_ui() falso", addon._is_english_ui() is False)
    check("sorgente italiana invariata",
          bpy.app.translations.pgettext("Token di mappatura")
          == "Token di mappatura")
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    bpy.context.preferences.view.language = original_language

print("\n===== RIEPILOGO TEST I18N =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)
