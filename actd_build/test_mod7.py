# -*- coding: utf-8 -*-
"""Test headless del Modulo 7: sostituzione (REPLACE) e backup JSON.

Copre la cartella di backup (blend salvato o TEMP), il nome del file per
armatura, la classificazione generato/manuale rispetto al registro, i due
REPLACE consecutivi, il caso KEEP senza rimozioni e lo schema completo del
JSON di backup.

Esecuzione:
    blender.exe --background --factory-startup --python test_mod7.py
"""

import glob
import json
import os
import re
import sys
import time
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


def activate(arm):
    """Rende l'armatura attiva in Pose Mode (l'operatore lavora su context.object)."""
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    if bpy.context.object.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')


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


def make_rig(name):
    return make_armature(
        name, ["DEF-a", "MCH-a", "DEF-b", "MCH-b", "MCH-manual"]
    )


def add_manual(arm, owner="MCH-manual", source="DEF-a", name="MANUALE"):
    pb = arm.pose.bones[owner]
    con = pb.constraints.new('COPY_TRANSFORMS')
    con.name = name
    con.target = arm
    con.subtarget = source
    return con


def backup_path(report):
    """Ultimo percorso di backup citato nel report (stringa vuota se assente)."""
    found = re.findall(r"Backup creato: (.+)", report)
    return found[-1].strip() if found else ""


def load_backup(path):
    """Contenuto del backup JSON; dizionario vuoto se manca o non e' valido."""
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except ValueError:
        return {}


def backup_files(arm_name):
    """Backup REPLACE gia' presenti nella cartella per una specifica armatura."""
    pattern = "actd_replace_backup_%s_*.json" % arm_name
    return sorted(glob.glob(os.path.join(
        glob.escape(addon._replace_backup_dir()), pattern
    )))


def remove_quiet(path):
    if path and os.path.isfile(path):
        os.remove(path)


def count_constraints(arm):
    return sum(len(pb.constraints) for pb in arm.pose.bones)


print("===== TEST MODULO 7 =====", flush=True)
addon.register()
check("register completa e operatore REPLACE disponibile",
      hasattr(bpy.ops.actd, "apply_transforms"))

