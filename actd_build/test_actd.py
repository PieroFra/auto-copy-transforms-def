# -*- coding: utf-8 -*-
"""
Test headless per l'addon "Auto Copy Transforms DEF".

Esecuzione:
    blender.exe --background --factory-startup --python test_actd.py
"""

import importlib.util
import os
import re
import sys
import traceback

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
# Il monolite non esiste piu': l'artefatto e' il pacchetto generato dalla build.
ADDON_PATH = os.path.join(HERE, "auto_copy_transforms_def")
ADDON_INIT = os.path.join(ADDON_PATH, "__init__.py")

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print("[{}] {}{}".format("PASS" if cond else "FAIL", name,
                             (" | " + detail) if detail else ""), flush=True)


def _txt(value):
    """Confronti indipendenti dalla codifica: Blender puo' restituire bytes."""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)


def load_addon():
    # Il pacchetto usa import relativi: la location secondaria dichiara la cartella.
    spec = importlib.util.spec_from_file_location(
        "auto_copy_transforms_def", ADDON_INIT,
        submodule_search_locations=[ADDON_PATH])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["auto_copy_transforms_def"] = mod
    spec.loader.exec_module(mod)
    mod.register()
    return mod


def make_armature(name, bone_names):
    """Crea un'armatura con le ossa date (nome -> posizione tail) e la attiva."""
    arm_data = bpy.data.armatures.new(name + "_data")
    obj = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.object.mode_set(mode='EDIT')
    for i, bname in enumerate(bone_names):
        eb = arm_data.edit_bones.new(bname)
        eb.head = (0.0, float(i), 0.0)
        eb.tail = (0.0, float(i) + 1.0, 0.0)
    bpy.ops.object.mode_set(mode='POSE')
    return obj


def counts(settings):
    rep = settings.last_report
    out = {}
    for key, label in (
        ("created", "Constraint creati"),
        ("updated", "Constraint aggiornati"),
        ("skipped", "Constraint saltati"),
        ("replaced", "Constraint sostituiti \\(rimossi\\)"),
    ):
        m = re.search(label + r": (\d+)", rep)
        out[key] = int(m.group(1)) if m else None
    out["report"] = rep
    return out


def reset_settings(s):
    """Riporta le impostazioni ai default della 1.1.0 e pulisce registro/collezioni.

    Il vecchio sistema di override e la collezione audit non esistono piu':
    al loro posto ci sono il registro JSON sull'armatura e diagnostic_items.
    """
    valori = {
        "source_object": None,
        "mix_mode": 'REPLACE',
        "use_offset": False,
        "remove_target_shear": False,
        "stack_position": 'BOTTOM',
        "constraint_type": 'COPY_TRANSFORMS',
        "source_token": "DEF-",
        "dest_token": "MCH-",
        "source_token_type": 'PREFIX',
        "dest_token_type": 'PREFIX',
        "custom_pattern": "",
        "use_regex": False,
        "apply_mode": 'ALL',
        "use_collection_filter": False,
        "collection_source": "",
        "collection_dest": "",
        "deform_only": False,
        "influence": 1.0,
        "target_space": 'WORLD',
        "owner_space": 'WORLD',
        "existing_mode": 'KEEP',
        "update_mode": 'MISSING_ONLY',
        "avoid_duplicates": True,
        "resolve_ambiguous": False,
        "constraint_name": mod.DEFAULT_CONSTRAINT_NAME,
        "preview_index": 0,
        "preview_armature": "",
        "last_report": "",
        "preview_is_stale": True,
        "diagnostic_is_stale": True,
    }
    for nome, valore in valori.items():
        if hasattr(s, nome):
            setattr(s, nome, valore)
    # Collezioni della 1.1.x (sostituiscono override e audit_items).
    mod._clear_collection(s.preview_items)
    mod._clear_collection(s.diagnostic_items)
    # Il registro JSON sostituisce gli override: va azzerato su ogni armatura.
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            mod._write_registry(obj, {})


