# -*- coding: utf-8 -*-
"""Test headless del Modulo 4: diagnostica pre-flight."""

import os
import sys
import traceback
from math import radians

import bpy
from mathutils import Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto_copy_transforms_def as addon  # noqa: E402

OK, FAIL = [], []


def check(name, cond, extra=""):
    (OK if cond else FAIL).append(name + ("" if cond else "  [" + str(extra) + "]"))
    print(("  OK   " if cond else "  FAIL ") + name +
          ("" if cond else "  [" + str(extra) + "]"), flush=True)


def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()


def make_armature(name, bone_specs, roll_offset=0.0):
    """bone_specs: lista di (nome, parent_name_or_None)."""
    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(obj)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for bn, parent in bone_specs:
        eb = arm.edit_bones.new(bn)
        eb.head = (0.0, 0.0, 0.0)
        eb.tail = (0.0, 1.0, 0.0)
        eb.roll = roll_offset
        if parent:
            eb.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def activate(obj, pose=False):
    if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if pose:
        bpy.ops.object.mode_set(mode='POSE')


def settings():
    return bpy.context.scene.actd_settings


def base_settings():
    s = settings()
    s.source_token = "DEF-"
    s.dest_token = "MCH-"
    s.source_object = None
    s.existing_mode = 'KEEP'
    s.update_mode = 'MISSING_ONLY'
    s.avoid_duplicates = True
    s.use_collection_filter = False
    s.collection_source = ""
    s.collection_dest = ""
    s.deform_only = False
    s.owner_space = 'WORLD'
    s.target_space = 'WORLD'
    s.resolve_ambiguous = False
    return s


def levels(findings):
    return [lvl for lvl, _ in findings]


def joined(findings):
    return " | ".join(text for _, text in findings)


print("===== TEST MODULO 4 =====", flush=True)
addon.register()

# ---------------------------------------------------------------------------
print("\n[1] Rig pulito: nessun errore", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig", [("DEF-a", None), ("MCH-a", None)])
    activate(arm, pose=True)
    base_settings()
    findings = addon.diagnose_rig(arm, settings())
    check("nessun errore su rig pulito", 'error' not in levels(findings), joined(findings))
    check("nessun avviso su rig pulito", 'warning' not in levels(findings), joined(findings))
    check("diagnostica non modifica la scena",
          sum(len(pb.constraints) for pb in arm.pose.bones) == 0)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[2] Nessuna coppia -> errore", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig2", [("osso1", None), ("osso2", None)])
    activate(arm, pose=True)
    base_settings()
    findings = addon.diagnose_rig(arm, settings())
    check("nessuna coppia segnalata come errore", 'error' in levels(findings), joined(findings))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[3] Ambigui segnalati", flush=True)
try:
    reset_scene()
    # 'DEF-a' senza side puo' corrispondere sia a 'MCH-a' sia a 'MCH-a.L'
    arm = make_armature("Rig3", [
        ("DEF-a", None), ("MCH-a", None), ("MCH-a.L", None),
    ])
    activate(arm, pose=True)
    base_settings()
    findings = addon.diagnose_rig(arm, settings())
    check("ambiguità segnalata", 'warning' in levels(findings), joined(findings))
    check("il messaggio contiene 'ambigue'", "ambigue" in joined(findings), joined(findings))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[4] Rest orientation diversa -> avviso", flush=True)
try:
    reset_scene()
    # sorgente con roll 0, destinazione ruotata di 60° sull'asse del bone
    src = make_armature("Def", [("DEF-a", None)], roll_offset=0.0)
    dst = make_armature("Mch", [("MCH-a", None)], roll_offset=radians(60.0))
    activate(dst, pose=True)
    s = base_settings()
    s.source_object = src
    findings = addon.diagnose_rig(dst, s)
    check("orientamento di rest diverso segnalato",
          'warning' in levels(findings) and "orientamento" in joined(findings),
          joined(findings))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[5] Driver concorrente sulla destinazione", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig5", [("DEF-a", None), ("MCH-a", None)])
    activate(arm, pose=True)
    pb = arm.pose.bones["MCH-a"]
    pb.driver_add("location", 0)
    base_settings()
    findings = addon.diagnose_rig(arm, settings())
    check("driver sulla destinazione segnalato",
          'warning' in levels(findings) and "driver" in joined(findings),
          joined(findings))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[6] Spazio consigliato", flush=True)
try:
    reset_scene()
    # stessa gerarchia: DEF e MCH sotto lo stesso root
    arm = make_armature("Rig6", [
        ("Root", None), ("DEF-a", "Root"), ("MCH-a", "Root"),
    ])
    activate(arm, pose=True)
    s = base_settings()
    s.owner_space = 'WORLD'
    findings = addon.diagnose_rig(arm, s)
    check("suggerisce LOCAL_WITH_PARENT con gerarchia uguale",
          "LOCAL_WITH_PARENT" in joined(findings), joined(findings))

    # gerarchie diverse
    reset_scene()
    arm2 = make_armature("Rig6b", [
        ("RootA", None), ("RootB", None),
        ("DEF-b", "RootA"), ("MCH-b", "RootB"),
    ])
    activate(arm2, pose=True)
    s = base_settings()
    s.owner_space = 'LOCAL'
    findings2 = addon.diagnose_rig(arm2, s)
    check("suggerisce WORLD con gerarchie diverse",
          "WORLD" in joined(findings2), joined(findings2))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[7] Collection inesistente segnalata", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig7", [("DEF-a", None), ("MCH-a", None)])
    activate(arm, pose=True)
    s = base_settings()
    s.use_collection_filter = True
    s.collection_dest = "NonEsiste"
    findings = addon.diagnose_rig(arm, s)
    check("collection inesistente segnalata",
          "inesistente" in joined(findings), joined(findings))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[8] Operatore actd.diagnose popola le proprieta'", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig8", [("osso1", None), ("osso2", None)])
    activate(arm, pose=True)
    base_settings()
    res = bpy.ops.actd.diagnose()
    check("operatore eseguito", res == {'FINISHED'}, res)
    items = settings().diagnostic_items
    check("items popolati", len(items) > 0, len(items))
    check("diagnostica non piu' stale", settings().diagnostic_is_stale is False)
    check("report testuale scritto", bool(settings().last_report))
    check("livelli validi",
          all(i.level in ('error', 'warning', 'info') for i in items),
          [i.level for i in items])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[9] Diagnostica con armatura sorgente non valida", flush=True)
try:
    reset_scene()
    dst = make_armature("Rig9", [("MCH-a", None)])
    src = make_armature("Src9", [("DEF-a", None)])
    activate(dst, pose=True)
    s = base_settings()
    s.source_object = src
    bpy.ops.object.mode_set(mode='OBJECT')
    activate(src)
    bpy.ops.object.mode_set(mode='EDIT')
    findings = addon.diagnose_rig(dst, s)
    check("sorgente in Edit Mode segnalata come errore",
          'error' in levels(findings), joined(findings))
    bpy.ops.object.mode_set(mode='OBJECT')
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[10] Nessuna armatura -> errore pulito", flush=True)
try:
    findings = addon.diagnose_rig(None, settings())
    check("None gestito senza crash", 'error' in levels(findings), joined(findings))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST MODULO 4 =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)
