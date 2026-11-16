# -*- coding: utf-8 -*-
"""Test headless: KEEP con tipi misti sullo stesso osso.

Scenario: in modalita' KEEP, su un osso si crea prima un Copy Location generato
e poi un Copy Rotation generato verso lo stesso sorgente. Entrambi i constraint
devono restare sull'osso.

Esecuzione:
    blender.exe --background --factory-startup --python test_keep_mixed_types.py
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
    s.constraint_type = 'COPY_TRANSFORMS'
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
    s.mute_state = False
    s.last_report = ""
    s.preview_report = ""
    s.diagnostic_report = ""
    s.maintenance_report = ""
    addon._clear_collection(s.preview_items)
    addon._clear_collection(s.diagnostic_items)
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            addon._write_registry(obj, {})
    return s


print("===== TEST KEEP MIXED TYPES =====", flush=True)
addon.register()
check("mute_state default False", settings().mute_state is False)

try:
    reset_scene()
    arm = make_armature("RigKeep", ["DEF-a", "MCH-a"])
    s = base_settings()

    # Primo passo: Copy Location generato.
    s.constraint_type = 'COPY_LOCATION'
    res1 = bpy.ops.actd.apply_transforms()
    check("primo apply FINISHED", res1 == {'FINISHED'}, res1)
    pba = arm.pose.bones["MCH-a"]
    check("dopo il primo passo un COPY_LOCATION generato",
          any(c.type == 'COPY_LOCATION' and addon._is_generated(arm, pba, c)
              for c in pba.constraints),
          [(c.name, c.type) for c in pba.constraints])

    # Secondo passo: Copy Rotation generato, stesso sorgente.
    s.constraint_type = 'COPY_ROTATION'
    res2 = bpy.ops.actd.apply_transforms()
    check("secondo apply FINISHED", res2 == {'FINISHED'}, res2)

    types = [c.type for c in pba.constraints]
    check("entrambi i constraint restano sull'osso",
          'COPY_LOCATION' in types and 'COPY_ROTATION' in types,
          types)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# Caso 2: KEEP a 3 tipi (COPY_LOCATION, COPY_ROTATION, COPY_SCALE) sullo
# stesso osso e stessa sorgente: tutti e 3 restano, senza doppi.
try:
    reset_scene()
    arm = make_armature("RigKeep3", ["DEF-a", "MCH-a"])
    s = base_settings()
    for ctype in ('COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE'):
        s.constraint_type = ctype
        res = bpy.ops.actd.apply_transforms()
        check("apply %s FINISHED" % ctype, res == {'FINISHED'}, res)
    pba = arm.pose.bones["MCH-a"]
    for ctype in ('COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE'):
        cnt = sum(1 for c in pba.constraints if c.type == ctype)
        check("dopo 3 tipi un solo %s" % ctype, cnt == 1, cnt)
    gens = [c for c in pba.constraints if addon._is_generated(arm, pba, c)]
    check("tutti e 3 i constraint sono generati", len(gens) == 3, len(gens))
    check("nessun duplicato tra i 3 tipi", len(pba.constraints) == 3, len(pba.constraints))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE (caso 3 tipi): " + traceback.format_exc().strip().splitlines()[-1])

# Caso 3: KEEP con avoid_duplicates attivo: ricreando gli stessi 3 tipi il
# conteggio per tipo non raddoppia.
try:
    reset_scene()
    arm = make_armature("RigKeepDup", ["DEF-a", "MCH-a"])
    s = base_settings()
    s.avoid_duplicates = True
    for ctype in ('COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE'):
        s.constraint_type = ctype
        bpy.ops.actd.apply_transforms()
    pba = arm.pose.bones["MCH-a"]
    before = {ct: sum(1 for c in pba.constraints if c.type == ct)
              for ct in ('COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE')}
    for ctype in ('COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE'):
        s.constraint_type = ctype
        res = bpy.ops.actd.apply_transforms()
        check("ri-apply %s FINISHED" % ctype, res == {'FINISHED'}, res)
    after = {ct: sum(1 for c in pba.constraints if c.type == ct)
             for ct in ('COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE')}
    for ctype in ('COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE'):
        check("conteggio %s non raddoppia" % ctype,
              after[ctype] == before[ctype] == 1, (before[ctype], after[ctype]))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE (caso avoid_duplicates): " + traceback.format_exc().strip().splitlines()[-1])

# Caso 4: REPLACE ("Sostituisci") - constraint generato con nome esatto nel
# registro viene sostituito: resta un solo constraint di quel tipo.
try:
    reset_scene()
    arm = make_armature("RigReplaceGen", ["DEF-a", "MCH-a"])
    s = base_settings()
    s.existing_mode = 'REPLACE'
    res0 = bpy.ops.actd.apply_transforms()
    check("caso REPLACE gen: primo apply FINISHED", res0 == {'FINISHED'}, res0)
    pba = arm.pose.bones["MCH-a"]
    res1 = bpy.ops.actd.apply_transforms()
    check("caso REPLACE gen: secondo apply FINISHED", res1 == {'FINISHED'}, res1)
    cnt = sum(1 for c in pba.constraints if c.type == 'COPY_TRANSFORMS')
    check("caso REPLACE gen: un solo constraint finale del tipo",
          cnt == 1, cnt)
    check("caso REPLACE gen: constraint generato",
          len(pba.constraints) == 1
          and addon._is_generated(arm, pba, pba.constraints[0]) is True,
          [c.name for c in pba.constraints])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE (caso REPLACE gen): " + traceback.format_exc().strip().splitlines()[-1])

# Caso 5: REPLACE ("Sostituisci") - constraint manuale con nome con
# prefisso/suffisso diverso NON viene rimosso.
try:
    reset_scene()
    arm = make_armature("RigReplaceMan", ["DEF-a", "MCH-a"])
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    pba = arm.pose.bones["MCH-a"]
    gen = pba.constraints[0]
    old_name = gen.name
    gen.name = "PRE_" + old_name
    addon._forget_generated(arm, pba, old_name)
    s.existing_mode = 'REPLACE'
    res = bpy.ops.actd.apply_transforms(replace_scelta='GENERATED_ONLY')
    check("caso REPLACE man: apply FINISHED", res == {'FINISHED'}, res)
    check("caso REPLACE man: il manuale con nome diverso resta",
          any(c.name == "PRE_" + old_name for c in pba.constraints),
          [c.name for c in pba.constraints])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE (caso REPLACE man): " + traceback.format_exc().strip().splitlines()[-1])

print("\nPassati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
print("RISULTATO passati=%d falliti=%d totale=%d" % (
    len(OK), len(FAIL), len(OK) + len(FAIL)), flush=True)
print("RISULTATO: " + ("FALLITO" if FAIL else "SUPERATO"), flush=True)
if FAIL:
    print("FALLIMENTI:", flush=True)
    for f in FAIL:
        print("  - " + f, flush=True)
addon.unregister()
