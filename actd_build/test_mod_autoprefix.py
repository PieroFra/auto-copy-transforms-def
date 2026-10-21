# -*- coding: utf-8 -*-
"""Test headless dell'auto-prefisso (PASSO 3).

Verifica l'estrazione del prefisso, lo scoring, i fallback ai default e
l'operatore actd.guess_prefixes.

Esecuzione:
    blender.exe --background --factory-startup --python test_mod_autoprefix.py
"""

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


def reset_scene():
    if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for arm in list(bpy.data.armatures):
        bpy.data.armatures.remove(arm)
    bpy.context.view_layer.update()


def make_armature(name, bone_names):
    arm_data = bpy.data.armatures.new(name + "_data")
    obj = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(obj)
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.object.mode_set(mode='EDIT')
    for i, bname in enumerate(bone_names):
        eb = arm_data.edit_bones.new(bname)
        eb.head = (0.0, float(i), 0.0)
        eb.tail = (0.0, float(i) + 1.0, 0.0)
    bpy.ops.object.mode_set(mode='POSE')
    return obj


def settings():
    return bpy.context.scene.actd_settings


def prepare(source_object=None):
    s = settings()
    s.source_object = source_object
    s.source_token = "ZZZ-"
    s.dest_token = "YYY-"
    s.source_token_type = 'SUFFIX'
    s.dest_token_type = 'SUFFIX'
    s.last_report = ""
    return s


print("===== TEST AUTO-PREFISSO =====", flush=True)
addon.register()

# ---------------------------------------------------------------------------
print("\n[1] Estrazione del prefisso", flush=True)
try:
    casi = [
        ("DEF-Hand.L", "DEF-"),
        ("MCH_Spine", "MCH_"),
        ("ORG.Arm", "ORG."),
        ("CTRL Arm", "CTRL "),
        ("DEFHand", "DEF"),
        ("MCHHand.L", "MCH"),
        ("Hand.L", ""),
        ("", ""),
    ]
    for nome, atteso in casi:
        trovato = addon._extract_prefix(nome)
        check("prefisso di %r = %r" % (nome, atteso), trovato == atteso, trovato)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[2] Stessa armatura: DEF- / MCH-", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig2", [
        "DEF-Hand.L", "DEF-Hand.R", "DEF-Spine",
        "MCH-Hand.L", "MCH-Hand.R", "MCH-Spine",
    ])
    s = prepare()
    s.source_object = None
    res = bpy.ops.actd.guess_prefixes()
    check("operatore FINISHED", res == {'FINISHED'}, res)
    check("token sorgente DEF-", s.source_token == "DEF-", s.source_token)
    check("token destinazione MCH-", s.dest_token == "MCH-", s.dest_token)
    check("tipi token riportati a PREFIX",
          s.source_token_type == 'PREFIX' and s.dest_token_type == 'PREFIX',
          (s.source_token_type, s.dest_token_type))
    check("report di stima riuscita",
          "stessa armatura" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[3] Armature separate: ORG- / CTRL-", flush=True)
try:
    reset_scene()
    src = make_armature("Src3", ["ORG-A", "ORG-B", "ORG-C"])
    dst = make_armature("Dst3", ["CTRL-A", "CTRL-B", "CTRL-C"])
    s = prepare(source_object=src)
    res = bpy.ops.actd.guess_prefixes()
    check("operatore FINISHED", res == {'FINISHED'}, res)
    check("token sorgente ORG-", s.source_token == "ORG-", s.source_token)
    check("token destinazione CTRL-", s.dest_token == "CTRL-", s.dest_token)
    check("report dalle due armature",
          "due armature" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[4] Stima non affidabile: default invariati", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig4", ["alpha", "beta", "gamma"])
    s = prepare()
    res = bpy.ops.actd.guess_prefixes()
    check("operatore FINISHED", res == {'FINISHED'}, res)
    check("default sorgente DEF-", s.source_token == "DEF-", s.source_token)
    check("default destinazione MCH-", s.dest_token == "MCH-", s.dest_token)
    check("report segnala l'assenza di prefissi",
          "Nessun prefisso" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[5] Un solo prefisso affidabile", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig5", ["DEF-A", "DEF-B", "root", "camera"])
    s = prepare()
    bpy.ops.actd.guess_prefixes()
    check("sorgente stimata DEF-", s.source_token == "DEF-", s.source_token)
    check("destinazione lasciata a MCH-", s.dest_token == "MCH-", s.dest_token)
    check("report segnala un solo prefisso",
          "Un solo prefisso" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[6] Stesso prefisso nelle due armature", flush=True)
try:
    reset_scene()
    src = make_armature("Src6", ["ORG-A", "ORG-B"])
    dst = make_armature("Dst6", ["ORG-C", "ORG-D"])
    s = prepare(source_object=src)
    bpy.ops.actd.guess_prefixes()
    check("sorgente ORG-", s.source_token == "ORG-", s.source_token)
    check("destinazione MCH- (nessuna alternativa)",
          s.dest_token == "MCH-", s.dest_token)
    check("report segnala l'uguaglianza",
          "uguale alla sorgente" in s.last_report,
          s.last_report.replace("\n", " / "))

    reset_scene()
    src = make_armature("Src6b", ["ORG-A", "ORG-B"])
    dst = make_armature(
        "Dst6b", ["ORG-C", "ORG-D", "ORG-E", "CTRL-F", "CTRL-G"]
    )
    s = prepare(source_object=src)
    bpy.ops.actd.guess_prefixes()
    check("sorgente ORG-", s.source_token == "ORG-", s.source_token)
    check("destinazione usa il secondo prefisso CTRL-",
          s.dest_token == "CTRL-", s.dest_token)
    check("report segnala il secondo prefisso",
          "usato il secondo" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[7] Parità: ordine alfabetico DEF- / MCH-", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig7", [
        "DEF-A", "DEF-B", "MCH-A", "MCH-B",
    ])
    s = prepare()
    bpy.ops.actd.guess_prefixes()
    check("parità risolta come DEF-/MCH-",
          s.source_token == "DEF-" and s.dest_token == "MCH-",
          (s.source_token, s.dest_token))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[8] Operatore registrato", flush=True)
try:
    check("actd.guess_prefixes disponibile",
          hasattr(bpy.ops.actd, "guess_prefixes"))
    check("classe presente nella registrazione",
          addon.ACTD_OT_guess_prefixes in addon._classes)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST AUTO-PREFISSO =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)
