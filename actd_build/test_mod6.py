# -*- coding: utf-8 -*-
"""Test headless del Modulo 6: manutenzione dei constraint generati.

Copre conversione in manuali, pulizia del registro, mute globale ed export
CSV/JSON.

Esecuzione:
    blender.exe --background --factory-startup --python test_mod6.py
"""

import csv
import json
import os
import re
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
    addon._clear_collection(s.preview_items)
    addon._clear_collection(s.diagnostic_items)
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            addon._write_registry(obj, {})
    return s


def make_rig(name):
    return make_armature(
        name, ["DEF-a", "MCH-a", "DEF-b", "MCH-b", "MCH-manual"]
    )


def add_manual(arm, owner="MCH-manual", source="DEF-a"):
    pb = arm.pose.bones[owner]
    con = pb.constraints.new('COPY_ROTATION')
    con.name = "MANUALE"
    con.target = arm
    con.subtarget = source
    return con


def export_path(report):
    found = re.findall(r"Report salvato in: (.+)", report)
    return found[-1].strip() if found else ""


print("===== TEST MODULO 6 =====", flush=True)
addon.register()
check("mute_state default False", settings().mute_state is False)

# ---------------------------------------------------------------------------
print("\n[1] Il registro memorizza il tipo", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig1")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    reg = addon._read_registry(arm)
    check("due voci nel registro", len(reg) == 2, reg)
    tipi = [
        entry.get("type")
        for entries in reg.values() for entry in entries.values()
    ]
    check("tipo COPY_TRANSFORMS registrato",
          tipi == ['COPY_TRANSFORMS', 'COPY_TRANSFORMS'], tipi)
    add_manual(arm)
    check("constraint manuale fuori dal registro",
          "MANUALE" not in addon._read_registry(arm).get("MCH-manual", {}))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[2] Converti in manuali", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig2")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    add_manual(arm)
    res = bpy.ops.actd.convert_to_manual()
    check("convert FINISHED", res == {'FINISHED'}, res)
    check("registro svuotato", addon._read_registry(arm) == {},
          addon._read_registry(arm))
    totale = sum(len(pb.constraints) for pb in arm.pose.bones)
    check("i constraint restano sulla riga", totale == 3, totale)
    check("report con 2 conversioni",
          "convertiti in manuali: 2" in s.last_report,
          s.last_report.replace("\n", " / "))

    res = bpy.ops.actd.remove_generated()
    totale = sum(len(pb.constraints) for pb in arm.pose.bones)
    check("remove_generated non tocca i convertiti",
          res == {'FINISHED'} and totale == 3, totale)
    check("report con 0 rimossi",
          "Constraint rimossi: 0" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[3] Mute globale dei soli generati", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig3")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    manual = add_manual(arm)

    res = bpy.ops.actd.mute_all()
    generati = [
        con for pb in arm.pose.bones for con in pb.constraints
        if addon._is_generated(arm, pb, con)
    ]
    check("mute_all FINISHED", res == {'FINISHED'}, res)
    check("stato mute attivo", s.mute_state is True)
    check("tutti i generati sono mutati",
          len(generati) == 2 and all(c.mute for c in generati),
          [c.mute for c in generati])
    check("il manuale non viene mutato", manual.mute is False)
    check("report 2 mutati", "mutati: 2" in s.last_report,
          s.last_report.replace("\n", " / "))

    res = bpy.ops.actd.mute_all()
    generati = [
        con for pb in arm.pose.bones for con in pb.constraints
        if addon._is_generated(arm, pb, con)
    ]
    check("secondo toggle smuta", s.mute_state is False)
    check("generati riattivati",
          len(generati) == 2 and all(not c.mute for c in generati),
          [c.mute for c in generati])
    check("report 2 riattivati", "riattivati: 2" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[4] Pulisci registro: constraint sparito", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig4")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    pba = arm.pose.bones["MCH-a"]
    nome_a = pba.constraints[0].name
    pba.constraints.remove(pba.constraints[0])

    res = bpy.ops.actd.clean_registry()
    reg = addon._read_registry(arm)
    check("clean FINISHED", res == {'FINISHED'}, res)
    check("voce del constraint sparito rimossa",
          nome_a not in reg.get("MCH-a", {}), reg)
    check("voce valida conservata", "MCH-b" in reg, reg)
    check("report con 1 voce rimossa",
          "Voci orfane rimosse dal registro: 1" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[5] Pulisci registro: tipo non coerente", flush=True)
try:
    arm = bpy.context.object
    manual = add_manual(arm)
    reg = addon._read_registry(arm)
    reg.setdefault("MCH-manual", {})["MANUALE"] = {
        "obj": arm.name,
        "bone": "DEF-a",
        "type": "COPY_SCALE",
    }
    addon._write_registry(arm, reg)

    res = bpy.ops.actd.clean_registry()
    reg = addon._read_registry(arm)
    check("clean FINISHED", res == {'FINISHED'}, res)
    check("voce con tipo sbagliato rimossa",
          "MANUALE" not in reg.get("MCH-manual", {}), reg)
    check("constraint manuale ancora presente",
          manual in list(arm.pose.bones["MCH-manual"].constraints))
    check("voce valida conservata", "MCH-b" in reg, reg)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[6] Pulisci registro: subtarget inesistente", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig6")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    pba = arm.pose.bones["MCH-a"]
    con_a = pba.constraints[0]
    con_a.subtarget = "DEF-Missing"

    res = bpy.ops.actd.clean_registry()
    reg = addon._read_registry(arm)
    check("clean FINISHED", res == {'FINISHED'}, res)
    check("voce con subtarget invalido rimossa",
          con_a.name not in reg.get("MCH-a", {}), reg)
    check("constraint resta sulla riga (solo registro)",
          con_a in list(pba.constraints))
    check("altra voce valida conservata", "MCH-b" in reg, reg)
    check("report con 1 voce rimossa",
          "Voci orfane rimosse dal registro: 1" in s.last_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[7] Export CSV", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig7")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    add_manual(arm)

    res = bpy.ops.actd.export_csv()
    path = export_path(s.last_report)
    check("export_csv FINISHED", res == {'FINISHED'}, res)
    check("file CSV creato", os.path.isfile(path), path)
    righe = []
    intestazione = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            intestazione = reader.fieldnames
            righe = list(reader)
    check("intestazione CSV completa",
          intestazione == list(addon._EXPORT_FIELDS), intestazione)
    check("due righe esportate (solo generati)", len(righe) == 2,
          len(righe))
    riga = next((r for r in righe if r["osso"] == "MCH-a"), {})
    check("campi della riga coerenti",
          riga.get("armatura") == "Rig7"
          and riga.get("tipo") == "COPY_TRANSFORMS"
          and riga.get("sorgente") == "DEF-a"
          and riga.get("target_object") == "Rig7"
          and riga.get("influenza") == "1.000"
          and riga.get("mix_mode") == "REPLACE"
          and riga.get("spazi") == "WORLD/WORLD"
          and riga.get("stato") == "attivo",
          riga)
    if os.path.isfile(path):
        os.remove(path)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[8] Export JSON con stato mute", flush=True)
