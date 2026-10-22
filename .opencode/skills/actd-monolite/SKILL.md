---
name: ACTD Monolite
description: Mappa semantica di actd_build/auto_copy_transforms_def.py (zona del file, cosa fa, dove trovare cosa, invarianti di progetto) e come ottenere i numeri di riga col Scout AST senza caricare il codice. Usare prima di modificare l'addon.
---

# ACTD — Il monolite

Mappa per orientarsi in `actd_build\auto_copy_transforms_def.py` (~3.900 righe, un solo file).
**Non contiene numeri di riga**: cambiano a ogni modifica. Per le righe esatte si usa lo **Scout AST**
(vedi in fondo), che restituisce `Simbolo: inizio-fine` senza caricare il file.

## Zone del file (dal basso verso l'alto)

| Zona | Contenuto |
|---|---|
| testata | `bl_info` (1.1.0, categoria Rigging), import, costanti, `CREATOR_NAME`, `README_TEXT`, `LICENSE_URL` |
| traduzioni | `_is_english_ui()`, `_translate_*` (traduzione del **report** solo in visualizzazione) |
| testo e pattern | `_clean`, `_wrap_text`, `_local_doc_url`, `_split_side`, `_name_has_token`, `_strip_token`, `_build_template_regex`, `_validate_pattern` |
| token e prefissi | `_Normalizer`, `_side_compatible`, `_float_close`, `_suggest_constraint_name`, `_effective_constraint_name`, `_extract_prefix`, `_rank_prefixes`, `_best_prefix`, `_guess_prefixes` |
| mapping | `MappingResult`, `_collection_names`, `_bone_collection_names`, `_collection_filter_passes`, `_bone_passes_filters`, `diagnose_rig`, `compute_mapping` |
| constraint | `_constraint_type`, `_resolved_mix_mode`, `_constraint_supports*`, `_infer_token_rule`, `_majority_token_rule`, `_apply_learned_settings` |
| registro JSON | `_read_registry`, `_write_registry`, `_mark_generated`, `_forget_generated`, `_is_generated`, `_prune_registry`, `_find_generated_constraint` (i constraint non supportano IDProperties: il marcatore è un JSON sull'oggetto armatura) |
| dati | `ACDT_DiagnosticItem`, `ACDT_MappingItem`, `ACDT_Settings` (PropertyGroup) |
| UIList | `ACDT_UL_mapping` |
| operatori | `ACDT_OT_*` (vedi elenco sotto) |
| pannelli | `ACDT_PT_main`, `ACTD_PT_advanced`, `ACTD_PT_maintenance`, `ACTD_PT_diagnostics`, `ACTD_PT_preview` |
| registrazione | `_classes`, `_registration_order()`, `register()`, `unregister()`, `if __name__ == "__main__"` |

## Gli operatori (`actd.*`)

| Classe | id `bl_idname` | Funzione |
|---|---|---|
| `ACDT_OT_set_source_object` | `actd.set_source_object` | imposta l'armatura sorgente |
| `ACDT_OT_dest_preset` | `actd.dest_preset` | scrive il preset di destinazione |
| `ACDT_OT_refresh_constraint_name` | `actd.refresh_constraint_name` | rinomina il constraint |
| `ACTD_OT_guess_prefixes` | `actd.guess_prefixes` | auto-prefisso dai nomi |
| `ACDT_OT_learn_pattern` | `actd.learn_pattern` | apprende il pattern da un constraint |
| `ACTD_OT_preview` | `actd.preview` | anteprima della mappatura |
| `ACDT_OT_diagnose` | `actd.diagnose` | diagnostica del rig |
| `ACTD_OT_apply` | `actd.apply_transforms` | crea/aggiorna i constraint |
| `ACDT_OT_remove` | `actd.remove_generated` | rimuove i constraint generati |
| `ACTD_OT_clean_registry` | `actd.clean_registry` | pulizia del registro |
| `ACDT_OT_convert_to_manual` | `actd.convert_to_manual` | constraint -> copia manuale |
| `ACDT_OT_mute_all` | `actd.mute_all` | silenzia i constraint generati |
| `ACDT_OT_export_csv` | `actd.export_csv` | export CSV |
| `ACTD_OT_export_json` | `actd.export_json` | export JSON |
| `ACDT_OT_show_info` | `actd.show_info` | popup informazioni |

## Invarianti (non negoziabili)

- Un **solo file .py**, autosufficiente e installabile in Blender. **Commenti in italiano.**
- Non rinominare `bl_info` name, categoria **Rigging** né gli id `actd.*`; non rimuovere UIList,
  pannelli, operatori o proprietà esposti nella UI.
- Default = versione 1.0.0 salvo decisione esplicita dell'autore: token **`DEF_` / `MCH_`** con
  `COPY_TRANSFORMS` (`DEF-` / `MCH-` solo per compatibilità legacy/test, mai default).
- Differenze di versione Blender: **fallback espliciti**, mai controlli di versione sparsi nel codice.
- Ogni PropertyGroup usata da una CollectionProperty deve comparire in `_classes` (via
  `_registration_order`) **prima** della classe che la usa.
- Il file omonimo nella root è una **copia ACTD legacy**: fuori scope, non modificarlo né rinominarlo.
- **Un modulo alla volta.**

## Come trovare le righe: Scout AST

Non leggere il monolite per cercare un numero di riga (3.900 righe = migliaia di token sprecati).

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\run_scout.ps1 -Filter Panel
powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\run_scout.ps1 -Line 3200
```

Output: `SCOUT_FILE <file> righe=… simboli=…` e `SIMBOLO <Classe|Funzione> <nome> <inizio>-<fine>`.
Usa `-Filter` per il nome, `-Line` per scoprire quale simbolo contiene una riga.
