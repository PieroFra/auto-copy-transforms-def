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
    # Report isolati per pannello (anteprima, diagnostica, manutenzione).
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
    # Versione attesa derivata da bl_info: nessun aggiornamento ai futuri bump
    versione_attesa = ".".join(str(x) for x in addon.bl_info["version"])
    check("versione e timestamp presenti",
          payload.get("versione") == versione_attesa
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

    # Layout: i controlli avanzati sono un vero pannello figlio richiudibile,
    # registrato subito dopo il principale, e l'anteprima non è più chiusa.
    check("pannello ACTD_PT_advanced in _classes",
          addon.ACTD_PT_advanced in addon._classes)
    check("pannello Avanzate registrato in Blender",
          hasattr(bpy.types, "ACTD_PT_advanced"))
    check("Avanzate figlio del pannello principale",
          addon.ACTD_PT_advanced.bl_parent_id == "ACTD_PT_main")
    check("Avanzate subito dopo il principale in _classes",
          addon._classes.index(addon.ACTD_PT_advanced)
          == addon._classes.index(addon.ACTD_PT_main) + 1)
    check("Avanzate richiudibile di default",
          'DEFAULT_CLOSED' in addon.ACTD_PT_advanced.bl_options,
          addon.ACTD_PT_advanced.bl_options)
    check("anteprima aperta di default (lista visibile)",
          addon.ACTD_PT_preview.bl_options == set(),
          addon.ACTD_PT_preview.bl_options)
    check("manutenzione e diagnostica restano richiudibili",
          'DEFAULT_CLOSED' in addon.ACTD_PT_maintenance.bl_options
          and 'DEFAULT_CLOSED' in addon.ACTD_PT_diagnostics.bl_options)

    # La label della mappatura segue i token correnti, non resta al default.
    s = settings()
    tokens = (s.source_token, s.dest_token, s.source_token_type,
              s.dest_token_type)
    try:
        s.source_token = "DEF_"
        s.dest_token = "MCH_"
        s.source_token_type = 'PREFIX'
        s.dest_token_type = 'PREFIX'
        etichetta = addon._mapping_label_text(s)
        check("label mappatura con i token correnti",
              etichetta.endswith("DEF_* → MCH_*"), etichetta)
        s.source_token = "ORG_"
        s.dest_token = "_ctrl"
        s.dest_token_type = 'SUFFIX'
        etichetta = addon._mapping_label_text(s)
        check("label mappatura segue prefisso e suffisso",
              etichetta.endswith("ORG_* → *_ctrl"), etichetta)
    finally:
        (s.source_token, s.dest_token, s.source_token_type,
         s.dest_token_type) = tokens
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[10] Report isolati: anteprima, diagnostica e manutenzione", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig10")
    s = base_settings()
    res = bpy.ops.actd.apply_transforms()
    anteprima = s.preview_report
    check("apply scrive preview_report",
          res == {'FINISHED'} and "Constraint creati" in anteprima,
          anteprima.replace("\n", " / "))
    check("manutenzione ancora vuota dopo apply",
          s.maintenance_report == "", s.maintenance_report)

    bpy.ops.actd.diagnose()
    check("la diagnostica non tocca il report di anteprima",
          s.preview_report == anteprima, s.preview_report)
    check("la diagnostica scrive diagnostic_report",
          bool(s.diagnostic_report), s.diagnostic_report)

    bpy.ops.actd.mute_all()
    check("mute_all aggiorna solo la manutenzione",
          "mutati: 2" in s.maintenance_report
          and s.preview_report == anteprima,
          s.maintenance_report.replace("\n", " / "))

    res = bpy.ops.actd.convert_to_manual()
    check("convert_to_manual scrive maintenance_report",
          res == {'FINISHED'}
          and "convertiti in manuali" in s.maintenance_report,
          s.maintenance_report.replace("\n", " / "))
    check("anteprima intatta dopo la manutenzione",
          s.preview_report == anteprima, s.preview_report)
    check("nessuna duplicazione tra anteprima e manutenzione",
          s.maintenance_report != s.preview_report
          and "Constraint creati" not in s.maintenance_report,
          s.maintenance_report.replace("\n", " / "))
    check("last_report segue l'ultima azione",
          s.last_report == s.maintenance_report, s.last_report)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[11] Layout headless: ordine, label e disegno dei pannelli", flush=True)


class _FakeOperator:
    """Operatore finto per le proprietà impostate dai pannelli."""

    def __init__(self):
        self.preset = None
        self.token_type = None
        self.clear = None
        self.url = None