try:
    s = settings()
    bpy.ops.actd.mute_all()
    res = bpy.ops.actd.export_json()
    path = export_path(s.last_report)
    payload = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    check("export_json FINISHED", res == {'FINISHED'}, res)
    check("file JSON creato", os.path.isfile(path), path)
    check("versione e timestamp presenti",
          payload.get("versione") == "1.1.0"
          and "T" in str(payload.get("generato_il", "")),
          payload.get("versione"))
    righe = payload.get("righe", [])
    check("due righe JSON", isinstance(righe, list) and len(righe) == 2,
          len(righe) if isinstance(righe, list) else righe)
    check("stato muto esportato",
          all(r.get("stato") == "muto" for r in righe),
          [r.get("stato") for r in righe])
    check("campi JSON coerenti",
          all(set(addon._EXPORT_FIELDS) <= set(r.keys()) for r in righe))
    if os.path.isfile(path):
        os.remove(path)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[9] Operatori e pannello registrati", flush=True)
try:
    for nome in ("convert_to_manual", "mute_all", "export_csv", "export_json"):
        check("operatore " + nome,
              hasattr(bpy.ops.actd, nome))
    check("pannello ACTD_PT_maintenance in _classes",
          addon.ACTD_PT_maintenance in addon._classes)
    check("pannello registrato in Blender",
          hasattr(bpy.types, "ACTD_PT_maintenance"))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST MODULO 6 =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)