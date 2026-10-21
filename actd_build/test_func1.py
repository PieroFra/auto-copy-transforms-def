# -*- coding: utf-8 -*-
"""Verifica funzionale: il constraint copia davvero i valori dalla sorgente."""

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


print("===== TEST FUNZIONALE MODULO 1 =====", flush=True)
addon.register()

try:
    # armatura sorgente ruotata di 90 su Z rispetto al mondo
    src = make_armature("Def", ["DEF-hand"])
    src.rotation_euler = Euler((0.0, 0.0, radians(90.0)))
    dst = make_armature("Mch", ["MCH-hand"])

    activate(dst, pose=True)
    s = bpy.context.scene.actd_settings
    s.source_token = "DEF-"
    s.dest_token = "MCH-"
    s.source_object = src
    s.owner_space = 'WORLD'
    s.target_space = 'WORLD'
    bpy.ops.actd.apply_transforms()

    # muovo l'osso sorgente in pose
    activate(src, pose=True)
    pb_src = src.pose.bones["DEF-hand"]
    pb_src.location = (1.0, 0.0, 0.0)
    pb_src.rotation_euler = Euler((0.0, 0.0, radians(45.0)))
    bpy.context.view_layer.update()

    activate(dst, pose=True)
    bpy.context.view_layer.update()

    pb_dst = dst.pose.bones["MCH-hand"]
    # Confronto in spazio MONDO: le due armature hanno transform oggetto diverse
    w_dst = dst.matrix_world @ pb_dst.matrix
    w_src = src.matrix_world @ pb_src.matrix
    mats_equal = all(
        abs(w_dst[i][j] - w_src[i][j]) < 1e-5
        for i in range(4) for j in range(4)
    )
    check("la destinazione segue la sorgente in spazio mondo", mats_equal,
          (list(map(list, w_dst)), list(map(list, w_src))))

    # dipendenza reale dal constraint, non da coincidenza: nascondo il constraint
    con = pb_dst.constraints[0]
    check("il constraint punta all'armatura sorgente", con.target == src,
          con.target.name if con.target else None)

    con.mute = True
    bpy.context.view_layer.update()
    diff = any(
        abs((dst.matrix_world @ pb_dst.matrix)[i][j] - w_src[i][j]) > 1e-4
        for i in range(4) for j in range(4)
    )
    check("con constraint muto la destinazione NON segue (prova della dipendenza)", diff)
    con.mute = False
    bpy.context.view_layer.update()

    # la sorgente non e' stata modificata dall'addon
    check("sorgente senza constraint aggiunti",
          len(src.pose.bones["DEF-hand"].constraints) == 0)
    check("sorgente alla rotazione originaria",
          abs(src.rotation_euler.z - radians(90.0)) < 1e-5,
          src.rotation_euler.z)

except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

print("\n===== RIEPILOGO =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)