class _FakeLayout:
    """Layout finto minimale che registra le chiamate dei pannelli.

    Non disegna nulla: serve solo a eseguire `draw` in headless per verificare
    che i pannelli non sollevino eccezioni, che le proprietà usate esistano e
    che gli operatori invocati siano registrati. Ogni sotto-layout ha il proprio
    stato `enabled`, così i test possono verificare i controlli disabilitati.
    """

    def __init__(self, record):
        self._record = record
        self.enabled = True

    def _child(self):
        return _FakeLayout(self._record)

    def box(self):
        self._record.append(("box", None))
        return self._child()

    def row(self, align=False, **kwargs):
        self._record.append(("row", align))
        return self._child()

    def column(self, align=False, **kwargs):
        self._record.append(("column", align))
        return self._child()

    def label(self, text="", icon='NONE', **kwargs):
        self._record.append(("label", text, icon))

    def prop(self, data, name, text="", **kwargs):
        if not hasattr(data, name):
            raise AttributeError("proprietà mancante nella UI: " + name)
        # Il testo è registrato: i test di layout verificano le label esterne.
        self._record.append(("prop", name, text))

    def prop_search(self, data, name, search_data, search_prop, text="",
                    **kwargs):
        if not hasattr(data, name):
            raise AttributeError("proprietà mancante nella UI: " + name)
        if not hasattr(search_data, search_prop):
            raise AttributeError(
                "collezione di ricerca mancante: " + search_prop
            )
        self._record.append(
            ("prop_search", name, search_prop, self.enabled)
        )

    def operator(self, idname, text="", icon='NONE', **kwargs):
        if not idname.startswith("actd."):
            raise ValueError("operatore inatteso: " + idname)
        if not hasattr(bpy.ops.actd, idname.split(".", 1)[1]):
            raise ValueError("operatore non registrato: " + idname)
        self._record.append(
            ("operator", idname, text, icon, self.enabled)
        )
        return _FakeOperator()

    def template_list(self, *args, **kwargs):
        self._record.append(("template_list", args[0] if args else ""))


class _FakePanel:
    """Sostituto di `self` per chiamare `draw` sui pannelli reali."""

    def __init__(self, record):
        self.layout = _FakeLayout(record)


def draw_panel(panel, context):
    record = []
    panel.draw(_FakePanel(record), context)
    return record


try:
    # (a) Senza un osso selezionato la nota spiega la condizione di Learn.
    reset_scene()
    nota, icona = addon._learn_condition_note(bpy.context)
    # La nota deve citare la Pose Mode: è la condizione richiesta dal poll.
    check("Learn: condizione spiegata quando il poll è falso",
          addon.ACTD_OT_learn_pattern.poll(bpy.context) is False
          and icona == 'INFO' and "constraint" in nota
          and "Pose Mode" in nota, (nota, icona))
    nota_en = addon._EN_TRANSLATIONS[
        "Serve un osso in Pose Mode con un constraint di copia"]
    check("Learn: variante inglese della nota cita Pose Mode",
          "Pose Mode" in nota_en, nota_en)

    # (b) Con osso selezionato e constraint di copia il poll è vero e la nota
    #     diventa di conferma: la semantica dell'operatore non cambia.
    arm = make_armature("RigLayout", ["DEF_Hand.L", "MCH_Hand.L"])
    s = base_settings()
    s.source_token = "DEF_"
    s.dest_token = "MCH_"
    s.source_token_type = 'PREFIX'
    s.dest_token_type = 'PREFIX'
    pb = arm.pose.bones["MCH_Hand.L"]
    con = pb.constraints.new('COPY_TRANSFORMS')
    con.target = arm
    con.subtarget = "DEF_Hand.L"
    for pose_bone in arm.pose.bones:
        pose_bone.select = False
    arm.pose.bones["MCH_Hand.L"].select = True
    bpy.context.view_layer.update()
    nota, icona = addon._learn_condition_note(bpy.context)
    check("Learn: nota di conferma quando il poll è vero",
          addon.ACTD_OT_learn_pattern.poll(bpy.context) is True
          and icona == 'CHECKMARK', (nota, icona))

    # (c) Disegno dei pannelli senza eccezioni.
    for panel, nome in (
        (addon.ACTD_PT_main, "principale"),
        (addon.ACTD_PT_advanced, "Avanzate"),
        (addon.ACTD_PT_preview, "anteprima"),
        (addon.ACTD_PT_maintenance, "manutenzione"),
        (addon.ACTD_PT_diagnostics, "diagnostica"),
    ):
        try:
            record = draw_panel(panel, bpy.context)
            check("draw del pannello " + nome + " senza errori",
                  any(r[0] in ("label", "operator") for r in record),
                  record[:4])
        except Exception:
            traceback.print_exc()
            check("draw del pannello " + nome + " senza errori", False,
                  traceback.format_exc().strip().splitlines()[-1])

    # (d) Flusso del principale: Anteprima e Applica prima dei token.
    record = draw_panel(addon.ACTD_PT_main, bpy.context)
    operatori = [r[1] for r in record if r[0] == "operator"]
    check("anteprima e applica in cima al pannello",
          operatori[:2] == ["actd.preview", "actd.apply_transforms"],
          operatori[:4])

    # (e) I controlli avanzati vivono solo nel pannello figlio.
    props_main = [r[1] for r in record if r[0] == "prop"]
    props_avanzate = [
        r[1] for r in draw_panel(addon.ACTD_PT_advanced, bpy.context)
        if r[0] == "prop"
    ]
    # I controlli avanzati includono anche tipo/nome constraint e le opzioni
    # sui constraint esistenti: sono stati spostati nel pannello figlio.
    avanzati = {"mix_mode", "use_collection_filter", "custom_pattern",
                "stack_position", "constraint_type", "constraint_name",
                "existing_mode", "update_mode", "avoid_duplicates"}
    check("filtro, pattern e mix nel pannello Avanzate",
          avanzati <= set(props_avanzate), props_avanzate)
    check("il pannello principale non ridisegna i controlli avanzati",
          not (avanzati & set(props_main)), props_main)

    # (f) Il menu dei preset usa items statiche (Blender 5.2 non registra gli
    #     enum con callback): le voci restano sempre le quattro della tabella.
    s.source_token = "MCH_"
    s.source_token_type = 'PREFIX'
    record = draw_panel(addon.ACTD_PT_main, bpy.context)
    label_righe = [r for r in record if r[0] == "label"]
    preset_props = [r for r in record
                    if r[0] == "prop" and r[1] == "dest_preset_choice"]
    check("menu preset destinazione disegnato nel principale",
          len(preset_props) == 1
          and preset_props[0][2] == ""
          and 0 <= next((i for i, r in enumerate(record)
                         if r[0] == "label"
                         and r[1] == "Preset destinazione:"), -1)
          < record.index(preset_props[0])
          and hasattr(bpy.ops.actd, "dest_preset"),
          (preset_props, hasattr(bpy.ops.actd, "dest_preset")))
    # Anche l'avviso REPLACE e' spezzato: le righe disegnate coincidono con
    # `_ui_report_lines` e nessuna supera la larghezza utile della sidebar.
    righe_replace = addon._ui_report_lines(
        bpy.app.translations.pgettext(
            "Sostituisci rimuove anche i constraint manuali dello stesso tipo"))
    etichette_adv = [
        r[1] for r in draw_panel(addon.ACTD_PT_advanced, bpy.context)
        if r[0] == "label" and r[2] == 'ERROR'
    ]
    check("nessuna label oltre la larghezza della UI",
          all(len(r[1]) <= addon._UI_TEXT_WIDTH for r in label_righe)
          and bool(righe_replace)
          and all(len(r) <= addon._UI_TEXT_WIDTH for r in righe_replace)
          and etichette_adv == righe_replace,
          ([r[1] for r in label_righe if len(r[1]) > addon._UI_TEXT_WIDTH],
           etichette_adv))
    # Larghezza ridotta: la sidebar reale tronca con '…' oltre ~40 caratteri.
    check("larghezza testo UI entro la sidebar (34)",
          addon._UI_TEXT_WIDTH == 34, addon._UI_TEXT_WIDTH)
    preset_tokens = [voce[0] for voce in addon.DEST_PRESET_ITEMS]
    check("menu preset con items statiche (4 voci)",
          preset_tokens == ["MCH_", "ORG_", "DEF_", "_ctrl"],
          preset_tokens)
    learn_lines = addon._ui_report_lines(
        addon._learn_condition_note(bpy.context)[0])
    check("nota Learn spezzata entro la larghezza della UI",
          bool(learn_lines) and all(len(r) <= 34 for r in learn_lines),
          learn_lines)

    # (g) Il vecchio rimando al pannello Avanzate non deve più comparire:
    #     si troncava ed era ridondante rispetto al pannello figlio.
    check("nessun rimando ridondante al pannello Avanzate",
          not any("Avanzate" in r[1] for r in label_righe),
          [r[1] for r in label_righe if "Avanzate" in r[1]])

    # (h) Nome constraint: label esterna e campo senza testo, così il nome
    #     usa tutta la larghezza disponibile invece di essere troncato.
    record_adv = draw_panel(addon.ACTD_PT_advanced, bpy.context)
    idx_label = next(
        (i for i, r in enumerate(record_adv)
         if r[0] == "label" and r[1] == "Nome constraint"), -1
    )
    idx_prop = next(
        (i for i, r in enumerate(record_adv)
         if r[0] == "prop" and r[1] == "constraint_name"), -1
    )
    check("nome constraint a piena larghezza con label esterna",
          0 <= idx_label < idx_prop and record_adv[idx_prop][2] == "",
          (idx_label, idx_prop))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[12] Preset destinazione: items statiche e applicazione", flush=True)
