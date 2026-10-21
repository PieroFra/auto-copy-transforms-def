# -*- coding: utf-8 -*-
"""Test headless del Modulo 5: impara il pattern da un constraint esistente.

Esecuzione:
    blender.exe --background --factory-startup --python test_mod_learn.py
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


def base_settings():
    s = settings()
    s.source_object = None
    s.source_token = "ZZZ-"
    s.dest_token = "YYY-"
    s.source_token_type = 'PREFIX'
    s.dest_token_type = 'PREFIX'
    s.custom_pattern = ""
    s.use_regex = False
    s.constraint_type = 'COPY_TRANSFORMS'
    s.mix_mode = 'REPLACE'
    s.use_offset = False
    s.remove_target_shear = False
    s.influence = 1.0
    s.target_space = 'WORLD'
    s.owner_space = 'WORLD'
    s.last_report = ""
    s.preview_is_stale = False
    return s


def select_only(arm, names):
    for pb in arm.pose.bones:
        pb.select = False
    for name in names:
        arm.pose.bones[name].select = True
    bpy.context.view_layer.update()


def add_manual(arm, owner, source, con_type='COPY_TRANSFORMS', **props):
    pb = arm.pose.bones[owner]
    con = pb.constraints.new(con_type)
    con.target = arm
    con.subtarget = source
    for key, value in props.items():
        setattr(con, key, value)
    pb.constraints.active = con
    return pb, con


print("===== TEST IMPARA PATTERN =====", flush=True)
addon.register()

# ---------------------------------------------------------------------------
print("\n[1] Inferenza dei token", flush=True)
try:
    casi = [
        (("MCH-Hand.L", "DEF-Hand.L"),
         ("DEF-", "MCH-", 'PREFIX', 'PREFIX')),
        (("Hand_MCH", "Hand_DEF"),
         ("_DEF", "_MCH", 'SUFFIX', 'SUFFIX')),
        (("MCHHand", "DEFHand"),
         ("DEF", "MCH", 'PREFIX', 'PREFIX')),
    ]
    for (owner, source), atteso in casi:
        trovato = addon._infer_token_rule(owner, source)
        check("token da %s / %s" % (owner, source), trovato == atteso, trovato)

    check("nomi identici: nessun token",
          addon._infer_token_rule("Hand", "Hand") is None)
    check("solo lati L/R: nessun token",
          addon._infer_token_rule("Hand.L", "Hand.R") is None)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[2] Apprende tipo, spazi, influenza, mix e token", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig2", ["DEF-Hand.L", "MCH-Hand.L"])
    s = base_settings()
    pb, con = add_manual(
        arm, "MCH-Hand.L", "DEF-Hand.L", 'COPY_ROTATION',
        influence=0.42, target_space='LOCAL', owner_space='LOCAL',
        mix_mode='BEFORE',
    )
    select_only(arm, ["MCH-Hand.L"])
    res = bpy.ops.actd.learn_pattern()
    check("operatore FINISHED", res == {'FINISHED'}, res)
    check("tipo Copy Rotation appreso",
          s.constraint_type == 'COPY_ROTATION', s.constraint_type)
    check("influenza appresa", abs(s.influence - 0.42) < 1e-5, s.influence)
    check("spazi appresi",
          s.target_space == 'LOCAL' and s.owner_space == 'LOCAL',
          (s.target_space, s.owner_space))
    check("mix appreso", s.mix_mode == 'BEFORE', s.mix_mode)
    check("token sorgente DEF-", s.source_token == "DEF-", s.source_token)
    check("token destinazione MCH-", s.dest_token == "MCH-", s.dest_token)
    check("tipo token PREFIX",
          s.source_token_type == 'PREFIX' and s.dest_token_type == 'PREFIX',
          (s.source_token_type, s.dest_token_type))
    check("armatura sorgente appresa", s.source_object == arm, s.source_object)
    check("report con i token appresi", "Token:" in s.last_report,
          s.last_report.replace("\n", " / "))
    check("anteprima marcata stale", s.preview_is_stale is True)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[3] Token di suffisso e use_offset", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig3", ["Hand_DEF", "Hand_MCH"])
    s = base_settings()
    add_manual(
        arm, "Hand_MCH", "Hand_DEF", 'COPY_LOCATION',
        influence=0.7, target_space='POSE', owner_space='WORLD',
        use_offset=True,
    )
    select_only(arm, ["Hand_MCH"])
    bpy.ops.actd.learn_pattern()
    check("tipo Copy Location appreso",
          s.constraint_type == 'COPY_LOCATION', s.constraint_type)
    check("token suffisso sorgente _DEF", s.source_token == "_DEF",
          s.source_token)
    check("token suffisso destinazione _MCH", s.dest_token == "_MCH",
          s.dest_token)
    check("tipo token SUFFIX",
          s.source_token_type == 'SUFFIX' and s.dest_token_type == 'SUFFIX',
          (s.source_token_type, s.dest_token_type))
    check("use_offset appreso", s.use_offset is True)
    check("influenza 0.7", abs(s.influence - 0.7) < 1e-5, s.influence)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[4] Token camelCase e opzioni Copy Transforms", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig4", ["DEFHand", "MCHHand"])
    s = base_settings()
    add_manual(
        arm, "MCHHand", "DEFHand", 'COPY_TRANSFORMS',
        influence=0.9, target_space='LOCAL_WITH_PARENT', owner_space='POSE',
        mix_mode='BEFORE_FULL', remove_target_shear=True,
    )
    select_only(arm, ["MCHHand"])
    bpy.ops.actd.learn_pattern()
    check("token camelCase DEF", s.source_token == "DEF", s.source_token)
    check("token camelCase MCH", s.dest_token == "MCH", s.dest_token)
    check("mix BEFORE_FULL appreso", s.mix_mode == 'BEFORE_FULL', s.mix_mode)
    check("remove_target_shear appreso",
          s.remove_target_shear is True, s.remove_target_shear)
    check("spazi appresi",
          s.target_space == 'LOCAL_WITH_PARENT' and s.owner_space == 'POSE',
          (s.target_space, s.owner_space))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[5] Nessun token deducibile: campi invariati", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig5", ["Solo"])
    s = base_settings()
    add_manual(arm, "Solo", "Solo", 'COPY_TRANSFORMS', influence=0.6)
    select_only(arm, ["Solo"])
    res = bpy.ops.actd.learn_pattern()
    check("operatore FINISHED", res == {'FINISHED'}, res)
    check("token invariati",
          s.source_token == "ZZZ-" and s.dest_token == "YYY-",
          (s.source_token, s.dest_token))
    check("influenza comunque appresa",
          abs(s.influence - 0.6) < 1e-5, s.influence)
    check("report segnala token non deducibili",
          "non deducibili" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[6] Più constraint: vince la maggioranza", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig6", [
        "DEF-A", "DEF-B", "DEF-C", "MCH-A", "MCH-B", "MCH-C",
        "ORG-Alt", "MCH-Alt",
    ])
    s = base_settings()
    for owner, source in (
        ("MCH-A", "DEF-A"),
        ("MCH-B", "DEF-B"),
        ("MCH-C", "DEF-C"),
        ("MCH-Alt", "ORG-Alt"),
    ):
        add_manual(arm, owner, source, 'COPY_TRANSFORMS', influence=0.5)
    select_only(arm, ["MCH-A", "MCH-B", "MCH-C", "MCH-Alt"])
    bpy.ops.actd.learn_pattern()
    check("maggioranza DEF-/MCH-",
          s.source_token == "DEF-" and s.dest_token == "MCH-",
          (s.source_token, s.dest_token))
    check("report con i token appresi", "Token:" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[7] Più constraint senza maggioranza", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig7", [
        "DEF-A", "MCH-A", "ORG-Alt", "MCH-Alt",
    ])
    s = base_settings()
    add_manual(arm, "MCH-A", "DEF-A", 'COPY_TRANSFORMS')
    add_manual(arm, "MCH-Alt", "ORG-Alt", 'COPY_TRANSFORMS')
    select_only(arm, ["MCH-A", "MCH-Alt"])
    bpy.ops.actd.learn_pattern()
    check("token invariati per assenza di maggioranza",
          s.source_token == "ZZZ-" and s.dest_token == "YYY-",
          (s.source_token, s.dest_token))
    check("report segnala assenza di maggioranza",
          "non deducibili" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[8] Poll e registrazione", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig8", ["DEF-A", "MCH-A"])
    base_settings()
    select_only(arm, [])
    check("poll falso senza selezione",
          addon.ACTD_OT_learn_pattern.poll(bpy.context) is False)
    select_only(arm, ["MCH-A"])
    check("poll falso senza constraint",
          addon.ACTD_OT_learn_pattern.poll(bpy.context) is False)
    add_manual(arm, "MCH-A", "DEF-A", 'COPY_TRANSFORMS')
    select_only(arm, ["MCH-A"])
    check("poll vero con constraint di copia",
          addon.ACTD_OT_learn_pattern.poll(bpy.context) is True)
    check("actd.learn_pattern disponibile",
          hasattr(bpy.ops.actd, "learn_pattern"))
    check("classe presente nella registrazione",
          addon.ACTD_OT_learn_pattern in addon._classes)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST IMPARA PATTERN =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)
