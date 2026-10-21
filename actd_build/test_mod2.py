# -*- coding: utf-8 -*-
"""Test headless del Modulo 2: mix_mode, remove_target_shear, ordine nello stack."""

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


def make_armature(name, bone_names):
    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(obj)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for bn in bone_names:
        eb = arm.edit_bones.new(bn)
        eb.head = (0.0, 0.0, 0.0)
        eb.tail = (0.0, 1.0, 0.0)
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
    s.mix_mode = 'REPLACE'
    s.use_offset = False
    s.remove_target_shear = False
    s.stack_position = 'BOTTOM'
    s.owner_space = 'WORLD'
    s.target_space = 'WORLD'
    s.influence = 1.0
    return s


print("===== TEST MODULO 2 =====", flush=True)
addon.register()

# ---------------------------------------------------------------------------
print("\n[1] Default: nessun cambiamento rispetto alla 1.0.x", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    base_settings()
    bpy.ops.actd.apply_transforms()
    con = arm.pose.bones["MCH-a"].constraints[0]
    check("mix_mode default = REPLACE", con.mix_mode == 'REPLACE', con.mix_mode)
    check("remove_target_shear default = False", con.remove_target_shear is False)
    check("constraint unico nello stack (index 0)",
          arm.pose.bones["MCH-a"].constraints.find(con.name) == 0)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[2] mix_mode viene applicato", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig2", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    s = base_settings()
    s.mix_mode = 'AFTER'
    bpy.ops.actd.apply_transforms()
    con = arm.pose.bones["MCH-a"].constraints[0]
    check("mix_mode = AFTER applicato", con.mix_mode == 'AFTER', con.mix_mode)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[3] mix_mode cambia davvero il risultato", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig3", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    s = base_settings()
    s.mix_mode = 'REPLACE'
    bpy.ops.actd.apply_transforms()
    pb = arm.pose.bones["MCH-a"]
    con = pb.constraints[0]

    # rotazione manuale reale sull'osso destinazione: con REPLACE viene
    # ignorata, con AFTER si combina con il risultato del constraint.
    pb.rotation_quaternion = Euler((0.0, 0.0, radians(30.0))).to_quaternion()
    bpy.context.view_layer.update()
    rep_matrix = [list(r) for r in pb.matrix]

    con.mix_mode = 'AFTER'
    arm.update_tag()
    bpy.context.view_layer.update()
    after_matrix = [list(r) for r in pb.matrix]
    changed = any(
        abs(rep_matrix[i][j] - after_matrix[i][j]) > 1e-5
        for i in range(4) for j in range(4)
    )
    check("AFTER produce un risultato diverso da REPLACE", changed)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[4] remove_target_shear", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig4", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    s = base_settings()
    s.remove_target_shear = True
    bpy.ops.actd.apply_transforms()
    con = arm.pose.bones["MCH-a"].constraints[0]
    check("remove_target_shear = True applicato", con.remove_target_shear is True)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[5] Posizione nello stack: TOP", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig5", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    pb = arm.pose.bones["MCH-a"]
    # constraint manuale preesistente
    manual = pb.constraints.new('COPY_ROTATION')
    manual.name = "Manuale"

    s = base_settings()
    s.stack_position = 'TOP'
    bpy.ops.actd.apply_transforms()
    order = [c.name for c in pb.constraints]
    gen_name = [n for n in order if n != "Manuale"][0]
    check("generato in cima allo stack", order[0] == gen_name, order)
    check("il manuale resta nello stack", "Manuale" in order, order)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[6] Posizione nello stack: BEFORE_IK", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig6", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    pb = arm.pose.bones["MCH-a"]
    first = pb.constraints.new('COPY_LOCATION')
    first.name = "Primo"
    ik = pb.constraints.new('IK')
    ik.name = "IK"
    last = pb.constraints.new('COPY_SCALE')
    last.name = "Ultimo"

    s = base_settings()
    s.stack_position = 'BEFORE_IK'
    bpy.ops.actd.apply_transforms()
    order = [c.name for c in pb.constraints]
    gen_name = [n for n in order if n not in ("Primo", "IK", "Ultimo")][0]
    check("generato subito prima dell'IK",
          order.index(gen_name) == order.index("IK") - 1, order)
    check("l'IK resta dopo il generato", order.index("IK") > order.index(gen_name), order)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[7] BEFORE_IK senza IK: nessuno spostamento", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig7", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    pb = arm.pose.bones["MCH-a"]
    other = pb.constraints.new('COPY_LOCATION')
    other.name = "Altro"

    s = base_settings()
    s.stack_position = 'BEFORE_IK'
    bpy.ops.actd.apply_transforms()
    order = [c.name for c in pb.constraints]
    gen_name = [n for n in order if n != "Altro"][0]
    check("senza IK il generato resta in fondo", order[-1] == gen_name, order)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[8] BOTTOM: comportamento classico", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig8", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    pb = arm.pose.bones["MCH-a"]
    other = pb.constraints.new('COPY_LOCATION')
    other.name = "Altro"

    s = base_settings()
    s.stack_position = 'BOTTOM'
    bpy.ops.actd.apply_transforms()
    order = [c.name for c in pb.constraints]
    gen_name = [n for n in order if n != "Altro"][0]
    check("generato in fondo allo stack", order[-1] == gen_name, order)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[9] UPDATE propaga mix/shear ai constraint esistenti", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig9", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    con = arm.pose.bones["MCH-a"].constraints[0]
    check("partenza REPLACE", con.mix_mode == 'REPLACE', con.mix_mode)

    s.mix_mode = 'BEFORE'
    s.remove_target_shear = True
    s.update_mode = 'UPDATE'
    bpy.ops.actd.apply_transforms()
    n = len(arm.pose.bones["MCH-a"].constraints)
    check("UPDATE non crea duplicati", n == 1, n)
    check("UPDATE applica il nuovo mix", con.mix_mode == 'BEFORE', con.mix_mode)
    check("UPDATE applica remove_target_shear", con.remove_target_shear is True)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[10] Constraint manuale con mix diverso non viene confuso", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig10", ["DEF-a", "MCH-a"])
    activate(arm, pose=True)
    pb = arm.pose.bones["MCH-a"]
    manual = pb.constraints.new('COPY_TRANSFORMS')
    manual.name = "Manuale"
    manual.target = arm
    manual.subtarget = "DEF-a"
    manual.owner_space = 'WORLD'
    manual.target_space = 'WORLD'
    manual.influence = 1.0
    manual.mix_mode = 'AFTER'

    s = base_settings()
    s.mix_mode = 'REPLACE'
    s.update_mode = 'UPDATE'
    bpy.ops.actd.apply_transforms()
    names = [c.name for c in pb.constraints]
    check("constraint manuale con mix diverso non trattato come equivalente",
          len(names) == 2, names)
    check("il manuale non viene toccato",
          pb.constraints["Manuale"].mix_mode == 'AFTER')
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST MODULO 2 =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)