try:
    s = settings()
    s.source_token = "DEF_"
    s.source_token_type = 'PREFIX'
    s.dest_preset_choice = "MCH_"
    s.dest_preset_notice = ""

    # (a) La proprieta' del menu esiste ed e' un EnumProperty semplice.
    proprieta_preset = s.bl_rna.properties.get("dest_preset_choice")
    check("proprieta' dest_preset_choice registrata",
          proprieta_preset is not None
          and proprieta_preset.type == 'ENUM'
          and proprieta_preset.is_enum_flag is False
          and proprieta_preset.name == "Preset",
          (proprieta_preset, getattr(proprieta_preset, "name", None)))
    # (b) Le voci sono statiche: quattro preset, sempre gli stessi.
    preset_tokens = [voce[0] for voce in addon.DEST_PRESET_ITEMS]
    check("items statiche: quattro preset nell'ordine della tabella",
          preset_tokens == ["MCH_", "ORG_", "DEF_", "_ctrl"]
          and len(addon._DEST_PRESETS) == 4
          and all(len(voce) == 3 and "Token destinazione" in voce[2]
                  for voce in addon.DEST_PRESET_ITEMS),
          (preset_tokens, addon.DEST_PRESET_ITEMS))
    check("proprieta' registrata con quattro voci statiche",
          len(proprieta_preset.enum_items) == 4,
          [voce.identifier for voce in proprieta_preset.enum_items])
    # (c) Scegliendo un preset valido il token destinazione viene impostato.
    s.dest_token = "MCH_"
    s.dest_token_type = 'PREFIX'
    s.dest_preset_choice = "ORG_"
    check("scegliendo un preset cambia il token destinazione",
          s.dest_token == "ORG_" and s.dest_token_type == 'PREFIX'
          and s.dest_preset_notice == "",
          (s.dest_token, s.dest_token_type, s.dest_preset_notice))
    # (d) Il preset in conflitto con la sorgente non tocca il token.
    s.source_token = "ORG_"
    s.dest_token = "MCH_"
    s.dest_token_type = 'PREFIX'
    s.dest_preset_choice = "ORG_"
    check("preset uguale alla sorgente: token invariato e avviso",
          s.dest_token == "MCH_"
          and "ORG_" in s.dest_preset_notice
          and addon._dest_preset_is_self_match(s, "ORG_", 'PREFIX') is True,
          (s.dest_token, s.dest_preset_notice))
    check("stesso token ma tipo diverso non e' self-match",
          addon._dest_preset_is_self_match(s, "_ctrl", 'SUFFIX') is False
          and addon._dest_preset_is_self_match(s, "_ctrl", 'PREFIX') is False)
    # (e) Con sorgente a suffisso il conflitto scatta solo a parita' di tipo.
    s.source_token = "_ctrl"
    s.source_token_type = 'SUFFIX'
    s.dest_token = "MCH_"
    s.dest_token_type = 'PREFIX'
    s.dest_preset_choice = "_ctrl"
    check("preset suffisso uguale alla sorgente non applicato",
          s.dest_token == "MCH_" and bool(s.dest_preset_notice),
          (s.dest_token, s.dest_preset_notice))

    # (f) L'aiutante unico applica token e tipo; lo usa anche l'operatore.
    s.source_token = "DEF_"
    s.source_token_type = 'PREFIX'
    addon._apply_dest_preset(
        s, "_ctrl", addon._dest_preset_token_type("_ctrl")
    )
    check("_apply_dest_preset imposta token e tipo",
          s.dest_token == "_ctrl" and s.dest_token_type == 'SUFFIX',
          (s.dest_token, s.dest_token_type))
    check("operatore preset ancora registrato (4 preset)",
          hasattr(bpy.ops.actd, "dest_preset")
          and len(addon._DEST_PRESETS) == 4,
          addon._DEST_PRESETS)
    risultato = bpy.ops.actd.dest_preset(preset="MCH_", token_type='PREFIX')
    check("l'operatore preset applica il token",
          'FINISHED' in risultato and s.dest_token == "MCH_",
          (risultato, s.dest_token))

    # (g) Il pannello principale disegna il menu e l'avviso spezzato.
    s.source_token = "DEF_"
    s.source_token_type = 'PREFIX'
    s.dest_token = "MCH_"
    s.dest_token_type = 'PREFIX'
    s.dest_preset_choice = "DEF_"
    record = draw_panel(addon.ACTD_PT_main, bpy.context)
    menu = [r for r in record
            if r[0] == "prop" and r[1] == "dest_preset_choice"]
    pulsanti = [r for r in record
                if r[0] == "operator" and r[1] == "actd.dest_preset"]
    check("menu preset disegnato nel pannello principale",
          len(menu) == 1 and menu[0][2] == ""
          and any(r[0] == "label" and r[1] == "Preset destinazione:"
                  for r in record)
          and not pulsanti,
          (menu, pulsanti))
    avviso = [r for r in record
              if r[0] == "label" and r[1].startswith("Preset ")
              and r[2] == 'ERROR']
    check("avviso preset mostrato come label spezzata",
          bool(avviso) and avviso[0][2] == 'ERROR'
          and all(len(r[1]) <= addon._UI_TEXT_WIDTH for r in avviso)
          and s.dest_token == "MCH_",
          avviso)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[13] Bone collection: prop_search con fallback testo", flush=True)