# ---------------------------------------------------------------------------
print("\n[1] .blend non salvato: backup nella TEMP di Blender", flush=True)
path_1 = ""
try:
    reset_scene()
    arm = make_rig("Rig7a")
    s = base_settings()
    check("precondizione: nessun .blend salvato", bpy.data.filepath == "",
          bpy.data.filepath)
    check("cartella di backup = tempdir senza .blend",
          os.path.normcase(addon._replace_backup_dir())
          == os.path.normcase(bpy.app.tempdir),
          (addon._replace_backup_dir(), bpy.app.tempdir))

    bpy.ops.actd.apply_transforms()          # KEEP: crea i due generati
    s.existing_mode = 'REPLACE'
    res = bpy.ops.actd.apply_transforms(replace_scelta='GENERATED_ONLY')
    path_1 = backup_path(s.preview_report)
    check("sostituzione con backup creato",
          res == {'FINISHED'} and os.path.isfile(path_1), (res, path_1))
    check("backup scritto nella tempdir, non nella cwd",
          bool(path_1)
          and os.path.normcase(os.path.abspath(os.path.dirname(path_1)))
          == os.path.normcase(os.path.abspath(bpy.app.tempdir)),
          path_1)
    check("il report riporta il percorso del backup",
          bool(path_1) and ("Backup creato: " + path_1) in s.preview_report,
          s.preview_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    remove_quiet(path_1)

# ---------------------------------------------------------------------------
print("\n[2] Due armature con lo stesso osso: backup distinti", flush=True)
path_2a, path_2b = "", ""
try:
    reset_scene()
    rig_a = make_rig("Rig7b1")
    rig_b = make_rig("Rig7b2")
    s = base_settings()

    # Armatura A: soli generati, sostituzione GENERATED_ONLY.
    activate(rig_a)
    res_a = bpy.ops.actd.apply_transforms()
    s.existing_mode = 'REPLACE'
    bpy.ops.actd.apply_transforms(replace_scelta='GENERATED_ONLY')
    path_2a = backup_path(s.preview_report)

    # Armatura B: generati piu' un manuale, sostituzione ALL.
    activate(rig_b)
    s.existing_mode = 'KEEP'
    res_b = bpy.ops.actd.apply_transforms()
    manuale = add_manual(rig_b, "MCH-a", "DEF-a", "MANUALE_B")
    s.existing_mode = 'REPLACE'
    bpy.ops.actd.apply_transforms(replace_scelta='ALL')
    path_2b = backup_path(s.preview_report)

    check("apply riuscita su entrambe le armature",
          res_a == {'FINISHED'} and res_b == {'FINISHED'}, (res_a, res_b))
    check("due backup distinti e presenti",
          bool(path_2a) and bool(path_2b) and path_2a != path_2b
          and os.path.isfile(path_2a) and os.path.isfile(path_2b),
          (path_2a, path_2b))
    check("il nome del file contiene l'armatura",
          re.match(r"^actd_replace_backup_Rig7b1_\d{8}-\d{6}-\d{6}\.json$",
                   os.path.basename(path_2a) or "") is not None
          and re.match(r"^actd_replace_backup_Rig7b2_\d{8}-\d{6}-\d{6}\.json$",
                       os.path.basename(path_2b) or "") is not None,
          (os.path.basename(path_2a), os.path.basename(path_2b)))

    righe_a = load_backup(path_2a).get("righe", [])
    righe_b = load_backup(path_2b).get("righe", [])
    check("backup di Rig7b1: 2 generati, 0 manuali",
          len(righe_a) == 2
          and all(r.get("armatura") == "Rig7b1" for r in righe_a)
          and all(r.get("generato") is True for r in righe_a),
          [(r.get("armatura"), r.get("generato")) for r in righe_a])
    check("backup di Rig7b2: 3 righe della sola Rig7b2",
          len(righe_b) == 3
          and all(r.get("armatura") == "Rig7b2" for r in righe_b),
          [(r.get("armatura"), r.get("constraint")) for r in righe_b])
    generati_b = [r for r in righe_b if r.get("generato") is True]
    manuali_b = [r for r in righe_b if r.get("generato") is False]
    check("conteggi N/M per Rig7b2 = 2/1",
          (len(generati_b), len(manuali_b)) == (2, 1),
          (len(generati_b), len(manuali_b)))
    check("il manuale di Rig7b2 e' nel suo backup",
          "MANUALE_B" in [r.get("constraint") for r in righe_b],
          [r.get("constraint") for r in righe_b])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    remove_quiet(path_2a)
    remove_quiet(path_2b)

# ---------------------------------------------------------------------------
print("\n[3] Constraint manuale con nome AUTO_COPY ma fuori dal registro",
      flush=True)
path_3 = ""
try:
    reset_scene()
    arm = make_rig("Rig7c")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    reg_prima = addon._read_registry(arm)
    manuale = add_manual(arm, "MCH-a", "DEF-a", "AUTO_COPY_DEF_to_MCH_MAN")
    nome_manuale = manuale.name

    check("precondizione: due generati nel registro",
          len(reg_prima) == 2 and count_constraints(arm) == 3,
          (reg_prima, count_constraints(arm)))
    check("il manuale si chiama AUTO_COPY... e non e' nel registro",
          nome_manuale.startswith("AUTO_COPY")
          and nome_manuale not in addon._read_registry(arm).get("MCH-a", {}),
          (nome_manuale, addon._read_registry(arm).get("MCH-a", {})))

    results = addon.compute_mapping(arm, s)
    voci = addon._classifica_replace(
        arm, results, None, 'COPY_TRANSFORMS'
    )
    voce_manuale = [v for v in voci if v[1].name == nome_manuale]
    check("classificato MANUALE come dice il registro",
          len(voce_manuale) == 1 and voce_manuale[0][2] is False,
          [(v[1].name, v[2]) for v in voci])
    check("conteggio REPLACE = 2 generati / 1 manuale",
          addon._count_replace_targets(
              arm, results, None, 'COPY_TRANSFORMS') == (2, 1),
          addon._count_replace_targets(
              arm, results, None, 'COPY_TRANSFORMS'))
    check("la classificazione non scrive nel registro",
          len(addon._read_registry(arm)) == 2
          and nome_manuale
          not in addon._read_registry(arm).get("MCH-a", {}),
          addon._read_registry(arm))

    s.existing_mode = 'REPLACE'
    bpy.ops.actd.apply_transforms(replace_scelta='GENERATED_ONLY')
    path_3 = backup_path(s.preview_report)
    righe_3 = load_backup(path_3).get("righe", [])
    check("GENERATED_ONLY conserva il manuale AUTO_COPY",
          arm.pose.bones["MCH-a"].constraints.get(nome_manuale) is not None,
          [c.name for c in arm.pose.bones["MCH-a"].constraints])
    check("il backup contiene solo i due generati",
          len(righe_3) == 2
          and nome_manuale not in [r.get("constraint") for r in righe_3],
          [r.get("constraint") for r in righe_3])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    remove_quiet(path_3)

# ---------------------------------------------------------------------------
print("\n[4] Generato rinominato: classificazione coerente col registro",
      flush=True)
try:
    reset_scene()
    arm = make_rig("Rig7d")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    pba = arm.pose.bones["MCH-a"]
    pbb = arm.pose.bones["MCH-b"]
    con_a = pba.constraints[0]
    nome_originale = con_a.name
    con_a.name = "MIO_COPY"
    reg = addon._read_registry(arm)

    check("rinomina applicata, registro sul nome originale",
          con_a.name == "MIO_COPY"
          and nome_originale in reg.get("MCH-a", {}),
          (con_a.name, reg.get("MCH-a", {})))

    results = addon.compute_mapping(arm, s)
    voci = addon._classifica_replace(arm, results, None, 'COPY_TRANSFORMS')
    rinominata = [v for v in voci if v[1].name == "MIO_COPY"]
    check("il rinominato resta classificato manuale (nome fuori registro)",
          len(rinominata) == 1 and rinominata[0][2] is False,
          [(v[1].name, v[2]) for v in voci])
    check("conteggi REPLACE = 1 generato / 1 manuale",
          addon._count_replace_targets(
              arm, results, None, 'COPY_TRANSFORMS') == (1, 1),
          addon._count_replace_targets(
              arm, results, None, 'COPY_TRANSFORMS'))

    s.existing_mode = 'REPLACE'
    res = bpy.ops.actd.apply_transforms(replace_scelta='GENERATED_ONLY')
    check("GENERATED_ONLY non rimuove il rinominato senza conferma",
          res == {'FINISHED'} and pba.constraints.get("MIO_COPY") is not None,
          (res, [c.name for c in pba.constraints]))
    check("l'altro osso viene comunque ricreato e marcato",
          len(pbb.constraints) == 1
          and addon._is_generated(arm, pbb, pbb.constraints[0]),
          [(c.name, c.type) for c in pbb.constraints])
    check("report: 1 rimosso e 1 saltato",
          "Constraint sostituiti (rimossi): 1" in s.preview_report
          and "Constraint saltati: 1" in s.preview_report,
          s.preview_report.replace("\n", " / "))
    check("la voce del registro resta sul nome originale (orfana)",
          nome_originale in addon._read_registry(arm).get("MCH-a", {})
          and "MIO_COPY"
          not in addon._read_registry(arm).get("MCH-a", {}),
          addon._read_registry(arm).get("MCH-a", {}))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[5] REPLACE su armatura senza constraint esistenti", flush=True)
path_5 = ""
try:
    reset_scene()
    arm = make_rig("Rig7e")
    s = base_settings()
    check("precondizione: nessun constraint sulla riga",
          count_constraints(arm) == 0, count_constraints(arm))

    s.existing_mode = 'REPLACE'
    res = bpy.ops.actd.apply_transforms(replace_scelta='ALL')
    path_5 = backup_path(s.preview_report)
    payload_5 = load_backup(path_5)
    righe_5 = payload_5.get("righe", [])
    check("sostituzione FINISHED con 2 constraint creati",
          res == {'FINISHED'} and count_constraints(arm) == 2
          and "Constraint creati: 2" in s.preview_report,
          (res, count_constraints(arm)))
    check("report: nessun constraint rimosso",
          "Constraint sostituiti (rimossi): 0" in s.preview_report,
          s.preview_report.replace("\n", " / "))
    # Comportamento reale: il backup viene scritto anche se non c'e' nulla da
    # rimuovere (file con "righe": []). Resta da decidere se sia desiderabile:
    # qui lo si documenta, senza assumerlo come comportamento corretto.
    check("backup scritto anche a vuoto (comportamento da decidere)",
          bool(path_5) and os.path.isfile(path_5), path_5)
    check("il backup a vuoto e' JSON valido con zero righe",
          isinstance(payload_5, dict) and righe_5 == []
          and "generato_il" in payload_5, payload_5)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    remove_quiet(path_5)

# ---------------------------------------------------------------------------
print("\n[6] Due REPLACE consecutivi: il secondo non sovrascrive il primo",
      flush=True)
path_6a, path_6b = "", ""
try:
    reset_scene()
    arm = make_rig("Rig7f")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    s.existing_mode = 'REPLACE'
    bpy.ops.actd.apply_transforms(replace_scelta='GENERATED_ONLY')
    path_6a = backup_path(s.preview_report)

    # Attesa di un secondo: il nome del backup usa il timestamp al secondo.
    time.sleep(1.1)
    add_manual(arm, "MCH-a", "DEF-a", "MANUALE_F")
    bpy.ops.actd.apply_transforms(replace_scelta='ALL')
    path_6b = backup_path(s.preview_report)

    check("primo backup creato", bool(path_6a) and os.path.isfile(path_6a),
          path_6a)
    check("secondo backup creato", bool(path_6b) and os.path.isfile(path_6b),
          path_6b)
    check("i due percorsi sono diversi", path_6a != path_6b,
          (path_6a, path_6b))
    check("il primo file esiste ancora dopo il secondo REPLACE",
          os.path.isfile(path_6a), path_6a)
    righe_6a = load_backup(path_6a).get("righe", [])
    righe_6b = load_backup(path_6b).get("righe", [])
    check("entrambi i file si leggono come JSON",
          isinstance(righe_6a, list) and isinstance(righe_6b, list)
          and bool(load_backup(path_6a)) and bool(load_backup(path_6b)),
          (len(righe_6a), len(righe_6b)))
    check("il primo backup conserva 2 righe, il secondo 3",
          (len(righe_6a), len(righe_6b)) == (2, 3),
          (len(righe_6a), len(righe_6b)))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    remove_quiet(path_6a)
    remove_quiet(path_6b)

# ---------------------------------------------------------------------------
print("\n[7] KEEP con replace_scelta='ALL': nessuna rimozione, nessun backup",
      flush=True)
try:
    reset_scene()
    arm = make_rig("Rig7g")
    s = base_settings()
    bpy.ops.actd.apply_transforms()          # 2 generati
    prima = backup_files("Rig7g")
    s.existing_mode = 'KEEP'
    res = bpy.ops.actd.apply_transforms(replace_scelta='ALL')
    dopo = backup_files("Rig7g")

    check("nessun backup creato in modalita' KEEP",
          res == {'FINISHED'} and prima == [] and dopo == [], (prima, dopo))
    check("nessun constraint rimosso",
          count_constraints(arm) == 2, count_constraints(arm))
    check("report senza riga 'Backup creato'",
          "Backup creato" not in s.preview_report,
          s.preview_report.replace("\n", " / "))
    check("report: zero sostituiti",
          "Constraint sostituiti (rimossi): 0" in s.preview_report,
          s.preview_report.replace("\n", " / "))
    check("registro ancora con i due generati",
          len(addon._read_registry(arm)) == 2, addon._read_registry(arm))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[8] Schema completo del backup JSON su un campione reale", flush=True)
path_8 = ""
try:
    reset_scene()
    arm = make_rig("Rig7h")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    manuale = add_manual(arm, "MCH-a", "DEF-a", "MANUALE_H")
    manuale.influence = 0.5
    manuale.mute = True
    manuale.owner_space = 'LOCAL'
    manuale.target_space = 'WORLD'
    mix_atteso = manuale.mix_mode

    s.existing_mode = 'REPLACE'
    res = bpy.ops.actd.apply_transforms(replace_scelta='ALL')
    path_8 = backup_path(s.preview_report)
    payload = load_backup(path_8)
    righe = payload.get("righe", [])
    riga = next((r for r in righe if r.get("constraint") == "MANUALE_H"), {})
    schema_riga = {
        "armatura", "osso", "constraint", "tipo", "sorgente",
        "target_object", "influenza", "mix_mode", "spazi", "stato",
        "generato", "timestamp",
    }

    check("backup creato con le tre righe attese",
          res == {'FINISHED'} and len(righe) == 3, (res, len(righe)))
    check("chiavi di primo livello: versione, generato_il, righe",
          set(payload.keys()) == {"versione", "generato_il", "righe"},
          sorted(payload.keys()))
    versione_attesa = ".".join(str(x) for x in addon.bl_info["version"])
    check("versione del backup uguale a bl_info",
          payload.get("versione") == versione_attesa,
          (payload.get("versione"), versione_attesa))
    check("la riga ha esattamente i 12 campi dello schema",
          bool(riga) and set(riga.keys()) == schema_riga,
          sorted(riga.keys()))
    check("campi descrittivi della riga",
          riga.get("armatura") == "Rig7h"
          and riga.get("osso") == "MCH-a"
          and riga.get("constraint") == "MANUALE_H"
          and riga.get("tipo") == 'COPY_TRANSFORMS'
          and riga.get("sorgente") == "DEF-a"
          and riga.get("target_object") == "Rig7h"
          and riga.get("generato") is False,
          riga)
    check("influenza, spazi, stato e mix coerenti col constraint",
          riga.get("influenza") == "0.500"
          and riga.get("spazi") == "WORLD/LOCAL"
          and riga.get("stato") == "muto"
          and riga.get("mix_mode") == mix_atteso
          and bool(mix_atteso),
          (riga.get("influenza"), riga.get("spazi"),
           riga.get("stato"), riga.get("mix_mode")))
    timestamp = [r.get("timestamp") for r in righe]
    check("timestamp ISO 8601 su tutte le righe, identico",
          bool(timestamp) and len(set(timestamp)) == 1
          and all(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", t or "")
                  is not None for t in timestamp),
          timestamp)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    remove_quiet(path_8)

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST MODULO 7 =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)
