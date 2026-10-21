# -*- coding: utf-8 -*-
"""Test headless del Modulo 3: filtro per bone collection e solo-deform."""

import os
import sys
import traceback

import bpy

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


def make_armature(name, bone_specs):
    """bone_specs: lista di (nome, use_deform)."""
    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(obj)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for bn, _deform in bone_specs:
        eb = arm.edit_bones.new(bn)
        eb.head = (0.0, 0.0, 0.0)
        eb.tail = (0.0, 1.0, 0.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    for bn, deform in bone_specs:
        arm.bones[bn].use_deform = deform
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
    return s


def make_collection(arm, name, bone_names):
    coll = arm.data.collections.new(name)
    for bn in bone_names:
        coll.assign(arm.data.bones[bn])
    return coll


print("===== TEST MODULO 3 =====", flush=True)
addon.register()

BONES = [
    ("DEF-hand.L", True), ("MCH-hand.L", True),
    ("DEF-hand.R", True), ("MCH-hand.R", True),
    ("DEF-neck", True), ("MCH-neck", True),
]

# ---------------------------------------------------------------------------
print("\n[1] Filtro disattivato: tutto mappato (default invariato)", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig", BONES)
    activate(arm, pose=True)
    base_settings()
    bpy.ops.actd.apply_transforms()
    n = sum(len(pb.constraints) for pb in arm.pose.bones)
    check("senza filtro crea 3 constraint", n == 3, n)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[2] Filtro su collection destinazione", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig2", BONES)
    make_collection(arm, "Meccaniche", ["MCH-hand.L", "MCH-hand.R"])
    activate(arm, pose=True)
    s = base_settings()
    s.use_collection_filter = True
    s.collection_dest = "Meccaniche"
    bpy.ops.actd.apply_transforms()
    got = sorted(pb.name for pb in arm.pose.bones if pb.constraints)
    check("solo le ossa della collection hanno constraint",
          got == ["MCH-hand.L", "MCH-hand.R"], got)
    check("MCH-neck escluso", "MCH-neck" not in got, got)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[3] Collection inesistente: nessun risultato, nessun errore", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig3", BONES)
    make_collection(arm, "Esiste", ["MCH-neck"])
    activate(arm, pose=True)
    s = base_settings()
    s.use_collection_filter = True
    s.collection_dest = "NonEsiste"
    bpy.ops.actd.apply_transforms()
    n = sum(len(pb.constraints) for pb in arm.pose.bones)
    check("collection inesistente -> nessun constraint", n == 0, n)
    check("l'operatore non manda in crash lo script", True)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[4] Filtro solo-ossa-deform", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig4", [
        ("DEF-hand.L", True), ("MCH-hand.L", True),
        ("DEF-crtl", False), ("MCH-crtl", False),
    ])
    activate(arm, pose=True)
    s = base_settings()
    s.use_collection_filter = True
    s.deform_only = True
    bpy.ops.actd.apply_transforms()
    got = sorted(pb.name for pb in arm.pose.bones if pb.constraints)
    check("solo le ossa deform ricevono il constraint", got == ["MCH-hand.L"], got)
    check("la control bone e' esclusa", "MCH-crtl" not in got, got)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[5] Filtro collection sorgente", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig5", BONES)
    make_collection(arm, "SoloNeck", ["DEF-neck"])
    activate(arm, pose=True)
    s = base_settings()
    s.use_collection_filter = True
    s.collection_source = "SoloNeck"
    bpy.ops.actd.apply_transforms()
    got = sorted(pb.name for pb in arm.pose.bones if pb.constraints)
    check("solo la destinazione della sorgente filtrata", got == ["MCH-neck"], got)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[6] Filtro con armature separate (Modulo 1 + 3)", flush=True)
try:
    reset_scene()
    dst = make_armature("Mch_Rig", [
        ("MCH-hand.L", True), ("MCH-hand.R", True), ("MCH-neck", True),
    ])
    src = make_armature("Def_Rig", [
        ("DEF-hand.L", True), ("DEF-hand.R", True), ("DEF-neck", True),
    ])
    make_collection(src, "ManiDef", ["DEF-hand.L", "DEF-hand.R"])
    activate(dst, pose=True)
    s = base_settings()
    s.source_object = src
    s.use_collection_filter = True
    s.collection_source = "ManiDef"
    bpy.ops.actd.apply_transforms()
    got = sorted(pb.name for pb in dst.pose.bones if pb.constraints)
    check("filtro sorgente su armatura separata", got == ["MCH-hand.L", "MCH-hand.R"], got)
    check("target corretti",
          all(c.target == src for pb in dst.pose.bones for c in pb.constraints))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[7] Anteprima coerente col filtro", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig7", BONES)
    make_collection(arm, "Meccaniche", ["MCH-hand.L", "MCH-hand.R"])
    activate(arm, pose=True)
    s = base_settings()
    s.use_collection_filter = True
    s.collection_dest = "Meccaniche"
    bpy.ops.actd.preview()
    pairs = [item for item in s.preview_items if item.status in ('match', 'resolved')]
    preview = [item.dest_name for item in pairs]
    check("la preview contiene solo le destinazioni filtrate",
          sorted(preview) == ["MCH-hand.L", "MCH-hand.R"], preview)
    check("preview conteggiata", len(pairs) == 2, len(pairs))
    dangling = [i.dest_name for i in s.preview_items if i.status == 'unmatched_dst']
    check("le destinazioni escluse restano visibili come 'senza match'",
          "MCH-neck" in dangling, dangling)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[8] Helper collection robusto", flush=True)
try:
    arm = bpy.data.objects.get("Rig7")
    bone = arm.data.bones["MCH-hand.L"]
    names = addon._bone_collection_names(bone, arm.data)
    check("helper legge la collection dell'osso", "Meccaniche" in names, names)
    check("helper su osso senza collection",
          addon._bone_collection_names(arm.data.bones["MCH-neck"], arm.data) == set(),
          addon._bone_collection_names(arm.data.bones["MCH-neck"], arm.data))
    check("_collection_names elenca le collection",
          addon._collection_names(arm.data) == ["Meccaniche"],
          addon._collection_names(arm.data))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST MODULO 3 =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)