def make_collection(arm, name, bone_names):
    coll = arm.data.collections.new(name)
    for bn in bone_names:
        coll.assign(arm.data.bones[bn])
    return coll


try:
    reset_scene()
    dst = make_armature("RigSearchDst", ["DEF-a", "MCH-a"])
    src = make_armature("RigSearchSrc", ["DEF-a", "MCH-a"])
    make_collection(dst, "Meccaniche", ["MCH-a"])
    make_collection(src, "Deform", ["DEF-a"])
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    bpy.context.view_layer.objects.active = dst
    dst.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    s = base_settings()
    s.source_object = src
    s.use_collection_filter = True

    src_arm = addon._collection_search_armature(bpy.context, s, True)
    dst_arm = addon._collection_search_armature(bpy.context, s, False)
    check("ricerca sorgente sull'armatura sorgente",
          src_arm is src, src_arm)
    check("ricerca destinazione sull'armatura attiva",
          dst_arm is dst, dst_arm)
    check("helper prop_search disponibile su 5.x",
          addon._collection_search_available(dst) is True)
    check("helper prop_search assente senza armatura",
          addon._collection_search_available(None) is False)

    class _NoCollectionsData:
        pass

    class _FakeArm:
        type = 'ARMATURE'
        data = _NoCollectionsData()

    check("fallback: armatura senza API collections",
          addon._collection_search_available(_FakeArm()) is False)

    record = draw_panel(addon.ACTD_PT_advanced, bpy.context)
    ricerche = [r for r in record if r[0] == "prop_search"]
    check("prop_search usato per entrambe le collection",
          [r[1] for r in ricerche]
          == ["collection_source", "collection_dest"],
          [r[1] for r in ricerche])
    check("la ricerca punta a Armature.collections",
          all(r[2] == "collections" for r in ricerche),
          [r[2] for r in ricerche])

    s.source_object = None
    dst_arm = addon._collection_search_armature(bpy.context, s, True)
    check("senza armatura sorgente si usa la destinazione",
          dst_arm is dst, dst_arm)

    # Proprietà e ID invariati: restano StringProperty.
    props = addon.ACTD_Settings.bl_rna.properties
    check("collection_source resta una StringProperty",
          props["collection_source"].type == 'STRING',
          props["collection_source"].type)
    check("collection_dest resta una StringProperty",
          props["collection_dest"].type == 'STRING',
          props["collection_dest"].type)

    # Fallback esplicito: armatura mancante/non valida -> campo testo.
    mesh = bpy.data.meshes.new("FallbackMesh")
    mesh_obj = bpy.data.objects.new("FallbackMesh", mesh)
    bpy.context.scene.collection.objects.link(mesh_obj)
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    record = draw_panel(addon.ACTD_PT_advanced, bpy.context)
    campi = [r[1] for r in record if r[0] == "prop"]
    check("fallback al campo testo senza armatura valida",
          "collection_source" in campi and "collection_dest" in campi,
          campi)
    check("nessun prop_search nel fallback",
          not any(r[0] == "prop_search" for r in record), record[:8])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[14] Icone semantiche valide e non duplicate", flush=True)
