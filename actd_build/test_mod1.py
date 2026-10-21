# -*- coding: utf-8 -*-
"""Test headless del Modulo 1: armatura sorgente separata dalla destinazione."""

import os
import sys
import traceback

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto_copy_transforms_def as addon  # noqa: E402

OK = []
FAIL = []


def check(name, cond, extra=""):
    if cond:
        OK.append(name)
        print("  OK   " + name, flush=True)
    else:
        FAIL.append(name + ("  [" + str(extra) + "]" if extra else ""))
        print("  FAIL " + name + ("  [" + str(extra) + "]" if extra else ""), flush=True)


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
        eb.tail = (1.0, 0.0, 0.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def settings():
    return bpy.context.scene.actd_settings


def activate(obj, pose=False):
    if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if pose:
        bpy.ops.object.mode_set(mode='POSE')


def apply():
    return bpy.ops.actd.apply_transforms()


def remove():
    return bpy.ops.actd.remove_generated()


def base_settings(src_token="DEF-", dst_token="MCH-"):
    s = settings()
    s.source_token = src_token
    s.dest_token = dst_token
    s.source_object = None
    s.existing_mode = 'KEEP'
    s.update_mode = 'MISSING_ONLY'
    s.avoid_duplicates = True
    return s


print("===== TEST MODULO 1 =====", flush=True)

# ---------------------------------------------------------------------------
print("\n[1] Registrazione", flush=True)
try:
    addon.register()
    check("register() senza errori", True)
    s = settings()
    check("proprieta' source_object esiste", hasattr(s, "source_object"))
    check("default source_object e' None", s.source_object is None, s.source_object)
    check("operatore set_source_object registrato",
          hasattr(bpy.types, "ACTD_OT_set_source_object"))
    check("operatore clean_registry registrato",
          hasattr(bpy.types, "ACTD_OT_clean_registry"))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[2] Default invariato: stessa armatura", flush=True)
try:
    reset_scene()
    arm = make_armature("Rig", ["DEF-hand.L", "DEF-hand.R", "MCH-hand.L", "MCH-hand.R"])
    activate(arm, pose=True)
    base_settings()
    apply()

    allc = [(pb.name, c) for pb in arm.pose.bones for c in pb.constraints]
    check("creati 2 constraint", len(allc) == 2, [n for n, _ in allc])
    check("target = stessa armatura", all(c.target == arm for _, c in allc))
    check("subtarget corretti",
          sorted(c.subtarget for _, c in allc) == ["DEF-hand.L", "DEF-hand.R"],
          [c.subtarget for _, c in allc])
    check("nome auto con token",
          all("AUTO_COPY" in c.name for _, c in allc), [c.name for _, c in allc])

    apply()
    n = sum(len(pb.constraints) for pb in arm.pose.bones)
    check("re-apply non duplica", n == 2, n)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[3] Armatura sorgente separata", flush=True)
try:
    reset_scene()
    dst = make_armature("Rig_Dest", ["MCH-hand.L", "MCH-hand.R", "MCH-neck"])
    src = make_armature("Rig_Def", ["DEF-hand.L", "DEF-hand.R", "DEF-neck", "DEF-extra"])

    activate(dst, pose=True)
    s = base_settings()
    s.source_object = src
    apply()

    pairs = sorted((pb.name, c.subtarget, c.target.name)
                   for pb in dst.pose.bones for c in pb.constraints)
    check("creati 3 constraint", len(pairs) == 3, pairs)
    check("target = armatura sorgente", all(p[2] == "Rig_Def" for p in pairs), pairs)
    check("destinazioni corrette",
          {p[0] for p in pairs} == {"MCH-hand.L", "MCH-hand.R", "MCH-neck"}, pairs)
    check("osso solo-sorgente ignorato", "DEF-extra" not in {p[1] for p in pairs}, pairs)

    reg = addon._read_registry(dst)
    check("registro scritto sulla destinazione", bool(reg), reg)
    check("registro non scritto sulla sorgente", not addon._read_registry(src))
    check("registro contiene l'oggetto sorgente",
          all(e["obj"] == "Rig_Def" for bones in reg.values() for e in bones.values()), reg)

    s.update_mode = 'UPDATE'
    apply()
    n = sum(len(pb.constraints) for pb in dst.pose.bones)
    check("UPDATE non duplica con sorgente separata", n == 3, n)
    check("target ancora corretto",
          all(c.target == src for pb in dst.pose.bones for c in pb.constraints))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[4] Rimozione e svuotamento registro", flush=True)
try:
    activate(dst, pose=True)
    remove()
    n = sum(len(pb.constraints) for pb in dst.pose.bones)
    check("remove() ha rimosso i constraint", n == 0, n)
    check("registro svuotato", not addon._read_registry(dst), addon._read_registry(dst))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[5] Voci orfane nel registro", flush=True)
try:
    reset_scene()
    arm2 = make_armature("Rig2", ["DEF-a", "MCH-a"])
    activate(arm2, pose=True)
    base_settings()
    apply()

    reg = addon._read_registry(arm2)
    reg.setdefault("osso_fantasma", {})["con_fantasma"] = {"obj": "Rig2", "bone": "DEF-x"}
    addon._write_registry(arm2, reg)
    check("voce orfana inserita", "osso_fantasma" in addon._read_registry(arm2))

    activate(arm2, pose=True)
    bpy.ops.actd.clean_registry()
    reg2 = addon._read_registry(arm2)
    check("voce orfana rimossa", "osso_fantasma" not in reg2, reg2)
    check("voce valida conservata", "MCH-a" in reg2, reg2)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[6] Constraint riconosciuto dopo rinomina", flush=True)
try:
    reset_scene()
    dst2 = make_armature("Rig_D", ["MCH-hand.L"])
    src2 = make_armature("Rig_S", ["DEF-hand.L"])
    activate(dst2, pose=True)
    s = base_settings()
    s.source_object = src2
    apply()

    pb = dst2.pose.bones["MCH-hand.L"]
    con = pb.constraints[0]
    con.name = "MioNome"
    check("rinomina applicata", con.name == "MioNome")
    check("ancora riconosciuto come generato", addon._is_generated(dst2, pb, con))

    activate(dst2, pose=True)
    remove()
    check("remove trova il constraint rinominato", len(pb.constraints) == 0)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[7] Validazione armatura sorgente", flush=True)
try:
    reset_scene()
    dst3 = make_armature("Rig_D2", ["MCH-hand.L"])
    src3 = make_armature("Rig_S2", ["DEF-hand.L"])
    activate(dst3, pose=True)

    check("sorgente = destinazione accettata",
          addon._source_obj(dst3, settings()) is dst3)
    check("sorgente valida accettata",
          addon.validate_source_object(dst3, src3) is None,
          addon.validate_source_object(dst3, src3))
    check("stessa armatura accettata",
          addon.validate_source_object(dst3, dst3) is None)

    # sorgente in Edit Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    activate(src3)
    bpy.ops.object.mode_set(mode='EDIT')
    err = addon.validate_source_object(dst3, src3)
    check("sorgente in Edit Mode rifiutata", err is not None and "Edit" in err, err)
    bpy.ops.object.mode_set(mode='OBJECT')

    # armatura senza ossa
    empty = bpy.data.objects.new("Vuota", bpy.data.armatures.new("VuotaData"))
    bpy.context.scene.collection.objects.link(empty)
    err2 = addon.validate_source_object(dst3, empty)
    check("armatura senza ossa rifiutata", err2 is not None, err2)

    # oggetto non armatura non selezionabile
    mesh = bpy.data.objects.new("Mesh", bpy.data.meshes.new("MeshData"))
    bpy.context.scene.collection.objects.link(mesh)
    err3 = addon.validate_source_object(dst3, mesh)
    check("oggetto non armatura rifiutato", err3 is not None, err3)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[8] Refresh nome constraint + UPDATE", flush=True)
try:
    reset_scene()
    arm3 = make_armature("Rig3", ["DEF-a", "MCH-a"])
    activate(arm3, pose=True)
    s = base_settings()
    s.constraint_name = "MioConstraint"
    apply()
    con = arm3.pose.bones["MCH-a"].constraints[0]
    check("nome manuale applicato", con.name == "MioConstraint", con.name)

    # rinomina manuale dell'utente
    con.name = "Rinominato"

    # refresh: ricalcola solo il nome suggerito nelle impostazioni
    bpy.ops.actd.refresh_constraint_name()
    sugg = settings().constraint_name
    check("refresh aggiorna il nome suggerito",
          "DEF" in sugg and "MCH" in sugg, sugg)

    # UPDATE applica davvero il nuovo nome al constraint esistente
    settings().update_mode = 'UPDATE'
    apply()
    names = [c.name for c in arm3.pose.bones["MCH-a"].constraints]
    check("UPDATE rinomina il constraint generato", names == [sugg], names)
    check("registro coerente dopo UPDATE",
          set(addon._read_registry(arm3).get("MCH-a", {})) == set(names),
          (addon._read_registry(arm3), names))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[9] register/unregister ciclico", flush=True)
try:
    addon.register()
    check("register() ripetuto tollerato", hasattr(bpy.context.scene, "actd_settings"))
    addon.unregister()
    check("unregister rimuove la proprieta'",
          not hasattr(bpy.types.Scene, "actd_settings"))
    addon.register()
    addon.unregister()
    addon.register()
    check("ciclo completo stabile", hasattr(bpy.context.scene, "actd_settings"))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST MODULO 1 =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("FALLITO" if FAIL else "SUPERATO"), flush=True)
