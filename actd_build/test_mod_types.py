# -*- coding: utf-8 -*-
"""Test headless dei tipi di constraint (Modulo 2 esteso).

Copre COPY_TRANSFORMS, COPY_ROTATION, COPY_LOCATION, COPY_SCALE:
mix_mode solo dove esiste, use_offset, spazi/influenza, filtro per tipo
nel registro e sostituzione/rimozione dei constraint generati.

Esecuzione:
    blender.exe --background --factory-startup --python test_mod_types.py
"""

import os
import sys
import traceback
from math import degrees, radians

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


def base_settings(constraint_type='COPY_TRANSFORMS'):
    """Riporta le impostazioni alla configurazione di default della 1.1.0."""
    s = settings()
    s.source_object = None
    s.source_token = "DEF-"
    s.dest_token = "MCH-"
    s.source_token_type = 'PREFIX'
    s.dest_token_type = 'PREFIX'
    s.custom_pattern = ""
    s.use_regex = False
    s.apply_mode = 'ALL'
    s.use_collection_filter = False
    s.collection_source = ""
    s.collection_dest = ""
    s.deform_only = False
    s.constraint_type = constraint_type
    s.mix_mode = 'REPLACE'
    s.use_offset = False
    s.remove_target_shear = False
    s.stack_position = 'BOTTOM'
    s.influence = 1.0
    s.target_space = 'WORLD'
    s.owner_space = 'WORLD'
    s.existing_mode = 'KEEP'
    s.update_mode = 'MISSING_ONLY'
    s.avoid_duplicates = True
    s.resolve_ambiguous = False
    s.constraint_name = addon.DEFAULT_CONSTRAINT_NAME
    addon._clear_collection(s.preview_items)
    addon._clear_collection(s.diagnostic_items)
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            addon._write_registry(obj, {})
    return s


def rig(name="Rig"):
    arm = make_armature(name, ["DEF-a", "MCH-a"])
    return arm, arm.pose.bones["MCH-a"]


print("===== TEST TIPI DI CONSTRAINT =====", flush=True)
addon.register()

# ---------------------------------------------------------------------------
print("\n[1] Default: COPY_TRANSFORMS invariato", flush=True)
try:
    reset_scene()
    arm, pb = rig("Rig1")
    s = base_settings()
    res = bpy.ops.actd.apply_transforms()
    con = pb.constraints[0]
    check("apply FINISHED", res == {'FINISHED'}, res)
    check("tipo di default COPY_TRANSFORMS",
          con.type == 'COPY_TRANSFORMS' and addon._constraint_type(s) == 'COPY_TRANSFORMS',
          con.type)
    check("un solo constraint generato", len(pb.constraints) == 1, len(pb.constraints))
    check("Copy Transforms non espone use_offset", not hasattr(con, "use_offset"))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[2] COPY_ROTATION: copia solo la rotazione", flush=True)
try:
    reset_scene()
    arm, pb = rig("Rig2")
    s = base_settings('COPY_ROTATION')
    bpy.ops.actd.apply_transforms()
    con = pb.constraints[0]
    check("constraint creato è Copy Rotation", con.type == 'COPY_ROTATION', con.type)
    check("constraint marcato nel registro",
          addon._is_generated(arm, pb, con) is True)
    check("mix REPLACE di default", con.mix_mode == 'REPLACE', con.mix_mode)

    src = arm.pose.bones["DEF-a"]
    rest_pos = pb.matrix.translation.copy()
    src.rotation_mode = 'XYZ'
    src.rotation_euler = (radians(35.0), radians(10.0), radians(5.0))
    bpy.context.view_layer.update()
    delta = degrees(abs(src.matrix.to_quaternion().rotation_difference(
        pb.matrix.to_quaternion()).angle))
    check("la rotazione viene copiata", delta < 1.0, delta)
    check("la posizione non viene copiata",
          (pb.matrix.translation - rest_pos).length < 1e-4,
          (pb.matrix.translation - rest_pos).length)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[3] mix_mode solo sui tipi che lo espongono", flush=True)