try:
    # Icone realmente disponibili nella build Blender in uso.
    icon_items = bpy.types.UILayout.bl_rna.functions["label"].parameters[
        "icon"
    ].enum_items
    valid_icons = {item.identifier for item in icon_items}
    record_main = draw_panel(addon.ACTD_PT_main, bpy.context)
    record_diag = draw_panel(addon.ACTD_PT_diagnostics, bpy.context)
    record_maint = draw_panel(addon.ACTD_PT_maintenance, bpy.context)

    guess = [
        r for r in record_main
        if r[0] == "operator" and r[1] == "actd.guess_prefixes"
    ]
    check("Guess prefixes non usa più SORTALPHA",
          guess and guess[0][3] != 'SORTALPHA', guess)
    check("icona Guess prefixes valida",
          guess and guess[0][3] in valid_icons, guess)

    diagnose = [
        r for r in record_diag
        if r[0] == "operator" and r[1] == "actd.diagnose"
    ]
    check("Rig check usa un'icona di verifica valida",
          diagnose and diagnose[0][3] == 'CHECKMARK'
          and 'CHECKMARK' in valid_icons, diagnose)

    export_icons = {
        r[1]: r[3] for r in record_maint
        if r[0] == "operator" and r[1] in ("actd.export_csv", "actd.export_json")
    }
    check("export CSV/JSON con icona di export valida",
          export_icons == {"actd.export_csv": 'EXPORT',
                           "actd.export_json": 'EXPORT'}
          and 'EXPORT' in valid_icons, export_icons)

    used = set()
    for panel_record in (record_main, record_diag, record_maint):
        for entry in panel_record:
            if entry[0] == "label" and len(entry) >= 3:
                used.add(entry[2])
            elif entry[0] == "operator" and len(entry) >= 4:
                used.add(entry[3])
    used.discard('NONE')
    used.discard(None)
    check("tutte le icone usate esistono in Blender",
          used <= valid_icons, used - valid_icons)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[15] _strip_token rimuove il token dal nome", flush=True)
try:
    # Prefisso: "DEF_" sparisce e resta il solo nome base.
    base = addon._strip_token("DEF_Spine", "DEF_", 'PREFIX')
    check("_strip_token rimuove il prefisso DEF_",
          base == "Spine", base)
    # Suffisso: comportamento speculare, invariato.
    base = addon._strip_token("Spine_ctrl", "_ctrl", 'SUFFIX')
    check("_strip_token rimuove il suffisso _ctrl",
          base == "Spine", base)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
def add_manual_copy(arm, owner="MCH-a", source="DEF-a"):
    """Aggiunge un COPY_TRANSFORMS manuale (fuori dal registro dei generati)."""
    pb = arm.pose.bones[owner]
    con = pb.constraints.new('COPY_TRANSFORMS')
    con.name = "MANUALE_COPY"
    con.target = arm
    con.subtarget = source
    return con


def count_copy(arm, bone_name):
    """Conta i COPY_TRANSFORMS presenti su un osso (0 se l'osso non esiste)."""
    pb = arm.pose.bones.get(bone_name)
    if pb is None:
        return 0
    return sum(1 for con in pb.constraints if con.type == 'COPY_TRANSFORMS')


class _FakeApp:
    """Sostituto minimale di ``bpy.app`` per simulare lo stato non headless."""

    def __init__(self, real, background):
        self._real = real
        self.background = background

    def __getattr__(self, name):
        return getattr(self._real, name)


class _FakeBpy:
    """Proxy di ``bpy`` con il solo ``app`` sostituito (guardie REPLACE)."""

    def __init__(self, real, background):
        self._real = real
        self.app = _FakeApp(real.app, background)

    def __getattr__(self, name):
        return getattr(self._real, name)