def clear_scene():
    print("--- clear_scene: inizio ---", flush=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for arm in list(bpy.data.armatures):
        bpy.data.armatures.remove(arm)
    print("--- clear_scene: fine ---", flush=True)


def add_manual_ct(pose_bone, arm_obj, subtarget, target_space='WORLD',
                  owner_space='WORLD', influence=1.0):
    con = pose_bone.constraints.new('COPY_TRANSFORMS')
    con.target = arm_obj
    con.subtarget = subtarget
    con.target_space = target_space
    con.owner_space = owner_space
    con.influence = influence
    return con


# =============================================================================
#  CARICAMENTO ADDON
# =============================================================================
mod = load_addon()
scene = bpy.context.scene
S = scene.actd_settings
print("--- addon caricato ---", flush=True)

check("register() ok e proprietà Scene presente", hasattr(scene, "actd_settings"))
check("operatori registrati",
      all(hasattr(bpy.ops.actd, n) for n in
          ("dest_preset", "refresh_constraint_name", "guess_prefixes",
           "learn_pattern", "preview", "apply_transforms",
           "remove_generated", "convert_to_manual", "mute_all",
           "export_csv", "export_json", "show_info")))
check("autore, descrizione inglese e nessun riferimento Discord",
      mod.bl_info.get("author") == "Pierfrancesco Diodato"
      and mod.bl_info.get("description", "").startswith(
          "Automatically creates Copy Transforms")
      and not hasattr(mod, "DISCORD_URL")
      and not hasattr(mod, "DISCORD_ID"),
      mod.bl_info.get("author"))
check("README e licenza incorporati",
      bool(mod.README_TEXT.strip()) and bool(mod.LICENSE_NOTICE.strip())
      and mod.LICENSE_NAME == "GPL-3.0-or-later")

# Default v1.1.x: token con underscore, non con trattino.
check("default token sorgente MCH_", S.source_token == "MCH_", S.source_token)
check("default token destinazione DEF_", S.dest_token == "DEF_", S.dest_token)
clear_scene()
arm_default = make_armature("ArmDefault", ["DEF_Hand.L", "MCH_Hand.L"])
bpy.ops.actd.apply_transforms()
check("default: owner DEF_ e target MCH_",
      len(arm_default.pose.bones["DEF_Hand.L"].constraints) == 1
      and arm_default.pose.bones["DEF_Hand.L"].constraints[0].subtarget
      == "MCH_Hand.L",
      str([c.subtarget
           for c in arm_default.pose.bones["DEF_Hand.L"].constraints]))
reset_settings(S)

# =============================================================================
#  T1 - Comportamento di default invariato
# =============================================================================
clear_scene()
arm = make_armature("Arm1", [
    "DEF-Hand.L", "DEF-Hand.R", "DEF-Spine",
    "MCH-Hand.L", "MCH-Hand.R", "MCH-Spine",
])
reset_settings(S)

check("T1 preview: flag stale azzerato dopo anteprima", True)
S.preview_is_stale = True
res = bpy.ops.actd.preview()
c = counts(S)
check("T1 preview FINISHED", res == {'FINISHED'}, str(res))
check("T1 preview: 3 coppie valide", c["report"].count("Coppie valide: 3") == 1,
      c["report"].replace("\n", " / "))
check("T1 preview_is_stale azzerato", S.preview_is_stale is False)

res = bpy.ops.actd.apply_transforms()
c = counts(S)
check("T1 apply FINISHED", res == {'FINISHED'}, str(res))
check("T1 default: 3 constraint creati", c["created"] == 3, c["report"].replace("\n", " / "))
pb = arm.pose.bones["MCH-Hand.L"]
check("T1 default: 1 constraint sull'osso", len(pb.constraints) == 1)
check("T1 default: nome constraint invariato (AUTO_COPY_DEF_to_MCH)",
      pb.constraints[0].name == "AUTO_COPY_DEF_to_MCH", pb.constraints[0].name)
check("T1 default: marcatore actd_generated",
      mod._is_generated(arm, pb, pb.constraints[0]) is True)
check("T1 default: subtarget corretto", pb.constraints[0].subtarget == "DEF-Hand.L")

# re-apply con MISSING_ONLY => nessun nuovo constraint
res = bpy.ops.actd.apply_transforms()
c = counts(S)
check("T1 re-apply: 0 creati, 3 saltati", c["created"] == 0 and c["skipped"] == 3,
      c["report"].replace("\n", " / "))

# =============================================================================
#  T2 - REPLACE raggiungibile anche con avoid_duplicates=True
# =============================================================================
clear_scene()
arm = make_armature("Arm2", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
add_manual_ct(arm.pose.bones["MCH-Hand.L"], arm, "DEF-Hand.L")
add_manual_ct(arm.pose.bones["MCH-Hand.L"], arm, "DEF-Altro")
S.existing_mode = 'REPLACE'

res = bpy.ops.actd.apply_transforms()
c = counts(S)
pb = arm.pose.bones["MCH-Hand.L"]
check("T2 apply FINISHED", res == {'FINISHED'}, str(res))
check("T2 REPLACE eseguito: 1 creato", c["created"] == 1, c["report"].replace("\n", " / "))
check("T2 REPLACE: 2 rimossi (replaced)", c["replaced"] == 2, c["report"].replace("\n", " / "))
check("T2 REPLACE: 0 saltati (nessun duplicato contato)", c["skipped"] == 0,
      c["report"].replace("\n", " / "))
check("T2 REPLACE: 1 solo constraint residuo", len(pb.constraints) == 1,
      str(len(pb.constraints)))
check("T2 REPLACE: constraint è quello generato",
      mod._is_generated(arm, pb, pb.constraints[0]) is True)

# =============================================================================
#  T3 - UPDATE non sovrascrive i constraint manuali
# =============================================================================
clear_scene()
arm = make_armature("Arm3", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
manual = add_manual_ct(arm.pose.bones["MCH-Hand.L"], arm, "DEF-Hand.L")
manual.name = "MIO_MANUALE"
S.update_mode = 'UPDATE'

res = bpy.ops.actd.apply_transforms()
c = counts(S)
pb = arm.pose.bones["MCH-Hand.L"]
check("T3 apply FINISHED", res == {'FINISHED'}, str(res))
check("T3 UPDATE su manuale: 0 creati, 1 saltato", c["created"] == 0 and c["skipped"] == 1,
      c["report"].replace("\n", " / "))
check("T3 constraint manuale intatto", len(pb.constraints) == 1
      and pb.constraints[0].name == "MIO_MANUALE"
      and mod._is_generated(arm, pb, pb.constraints[0]) is False)
check("T3 avviso 'constraint manuale' nel report",
      "constraint manuale" in c["report"], c["report"].replace("\n", " / "))

# =============================================================================
#  T4 - _find_matching_copy non è più permissivo
# =============================================================================
clear_scene()
arm = make_armature("Arm4", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
# stesso target/subtarget ma owner_space diverso => NON è un duplicato
add_manual_ct(arm.pose.bones["MCH-Hand.L"], arm, "DEF-Hand.L",
              target_space='WORLD', owner_space='LOCAL')

res = bpy.ops.actd.apply_transforms()
c = counts(S)
pb = arm.pose.bones["MCH-Hand.L"]
check("T4 spazi diversi: nuovo constraint creato", c["created"] == 1,
      c["report"].replace("\n", " / "))
check("T4 ora 2 constraint sull'osso", len(pb.constraints) == 2, str(len(pb.constraints)))

# influenza diversa => non duplicato
clear_scene()
arm = make_armature("Arm4b", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
add_manual_ct(arm.pose.bones["MCH-Hand.L"], arm, "DEF-Hand.L", influence=0.5)
bpy.ops.actd.apply_transforms()
c = counts(S)
check("T4 influenza diversa: nuovo constraint creato", c["created"] == 1,
      c["report"].replace("\n", " / "))

# identico => duplicato, saltato
clear_scene()
arm = make_armature("Arm4c", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
add_manual_ct(arm.pose.bones["MCH-Hand.L"], arm, "DEF-Hand.L")
bpy.ops.actd.apply_transforms()
c = counts(S)
check("T4 identico: riconosciuto come duplicato e saltato",
      c["created"] == 0 and c["skipped"] == 1, c["report"].replace("\n", " / "))

# =============================================================================
#  T5 - Constraint generati duplicati: pulizia + avviso
# =============================================================================
clear_scene()
arm = make_armature("Arm5", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
pb = arm.pose.bones["MCH-Hand.L"]
for i in range(3):
    con = add_manual_ct(pb, arm, "DEF-Hand.L")
    con.name = "GEN%d" % i
    mod._mark_generated(arm, pb, con, arm, "DEF-Hand.L")

res = bpy.ops.actd.apply_transforms()
c = counts(S)
check("T5 apply FINISHED", res == {'FINISHED'}, str(res))
check("T5 duplicati generati ripuliti: resta 1 constraint",
      len(pb.constraints) == 1, str(len(pb.constraints)))
check("T5 avviso duplicati generati nel report",
      "constraint generati duplicati" in c["report"], c["report"].replace("\n", " / "))

# =============================================================================
#  T6 - Conflitto simmetrico: più sorgenti -> stessa destinazione
# =============================================================================
clear_scene()
arm = make_armature("Arm6", ["DEF-Hand.L", "DEF-Hand_L", "MCH-Hand"])
reset_settings(S)
S.resolve_ambiguous = True  # anche risolvendo, il conflitto deve emergere
res = bpy.ops.actd.preview()
items = [(i.source_name, i.dest_name, i.status, i.note)
         for i in S.preview_items]
contese = [i for i in items
           if i[0] in ("DEF-Hand.L", "DEF-Hand_L")]
check("T6 entrambe le coppie verso MCH-Hand esistono",
      len(contese) == 2, str(items))
check("T6 entrambe marcate 'ambiguous' e destinazione azzerata",
      all(i[2] == 'ambiguous' and i[1] == "" for i in contese), str(contese))
check("T6 nota 'contesa' presente",
      any("contesa" in i[3] for i in contese), str(contese))

res = bpy.ops.actd.apply_transforms()
c = counts(S)
check("T6 nessun constraint creato su destinazione contesa", c["created"] == 0,
      c["report"].replace("\n", " / "))

# =============================================================================
#  T7 - Validazione template / regex
# =============================================================================
check("T7 template con due {name} rifiutato",
      mod._build_template_regex("{name}{name}", "DEF-") is None)
check("T7 template con due {side} rifiutato",
      mod._build_template_regex("{name}{side}{side}", "DEF-") is None)
check("T7 template senza {name} rifiutato",
      mod._build_template_regex("{token}{side}", "DEF-") is None)
check("T7 template valido accettato",
      mod._build_template_regex("{token}{name}{side}", "DEF-") is not None)

S.custom_pattern = "{name}{name}"
S.use_regex = False
check("T7 _validate_pattern segnala doppio {name}", mod._validate_pattern(S) != "")
S.custom_pattern = "{name}{side}{side}"
check("T7 _validate_pattern segnala doppio {side}", mod._validate_pattern(S) != "")
S.custom_pattern = "["
S.use_regex = True
check("T7 _validate_pattern segnala regex invalida", mod._validate_pattern(S) != "")
S.custom_pattern = ""
S.use_regex = False
check("T7 _validate_pattern vuoto => nessun warning", mod._validate_pattern(S) == "")

# =============================================================================
#  T8 - remove/apply con SELECTED e nessuna selezione
# =============================================================================
clear_scene()
arm = make_armature("Arm8", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
bpy.ops.actd.apply_transforms()
for pb in arm.pose.bones:
    pb.select = False
S.apply_mode = 'SELECTED'

res = bpy.ops.actd.remove_generated()
check("T8 remove senza selezione: CANCELLED", res == {'CANCELLED'}, str(res))
check("T8 nessun constraint rimosso",
      len(arm.pose.bones["MCH-Hand.L"].constraints) == 1)
res = bpy.ops.actd.apply_transforms()
check("T8 apply senza selezione: CANCELLED", res == {'CANCELLED'}, str(res))
check("T8 report di annullamento presente", "annullata" in S.last_report,
      S.last_report)

# con selezione funziona
arm.pose.bones["MCH-Hand.L"].select = True
check("T8 _is_pose_bone_selected compatibile con questa versione",
      mod._is_pose_bone_selected(arm.pose.bones["MCH-Hand.L"]) is True)
res = bpy.ops.actd.remove_generated()
check("T8 remove con selezione: FINISHED e 1 rimosso",
      res == {'FINISHED'} and len(arm.pose.bones["MCH-Hand.L"].constraints) == 0,
      str(res))

# =============================================================================
#  T9 - preview_is_stale
# =============================================================================
clear_scene()
arm = make_armature("Arm9", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
S.preview_is_stale = False
S.source_token = "DEF_"   # modifica parametro
check("T9 modifica token => preview_is_stale True", S.preview_is_stale is True)
bpy.ops.actd.preview()
check("T9 dopo preview => preview_is_stale False", S.preview_is_stale is False)
S.dest_token = "MCH_"
check("T9 modifica token dest => stale di nuovo", S.preview_is_stale is True)
bpy.ops.actd.apply_transforms()
check("T9 dopo apply => preview_is_stale False", S.preview_is_stale is False)

# =============================================================================
#  T10 - Nome constraint derivato dai token
# =============================================================================
clear_scene()
arm = make_armature("Arm10", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
bpy.ops.actd.refresh_constraint_name()
check("T10 nome suggerito da token di default",
      S.constraint_name == "AUTO_COPY_DEF_to_MCH", S.constraint_name)

reset_settings(S)
S.source_token = "DEF-"
S.dest_token = "ORG-"
bpy.ops.actd.refresh_constraint_name()
check("T10 nome aggiornato con token ORG-",
      S.constraint_name == "AUTO_COPY_DEF_to_ORG", S.constraint_name)

# applica con nome vuoto => deriva dai token
clear_scene()
arm = make_armature("Arm10b", ["DEF-Hand.L", "ORG-Hand.L"])
reset_settings(S)
S.dest_token = "ORG-"
S.constraint_name = ""
bpy.ops.actd.apply_transforms()
check("T10 nome vuoto => derivato dai token",
      arm.pose.bones["ORG-Hand.L"].constraints[0].name == "AUTO_COPY_DEF_to_ORG",
      arm.pose.bones["ORG-Hand.L"].constraints[0].name)

# preset destinazione con underscore (stile nomi osso)
reset_settings(S)
res = bpy.ops.actd.dest_preset(preset="ORG_", token_type="PREFIX")
check("T10 preset destinazione ORG_",
      res == {'FINISHED'} and S.dest_token == "ORG_", S.dest_token)

# =============================================================================
#  T11 - Nome constraint esplicito rispettato
# =============================================================================
clear_scene()
arm = make_armature("Arm11", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
S.constraint_name = "IL_MIO_NOME"
bpy.ops.actd.apply_transforms()
check("T11 nome esplicito rispettato",
      arm.pose.bones["MCH-Hand.L"].constraints[0].name == "IL_MIO_NOME",
      arm.pose.bones["MCH-Hand.L"].constraints[0].name)

# =============================================================================
#  T12 - register/unregister robusto (doppio ciclo)
# =============================================================================
ok = True
detail = ""
try:
    mod.unregister()
    mod.unregister()  # doppio: non deve lanciare
    check("T12 unregister() doppio senza errori", True)
except Exception as exc:
    ok = False
    detail = traceback.format_exc()
    check("T12 unregister() doppio senza errori", False, detail)
try:
    mod.register()  # re-registro per i test successivi
    S = bpy.context.scene.actd_settings  # nuova istanza dopo la re-registrazione
    check("T12 register() dopo unregister", hasattr(bpy.context.scene, "actd_settings"))
except Exception:
    check("T12 register() dopo unregister", False, traceback.format_exc())

try:
    mod.register()
    mod.register()  # doppio: ora è idempotente e non deve lanciare
    check("T12 register() doppio senza errori", True)
except Exception:
    check("T12 register() doppio senza errori", False, traceback.format_exc())

check("T12 Scene.actd_settings presente dopo doppio register",
      hasattr(bpy.types.Scene, "actd_settings"))

try:
    mod.unregister()
    mod.unregister()
    check("T12 ciclo register/unregister ripetuto pulito",
          not hasattr(bpy.types.Scene, "actd_settings"))
except Exception:
    check("T12 ciclo register/unregister ripetuto pulito", False, traceback.format_exc())

# =============================================================================
#  T13 - Rimozione constraint generati (T1 era stato applicato su Arm1)
# =============================================================================
mod.register()
print("T13: addon re-registrato", flush=True)
# [NOTA TEST] dopo unregister/register la vecchia istanza di PropertyGroup è
# orfana: va sempre ri-acquisita dalla Scene.
scene = bpy.context.scene
S = scene.actd_settings
check("T13 settings ri-acquisita dopo reload", S is not None)
clear_scene()
print("T13: scene pulita", flush=True)
arm = make_armature("Arm13", ["DEF-Hand.L", "MCH-Hand.L"])
print("T13: armatura creata", flush=True)
reset_settings(S)
print("T13: settings impostati", flush=True)
bpy.ops.actd.apply_transforms()
print("T13: apply eseguito", flush=True)
res = bpy.ops.actd.remove_generated()
check("T13 remove_generated FINISHED e 0 constraint",
      res == {'FINISHED'} and len(arm.pose.bones["MCH-Hand.L"].constraints) == 0,
      str(res))

# =============================================================================
#  T14 - Ambiguità e risoluzione automatica (sostituisce l'override manuale)
# =============================================================================
clear_scene()
arm = make_armature("Arm14", ["DEF-Hand", "MCH-Hand.L", "MCH-Hand.R"])
reset_settings(S)

res = bpy.ops.actd.preview()
righe = [(i.source_name, i.dest_name, i.status, i.note)
         for i in S.preview_items if i.source_name == "DEF-Hand"]
check("T14 preview FINISHED", res == {'FINISHED'}, str(res))
check("T14 due destinazioni => riga ambigua",
      len(righe) == 1 and righe[0][2] == 'ambiguous', str(righe))
check("T14 nota con i candidati",
      len(righe) == 1 and "Candidati" in righe[0][3], str(righe))
check("T14 nessun constraint creato in anteprima",
      sum(len(pb.constraints) for pb in arm.pose.bones) == 0)

S.resolve_ambiguous = True
bpy.ops.actd.preview()
righe = [(i.source_name, i.dest_name, i.status)
         for i in S.preview_items if i.source_name == "DEF-Hand"]
check("T14 resolve_ambiguous => status resolved",
      len(righe) == 1 and righe[0][2] == 'resolved', str(righe))
check("T14 candidato scelto: MCH-Hand.L",
      len(righe) == 1 and righe[0][1] == "MCH-Hand.L", str(righe))

res = bpy.ops.actd.apply_transforms()
c = counts(S)
check("T14 apply FINISHED", res == {'FINISHED'}, str(res))
check("T14 apply crea un solo constraint", c["created"] == 1,
      c["report"].replace("\n", " / "))
check("T14 constraint sul candidato scelto",
      len(arm.pose.bones["MCH-Hand.L"].constraints) == 1)
check("T14 nessun constraint sul candidato scartato",
      len(arm.pose.bones["MCH-Hand.R"].constraints) == 0)

# =============================================================================
#  T15 - Mapping non valido e regex errata
# =============================================================================
clear_scene()
arm = make_armature("Arm15", ["DEF-Hand.L", "MCH-Hand.L", "DEF-Foot.L"])
reset_settings(S)

# 1) Token sorgente inesistente: nessuna coppia valida
S.source_token = "ZZZ-"
results = mod.compute_mapping(arm, S)
check("T15 token inesistente: nessuna coppia valida",
      all(r.status not in ('match', 'resolved') for r in results),
      str([(r.source, r.dest, r.status) for r in results]))

res = bpy.ops.actd.apply_transforms()
c = counts(S)
check("T15 apply FINISHED", res == {'FINISHED'}, str(res))
check("T15 nessun constraint creato", c["created"] == 0,
      c["report"].replace("\n", " / "))
check("T15 report riporta ossa senza match",
      "Ossa sorgente senza match" in c["report"]
      and "Ossa destinazione senza match" in c["report"],
      c["report"].replace("\n", " / "))
check("T15 nessun constraint sull'armatura",
      sum(len(pb.constraints) for pb in arm.pose.bones) == 0)

# 2) Osso sorgente senza destinazione: riga unmatched_src
reset_settings(S)
results = mod.compute_mapping(arm, S)
stati_foot = [r.status for r in results if r.source == "DEF-Foot.L"]
check("T15 osso sorgente senza destinazione => unmatched_src",
      stati_foot == ['unmatched_src'], str(stati_foot))

# 3) Regex non valida: anteprima rifiutata e nessuna riga
reset_settings(S)
S.use_regex = True
S.custom_pattern = "("
mod._clear_collection(S.preview_items)
res = None
err_msg = ""
try:
    res = bpy.ops.actd.preview()
except RuntimeError as exc:
    err_msg = str(exc)

# bpy.ops solleva RuntimeError quando l'operatore fa report({'ERROR'}):
# il rifiuto e' corretto sia con CANCELLED sia con l'eccezione.
rifiutato = bool(err_msg) or (
    res is not None and "CANCELLED" in _txt(res).upper()
)
check("T15 regex non valida rifiutata",
      rifiutato and ("Regex non valida" in err_msg
                     or "Invalid regex" in err_msg),
      "res={!r} err={!r}".format(res, err_msg))
check("T15 regex non valida: nessuna riga in anteprima",
      len(S.preview_items) == 0, str(len(S.preview_items)))

# =============================================================================
#  T16 - Posizione nella pila dei constraint
# =============================================================================
clear_scene()
arm = make_armature("Arm16", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
pre = add_manual_ct(arm.pose.bones["MCH-Hand.L"], arm, "DEF-Hand.L")
pre.name = "PREESISTENTE"
S.avoid_duplicates = False
S.stack_position = 'TOP'
bpy.ops.actd.apply_transforms()
nomi = [c.name for c in arm.pose.bones["MCH-Hand.L"].constraints]
check("T16 stack_position TOP: nuovo constraint in cima",
      nomi == ["AUTO_COPY_DEF_to_MCH", "PREESISTENTE"], str(nomi))

clear_scene()
arm = make_armature("Arm16b", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
pre = add_manual_ct(arm.pose.bones["MCH-Hand.L"], arm, "DEF-Hand.L")
pre.name = "PREESISTENTE"
S.avoid_duplicates = False
S.stack_position = 'BOTTOM'
bpy.ops.actd.apply_transforms()
nomi = [c.name for c in arm.pose.bones["MCH-Hand.L"].constraints]
check("T16 stack_position BOTTOM: comportamento invariato",
      nomi == ["PREESISTENTE", "AUTO_COPY_DEF_to_MCH"], str(nomi))

# =============================================================================
#  T17 - Diagnostica pre-flight e pulizia del registro
# =============================================================================
clear_scene()
arm = make_armature("Arm17", ["DEF-Hand.L", "MCH-Hand.L"])
reset_settings(S)
bpy.ops.actd.apply_transforms()
pb = arm.pose.bones["MCH-Hand.L"]
generato = pb.constraints[0]
manuale = add_manual_ct(pb, arm, "DEF-Hand.L")
manuale.name = "MIO_MANUALE"
# Driver concorrente sulla destinazione: la diagnostica deve segnalarlo.
pb.driver_add("location", 0)

S.diagnostic_is_stale = True
res = bpy.ops.actd.diagnose()
items = list(S.diagnostic_items)
check("T17 diagnose FINISHED", res == {'FINISHED'}, str(res))
check("T17 diagnostic_items popolati", len(items) > 0, str(len(items)))
check("T17 livelli validi e testi non vuoti",
      all(i.level in ('error', 'warning', 'info') and i.text.strip()
          for i in items),
      str([(i.level, i.text) for i in items]))
check("T17 driver sulla destinazione segnalato",
      any("driver" in i.text.lower() for i in items),
      " | ".join(i.text for i in items))
check("T17 diagnostic_is_stale azzerato", S.diagnostic_is_stale is False)

# Voce orfana nel registro: il constraint e' sparito senza passare dall'addon.
reg = mod._read_registry(arm)
reg.setdefault("MCH-Hand.L", {})["FANTASMA"] = {
    "obj": arm.name,
    "bone": "DEF-Hand.L",
}
mod._write_registry(arm, reg)
prima = len(pb.constraints)

res = bpy.ops.actd.clean_registry()
reg_dopo = mod._read_registry(arm)
check("T17 clean_registry FINISHED", res == {'FINISHED'}, str(res))
check("T17 voce orfana rimossa dal registro",
      "FANTASMA" not in reg_dopo.get("MCH-Hand.L", {}),
      str(reg_dopo))
check("T17 constraint manuali e generati intatti",
      len(pb.constraints) == prima, str([c.name for c in pb.constraints]))
check("T17 voce del constraint generato conservata",
      generato.name in reg_dopo.get("MCH-Hand.L", {}), str(reg_dopo))

# =============================================================================
#  T18 - Coppie in anteprima (sostituisce highlight_pair)
# =============================================================================
clear_scene()
arm = make_armature(
    "Arm18", ["DEF-Hand.L", "MCH-Hand.L", "DEF-Foot.L", "MCH-Spine"]
)
reset_settings(S)
res = bpy.ops.actd.preview()
righe = {
    (_txt(i.source_name), _txt(i.dest_name)): _txt(i.status)
    for i in S.preview_items
}
check("T18 preview FINISHED", res == {'FINISHED'}, str(res))
check("T18 coppia attesa presente",
      righe.get(("DEF-Hand.L", "MCH-Hand.L")) == "match", str(righe))
check("T18 sorgente senza destinazione marcata unmatched_src",
      any(src == "DEF-Foot.L" and stato == "unmatched_src"
          for (src, _dst), stato in righe.items()), str(righe))
check("T18 destinazione senza sorgente marcata unmatched_dst",
      any(dst == "MCH-Spine" and stato == "unmatched_dst"
          for (_src, dst), stato in righe.items()), str(righe))

# =============================================================================
#  T19 / T20 - Rimossi dal legacy
# =============================================================================
# T19 (export report) e T20 (filtri UIList) non appartengono piu' alla 1.1.x:
# l'export CSV/JSON sara' implementato nel Modulo 6 (PASSO 5) e testato in
# test_mod6.py; la UIList attuale non espone filtri.

# =============================================================================
#  T21 - Guardia anti-ciclo in fase di apply
# =============================================================================
clear_scene()
arm = make_armature("Arm21", ["Solo"])
reset_settings(S)
S.source_token = ""
S.dest_token = ""
res = bpy.ops.actd.apply_transforms()
c = counts(S)
results = mod.compute_mapping(arm, S)
check("T21 self-loop escluso dalla mappatura",
      res == {'FINISHED'}
      and all(r.status not in ('match', 'resolved') for r in results),
      str([(r.source, r.dest, r.status) for r in results]))
check("T21 apply non crea e non salta constraint",
      c["created"] == 0 and (c["skipped"] or 0) == 0,
      c["report"].replace("\n", " / "))
check("T21 report riporta osso senza controparte",
      "Ossa sorgente senza match" in c["report"]
      and "Ossa destinazione senza match" in c["report"],
      c["report"].replace("\n", " / "))
check("T21 nessun constraint sulla singola osso",
      len(arm.pose.bones["Solo"].constraints) == 0)

# =============================================================================
#  RIEPILOGO
# =============================================================================
total = len(RESULTS)
passed = sum(1 for _, ok, _ in RESULTS if ok)
print("\n===== RIEPILOGO TEST =====", flush=True)
print("Superati: {}/{}".format(passed, total), flush=True)
for name, ok, detail in RESULTS:
    if not ok:
        print("FALLITO: {} | {}".format(name, detail), flush=True)
print("==========================", flush=True)

if passed != total:
    raise SystemExit(1)
print("TUTTI I TEST SUPERATI", flush=True)