try:
    reset_scene()
    arm, pb = rig("Rig3")
    s = base_settings('COPY_ROTATION')
    s.mix_mode = 'BEFORE_SPLIT'
    bpy.ops.actd.apply_transforms()
    con = pb.constraints[0]
    check("Copy Rotation: BEFORE_SPLIT degradato a BEFORE",
          con.mix_mode == 'BEFORE', con.mix_mode)
    check("Copy Rotation: avviso di fallback nel report",
          "non disponibile" in s.last_report and "BEFORE" in s.last_report,
          s.last_report.replace("\n", " / "))

    reset_scene()
    arm, pb = rig("Rig3b")
    s = base_settings('COPY_LOCATION')
    s.mix_mode = 'BEFORE'
    bpy.ops.actd.apply_transforms()
    con = pb.constraints[0]
    check("Copy Location: mix_mode assente", not hasattr(con, "mix_mode"))
    check("Copy Location: avviso 'non supporta Mix'",
          "non supporta 'Mix'" in s.last_report,
          s.last_report.replace("\n", " / "))

    reset_scene()
    arm, pb = rig("Rig3c")
    s = base_settings('COPY_SCALE')
    s.mix_mode = 'AFTER'
    bpy.ops.actd.apply_transforms()
    con = pb.constraints[0]
    check("Copy Scale: mix_mode assente", not hasattr(con, "mix_mode"))
    check("Copy Scale: avviso 'non supporta Mix'",
          "non supporta 'Mix'" in s.last_report,
          s.last_report.replace("\n", " / "))

    reset_scene()
    arm, pb = rig("Rig3d")
    s = base_settings('COPY_TRANSFORMS')
    s.mix_mode = 'BEFORE_FULL'
    bpy.ops.actd.apply_transforms()
    check("Copy Transforms: BEFORE_FULL applicato",
          pb.constraints[0].mix_mode == 'BEFORE_FULL',
          pb.constraints[0].mix_mode)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[4] use_offset su Location/Scale/Rotation", flush=True)