# ---------------------------------------------------------------------------
print("\n[16] REPLACE con soli generati: nessun popup, comportamento storico",
      flush=True)
try:
    reset_scene()
    arm = make_rig("Rig16")
    s = base_settings()
    bpy.ops.actd.apply_transforms()          # KEEP: crea i due generati
    s.existing_mode = 'REPLACE'
    # In headless ASK vale ALL e non c'e' popup: con zero manuali si va
    # dritti a execute, quindi l'invoke completa senza finestra.
    res = bpy.ops.actd.apply_transforms('INVOKE_DEFAULT')
    check("REPLACE con soli generati completa senza popup",
          res == {'FINISHED'}, res)
    check("sostituiti i due generati come prima",
          "Constraint sostituiti (rimossi): 2" in s.last_report,
          s.last_report.replace("\n", " / "))
    stato = []
    for pb in arm.pose.bones:
        for con in pb.constraints:
            if con.type == 'COPY_TRANSFORMS':
                stato.append(addon._is_generated(arm, pb, con))
    check("due generati ricreati, nessun manuale",
          len(stato) == 2 and all(stato), stato)
    check("registro con due voci", len(addon._read_registry(arm)) == 2,
          addon._read_registry(arm))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[17] Conteggi REPLACE via _count_replace_targets", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig17")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    add_manual_copy(arm, "MCH-a", "DEF-a")
    add_manual(arm)                          # COPY_ROTATION: tipo diverso
    results = addon.compute_mapping(arm, s)
    generati, manuali = addon._count_replace_targets(
        arm, results, None, 'COPY_TRANSFORMS'
    )
    check("conteggio generati/manuali (2,1)",
          (generati, manuali) == (2, 1), (generati, manuali))
    generati_sel, manuali_sel = addon._count_replace_targets(
        arm, results, {"MCH-a"}, 'COPY_TRANSFORMS'
    )
    check("conteggio filtrato per osso (1,1)",
          (generati_sel, manuali_sel) == (1, 1),
          (generati_sel, manuali_sel))
    zero = addon._count_replace_targets(
        arm, results, {"MCH-manual"}, 'COPY_TRANSFORMS'
    )
    check("osso senza mappatura non conteggiato (0,0)", zero == (0, 0), zero)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[18] replace_scelta GENERATED_ONLY preserva i manuali", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig18")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    manuale = add_manual_copy(arm, "MCH-a", "DEF-a")
    nome_manuale = manuale.name
    s.existing_mode = 'REPLACE'
    res = bpy.ops.actd.apply_transforms(replace_scelta='GENERATED_ONLY')
    check("GENERATED_ONLY FINISHED", res == {'FINISHED'}, res)
    pba = arm.pose.bones["MCH-a"]
    check("il manuale resta sull'osso destinazione",
          len(pba.constraints) == 1
          and pba.constraints.get(nome_manuale) is not None
          and not addon._is_generated(arm, pba, pba.constraints[0]),
          [(c.name, c.type) for c in pba.constraints])
    pbb = arm.pose.bones["MCH-b"]
    check("il generato su MCH-b viene ricreato",
          len(pbb.constraints) == 1
          and addon._is_generated(arm, pbb, pbb.constraints[0]),
          [(c.name, c.type) for c in pbb.constraints])
    duplicati = [pb.name for pb in arm.pose.bones if count_copy(arm, pb.name) > 1]
    check("nessun constraint duplicato", duplicati == [], duplicati)
    check("report: 2 rimossi e 1 saltato",
          "Constraint sostituiti (rimossi): 2" in s.last_report
          and "Constraint saltati: 1" in s.last_report,
          s.last_report.replace("\n", " / "))
    check("avviso di manuale conservato",
          "constraint manuale conservato" in s.last_report,
          s.last_report.replace("\n", " / "))
    reg = addon._read_registry(arm)
    check("registro senza generati per il manuale",
          not reg.get("MCH-a") and len(reg.get("MCH-b", {})) == 1, reg)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[19] replace_scelta ALL senza conferma: rifiuto fuori background",
      flush=True)
try:
    reset_scene()
    arm = make_rig("Rig19")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    add_manual_copy(arm, "MCH-a", "DEF-a")
    s.existing_mode = 'REPLACE'
    s.replace_conferma_manuali = False
    # Il rifiuto vale solo fuori background: il ramo execute passa il
    # background reale, quindi in headless il caso si prova sulla funzione
    # pura, che dipende solo da checkbox e background.
    ok_false = addon._replace_conferma_ok(s, 'ALL', False)
    check("ALL senza conferma rifiutato fuori background",
          ok_false is False, ok_false)
    s.replace_conferma_manuali = True
    ok_true = addon._replace_conferma_ok(s, 'ALL', True)
    check("ALL con conferma ammesso con checkbox attiva",
          ok_true is True, ok_true)
    # La stessa scelta in background resta permessa: qui il background e'
    # quello reale del test headless, quindi si controlla la chiamata vera.
    s.replace_conferma_manuali = False
    res = bpy.ops.actd.apply_transforms(replace_scelta='ALL')
    check("in background la stessa chiamata resta permessa",
          res == {'FINISHED'}, res)
    totale = sum(len(pb.constraints) for pb in arm.pose.bones)
    check("bypass headless: manuale rimosso e due generati ricreati",
          totale == 2 and len(addon._read_registry(arm)) == 2,
          (totale, addon._read_registry(arm)))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[20] replace_scelta ALL con conferma: rimuove anche i manuali",
      flush=True)