try:
    reset_scene()
    arm, pb = rig("Rig4a")
    s = base_settings('COPY_LOCATION')
    s.use_offset = True
    bpy.ops.actd.apply_transforms()
    con = pb.constraints[0]
    check("Copy Location: use_offset applicato", con.use_offset is True)

    s.update_mode = 'UPDATE'
    s.use_offset = False
    bpy.ops.actd.apply_transforms()
    check("Copy Location: UPDATE riporta use_offset a False",
          len(pb.constraints) == 1 and pb.constraints[0].use_offset is False,
          pb.constraints[0].use_offset)

    reset_scene()
    arm, pb = rig("Rig4b")
    s = base_settings('COPY_SCALE')
    s.use_offset = True
    bpy.ops.actd.apply_transforms()
    check("Copy Scale: use_offset applicato",
          pb.constraints[0].use_offset is True)

    reset_scene()
    arm, pb = rig("Rig4c")
    s = base_settings('COPY_ROTATION')
    s.use_offset = True
    bpy.ops.actd.apply_transforms()
    con = pb.constraints[0]
    check("Copy Rotation: use_offset ignorato (dipende dal mix)",
          con.mix_mode == 'REPLACE', con.mix_mode)
    check("Copy Rotation: avviso use_offset/mix nel report",
          "'Usa offset' dipende da Mix" in s.last_report,
          s.last_report.replace("\n", " / "))

    reset_scene()
    arm, pb = rig("Rig4d")
    s = base_settings('COPY_TRANSFORMS')
    s.use_offset = True
    bpy.ops.actd.apply_transforms()
    con = pb.constraints[0]
    check("Copy Transforms: use_offset ignorato senza errore",
          not hasattr(con, "use_offset"), con.type)
    check("Copy Transforms: avviso use_offset nel report",
          "'Usa offset' non esiste" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[5] Spazi e influenza comuni a tutti i tipi", flush=True)
try:
    for con_type in ('COPY_ROTATION', 'COPY_LOCATION', 'COPY_SCALE'):
        reset_scene()
        arm, pb = rig("Rig5_" + con_type)
        s = base_settings(con_type)
        s.influence = 0.35
        s.target_space = 'POSE'
        s.owner_space = 'LOCAL'
        bpy.ops.actd.apply_transforms()
        con = pb.constraints[0]
        check(con_type + ": tipo corretto", con.type == con_type, con.type)
        check(con_type + ": influenza 0.35",
              abs(con.influence - 0.35) < 1e-5, con.influence)
        check(con_type + ": spazi POSE/LOCAL",
              con.target_space == 'POSE' and con.owner_space == 'LOCAL',
              (con.target_space, con.owner_space))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[6] _find_all_generated con filtro con_type", flush=True)
try:
    reset_scene()
    arm, pb = rig("Rig6")
    base_settings()

    manual = pb.constraints.new('COPY_ROTATION')
    manual.name = "MANUALE"

    gen_ct = pb.constraints.new('COPY_TRANSFORMS')
    gen_ct.name = "GEN_CT"
    addon._mark_generated(arm, pb, gen_ct, arm, "DEF-a")
    gen_cl = pb.constraints.new('COPY_LOCATION')
    gen_cl.name = "GEN_CL"
    addon._mark_generated(arm, pb, gen_cl, arm, "DEF-a")

    tutti = addon._find_all_generated(arm, pb)
    check("senza filtro: solo i due generati",
          sorted(c.name for c in tutti) == ["GEN_CL", "GEN_CT"],
          [c.name for c in tutti])
    check("filtro COPY_TRANSFORMS: un solo risultato",
          [c.name for c in addon._find_all_generated(
              arm, pb, 'COPY_TRANSFORMS')] == ["GEN_CT"])
    check("filtro COPY_ROTATION: nessun generato (il manuale è escluso)",
          addon._find_all_generated(arm, pb, 'COPY_ROTATION') == [])
    primo = addon._find_generated_constraint(arm, pb, 'COPY_LOCATION')
    check("_find_generated_constraint per tipo",
          primo is not None and primo.name == "GEN_CL",
          primo.name if primo is not None else None)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[7] Cambio tipo con KEEP: il vecchio generato viene sostituito", flush=True)
try:
    reset_scene()
    arm, pb = rig("Rig7")
    s = base_settings('COPY_TRANSFORMS')
    bpy.ops.actd.apply_transforms()
    check("partenza Copy Transforms",
          len(pb.constraints) == 1 and pb.constraints[0].type == 'COPY_TRANSFORMS')

    s.constraint_type = 'COPY_ROTATION'
    bpy.ops.actd.apply_transforms()
    check("dopo il cambio resta un solo constraint",
          len(pb.constraints) == 1, [c.type for c in pb.constraints])
    check("il constraint è Copy Rotation",
          pb.constraints[0].type == 'COPY_ROTATION', pb.constraints[0].type)
    check("avviso di sostituzione per tipo nel report",
          "tipo diverso" in s.last_report,
          s.last_report.replace("\n", " / "))
    reg = addon._read_registry(arm)
    voci = reg.get("MCH-a", {})
    check("registro aggiornato: una sola voce",
          len(voci) == 1 and pb.constraints[0].name in voci, voci)

    s.constraint_type = 'COPY_TRANSFORMS'
    bpy.ops.actd.apply_transforms()
    check("round-trip: torna Copy Transforms",
          len(pb.constraints) == 1
          and pb.constraints[0].type == 'COPY_TRANSFORMS',
          [c.type for c in pb.constraints])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[8] remove_generated: rimuove i generati, risparmia i manuali", flush=True)
try:
    reset_scene()
    arm, pb = rig("Rig8")
    s = base_settings('COPY_TRANSFORMS')
    bpy.ops.actd.apply_transforms()

    gen_cl = pb.constraints.new('COPY_LOCATION')
    gen_cl.name = "GEN_CL"
    addon._mark_generated(arm, pb, gen_cl, arm, "DEF-a")

    manual = pb.constraints.new('COPY_SCALE')
    manual.name = "MANUALE"

    res = bpy.ops.actd.remove_generated()
    nomi = [c.name for c in pb.constraints]
    check("remove_generated FINISHED", res == {'FINISHED'}, res)
    check("rimosso solo il generato Copy Transforms",
          nomi == ["GEN_CL", "MANUALE"], nomi)
    check("registro conserva il generato di altro tipo",
          "GEN_CL" in addon._read_registry(arm).get("MCH-a", {}),
          addon._read_registry(arm))
    check("report con 1 constraint rimosso",
          "Constraint rimossi: 1" in s.last_report,
          s.last_report.replace("\n", " / "))

    s.constraint_type = 'COPY_LOCATION'
    res = bpy.ops.actd.remove_generated()
    nomi = [c.name for c in pb.constraints]
    check("secondo passaggio: rimosso il generato Copy Location",
          nomi == ["MANUALE"], nomi)
    check("registro vuoto dopo la rimozione",
          addon._read_registry(arm) == {}, addon._read_registry(arm))
    check("report del secondo passaggio",
          "Constraint rimossi: 1" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST TIPI =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)