try:
    reset_scene()
    arm = make_rig("Rig20")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    manuale = add_manual_copy(arm, "MCH-a", "DEF-a")
    nome_manuale = manuale.name
    s.existing_mode = 'REPLACE'
    s.replace_conferma_manuali = True
    bpy_reale = addon.bpy
    try:
        addon.bpy = _FakeBpy(bpy_reale, False)
        res = bpy.ops.actd.apply_transforms(replace_scelta='ALL')
    finally:
        addon.bpy = bpy_reale
    check("ALL con conferma eseguito", res == {'FINISHED'}, res)
    check("report: 3 constraint rimossi",
          "Constraint sostituiti (rimossi): 3" in s.last_report,
          s.last_report.replace("\n", " / "))
    pba = arm.pose.bones["MCH-a"]
    check("il manuale è stato rimosso",
          pba.constraints.get(nome_manuale) is None,
          [c.name for c in pba.constraints])
    totale = sum(len(pb.constraints) for pb in arm.pose.bones)
    check("restano i soli due generati", totale == 2, totale)
    check("registro riallineato a due voci",
          len(addon._read_registry(arm)) == 2, addon._read_registry(arm))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[21] replace_conferma_manuali: default e tipo", flush=True)
try:
    s = base_settings()
    s.replace_conferma_manuali = False
    prop = s.bl_rna.properties.get("replace_conferma_manuali")
    check("proprietà replace_conferma_manuali è booleana",
          prop is not None and prop.type == 'BOOLEAN',
          getattr(prop, "type", None))
    check("default False", prop is not None and prop.default is False,
          getattr(prop, "default", None))
    enum = bpy.ops.actd.apply_transforms.get_rna_type().properties.get(
        "replace_scelta"
    )
    voci = [item.identifier for item in enum.enum_items] if enum else []
    check("replace_scelta con quattro scelte e default ASK",
          voci == ['ASK', 'CANCEL', 'GENERATED_ONLY', 'ALL']
          and enum.default == 'ASK',
          (voci, getattr(enum, "default", None)))
    check("replace_scelta non salvata nel file (SKIP_SAVE)",
          enum is not None and enum.is_skip_save is True,
          getattr(enum, "is_skip_save", None))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
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


print("\n[22] REPLACE con rimozione: backup JSON per GENERATED_ONLY e ALL",
      flush=True)
creati_22 = []
try:
    for suffisso, scelta, conferma in (
        ("gen", 'GENERATED_ONLY', False),
        ("all", 'ALL', True),
    ):
        reset_scene()
        arm = make_rig("Rig22" + suffisso)
        s = base_settings()
        bpy.ops.actd.apply_transforms()
        add_manual_copy(arm, "MCH-a", "DEF-a")
        s.existing_mode = 'REPLACE'
        s.replace_conferma_manuali = conferma
        res = bpy.ops.actd.apply_transforms(replace_scelta=scelta)
        path = backup_path(s.preview_report)
        creati_22.append(path)
        check("sostituzione con backup creata (" + scelta + ")",
              res == {'FINISHED'} and os.path.isfile(path), (res, path))
        check("nome backup con armatura e data (" + scelta + ")",
              re.match(
                  r"^actd_replace_backup_%s_\d{8}-\d{6}-\d{6}\.json$"
                  % re.escape(arm.name),
                  os.path.basename(path) or "",
              ) is not None,
              os.path.basename(path))
        payload = load_backup(path)
        righe = payload.get("righe", [])
        check("backup leggibile con json.load (" + scelta + ")",
              isinstance(righe, list) and bool(righe)
              and isinstance(payload.get("generato_il"), str),
              (payload.get("generato_il"), righe))
        # Lo schema e' quello di actd.export_json: il nome del constraint e'
        # nel campo "constraint", accanto al flag "generato" e al timestamp.
        check("righe backup con i campi dello schema (" + scelta + ")",
              bool(righe) and all(
                  set(addon._EXPORT_FIELDS) <= set(r.keys())
                  and {"armatura", "osso", "constraint", "generato",
                       "timestamp"} <= set(r.keys())
                  and r["armatura"] == arm.name
                  and isinstance(r["osso"], str) and bool(r["osso"])
                  and isinstance(r["constraint"], str) and bool(r["constraint"])
                  and isinstance(r["generato"], bool)
                  for r in righe
              ),
              righe[:2])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    for _path in creati_22:
        if _path and os.path.isfile(_path):
            os.remove(_path)

# ---------------------------------------------------------------------------
print("\n[23] Backup GENERATED_ONLY: solo i generati rimossi", flush=True)
path_23 = ""
try:
    reset_scene()
    arm = make_rig("Rig23")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    manuale = add_manual_copy(arm, "MCH-a", "DEF-a")
    nome_manuale = manuale.name
    s.existing_mode = 'REPLACE'
    res = bpy.ops.actd.apply_transforms(replace_scelta='GENERATED_ONLY')
    path_23 = backup_path(s.preview_report)
    righe = load_backup(path_23).get("righe", [])
    check("GENERATED_ONLY con backup creato",
          res == {'FINISHED'} and os.path.isfile(path_23), (res, path_23))
    check("backup con i due soli generati", len(righe) == 2, righe)
    check("tutte le righe backup sono generati",
          bool(righe) and all(r.get("generato") is True for r in righe),
          [r.get("generato") for r in righe])
    check("backup sulle ossa dei generati rimossi",
          sorted(r.get("osso", "") for r in righe) == ["MCH-a", "MCH-b"],
          [r.get("osso") for r in righe])
    check("il manuale non entra nel backup",
          bool(righe)
          and all(r.get("constraint") != nome_manuale for r in righe),
          [r.get("constraint") for r in righe])
    check("il manuale resta sull'armatura",
          arm.pose.bones["MCH-a"].constraints.get(nome_manuale) is not None,
          [c.name for c in arm.pose.bones["MCH-a"].constraints])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    if path_23 and os.path.isfile(path_23):
        os.remove(path_23)

# ---------------------------------------------------------------------------
print("\n[24] Backup ALL con conferma: generati e manuali", flush=True)
path_24 = ""
try:
    reset_scene()
    arm = make_rig("Rig24")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    manuale = add_manual_copy(arm, "MCH-a", "DEF-a")
    nome_manuale = manuale.name
    s.existing_mode = 'REPLACE'
    s.replace_conferma_manuali = True
    bpy_reale = addon.bpy
    try:
        addon.bpy = _FakeBpy(bpy_reale, False)
        res = bpy.ops.actd.apply_transforms(replace_scelta='ALL')
    finally:
        addon.bpy = bpy_reale
    path_24 = backup_path(s.preview_report)
    righe = load_backup(path_24).get("righe", [])
    check("ALL con conferma e backup creato",
          res == {'FINISHED'} and os.path.isfile(path_24), (res, path_24))
    check("backup con tre righe", len(righe) == 3, righe)
    check("il manuale rimosso e' nel backup",
          nome_manuale in [r.get("constraint") for r in righe],
          [r.get("constraint") for r in righe])
    generati = [r for r in righe if r.get("generato") is True]
    manuali = [r for r in righe if r.get("generato") is False]
    check("backup con due generati e un manuale",
          (len(generati), len(manuali)) == (2, 1),
          (len(generati), len(manuali)))
    check("riga del manuale sull'osso giusto",
          bool(manuali) and manuali[0].get("osso") == "MCH-a", manuali)
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    if path_24 and os.path.isfile(path_24):
        os.remove(path_24)

# ---------------------------------------------------------------------------
print("\n[25] Scrittura backup fallita: sostituzione annullata", flush=True)
try:
    reset_scene()
    arm = make_rig("Rig25")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    add_manual_copy(arm, "MCH-a", "DEF-a")
    prima = sum(len(pb.constraints) for pb in arm.pose.bones)
    s.existing_mode = 'REPLACE'
    s.replace_conferma_manuali = True

    def _backup_rotto(arm_obj, rows):
        """Simula una cartella di backup non scrivibile."""
        raise OSError("scrittura non permessa (test)")

    # Nel pacchetto _write_replace_backup vive nel modulo actd_operators: patchiare
    # il solo namespace del pacchetto non ha effetto sul codice eseguito.
    ops_mod = sys.modules["auto_copy_transforms_def.actd_operators"]
    reale = ops_mod._write_replace_backup
    try:
        ops_mod._write_replace_backup = _backup_rotto
        res = bpy.ops.actd.apply_transforms(replace_scelta='ALL')
    finally:
        ops_mod._write_replace_backup = reale
    dopo = sum(len(pb.constraints) for pb in arm.pose.bones)
    check("backup fallito: operatore CANCELLED", res == {'CANCELLED'}, res)
    check("backup fallito: nessun constraint rimosso", dopo == prima,
          (prima, dopo))
    check("backup fallito: registro invariato",
          len(addon._read_registry(arm)) == 2, addon._read_registry(arm))
    check("report con la riga 'Backup non riuscito'",
          "Backup non riuscito: sostituzione annullata" in s.preview_report,
          s.preview_report.replace("\n", " / "))
    check("last_report riporta la stessa riga",
          s.last_report == s.preview_report,
          s.last_report.replace("\n", " / "))
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------------------
print("\n[26] Report finale con la riga 'Backup creato:'", flush=True)
path_26 = ""
try:
    reset_scene()
    arm = make_rig("Rig26")
    s = base_settings()
    bpy.ops.actd.apply_transforms()
    s.existing_mode = 'REPLACE'
    res = bpy.ops.actd.apply_transforms(replace_scelta='GENERATED_ONLY')
    path_26 = backup_path(s.preview_report)
    check("sostituzione riuscita con backup",
          res == {'FINISHED'} and os.path.isfile(path_26), (res, path_26))
    check("riga Backup creato: nel report finale",
          bool(path_26) and ("Backup creato: " + path_26) in s.preview_report,
          s.preview_report.replace("\n", " / "))
    check("la riga del backup chiude il report",
          bool(path_26)
          and s.preview_report.splitlines()[-1] == "Backup creato: " + path_26,
          s.preview_report.splitlines()[-1:])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    if path_26 and os.path.isfile(path_26):
        os.remove(path_26)

# ---------------------------------------------------------------------------
print("\n===== RIEPILOGO TEST MODULO 6 =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)