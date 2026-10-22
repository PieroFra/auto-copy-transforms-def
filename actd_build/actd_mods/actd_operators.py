# MODULO actd_operators.py — operatori actd.* e helper di supporto (intestazione di build, non fa parte del monolite)


# =============================================================================
#  OPERATORI
# =============================================================================

class ACTD_OT_set_source_object(Operator):
    """Imposta l'armatura sorgente sull'oggetto attivo selezionato (o la azzera)"."""

    bl_idname = "actd.set_source_object"
    bl_label = "Imposta armatura sorgente"
    bl_description = (
        "Usa l'oggetto attivo selezionato come armatura sorgente, oppure "
        "azzera il campo per tornare alla stessa armatura"
    )
    bl_options = {'REGISTER', 'UNDO'}

    clear: BoolProperty(
        name="Azzera",
        description="Rimuove l'armatura sorgente selezionata",
        default=False,
    )

    def execute(self, context):
        settings = _settings(context)
        if self.clear:
            settings.source_object = None
            self.report({'INFO'}, "Armatura sorgente azzerata (stessa armatura).")
            return {'FINISHED'}

        obj = context.active_object
        if obj is None:
            for candidate in context.selected_objects:
                if candidate.type == 'ARMATURE':
                    obj = candidate
                    break
        if obj is None or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Seleziona un'armatura da usare come sorgente.")
            return {'CANCELLED'}

        settings.source_object = obj
        settings.preview_is_stale = True
        self.report({'INFO'}, f"Armatura sorgente: {obj.name}")
        return {'FINISHED'}


class ACTD_OT_dest_preset(Operator):
    """Imposta rapidamente il token destinazione a un valore predefinito."""

    bl_idname = "actd.dest_preset"
    bl_label = "Preset destinazione"
    bl_description = "Imposta rapidamente il token di destinazione"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    preset: StringProperty(default="MCH_")
    token_type: StringProperty(default="PREFIX")

    def execute(self, context):
        _apply_dest_preset(_settings(context), self.preset, self.token_type)
        return {'FINISHED'}


class ACTD_OT_refresh_constraint_name(Operator):
    """Ricalcola il nome del constraint dai token correnti."""

    bl_idname = "actd.refresh_constraint_name"
    bl_label = "Aggiorna nome constraint dai token"
    bl_description = "Calcola un nome constraint suggerito dai token sorgente/destinazione"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        settings = _settings(context)
        settings.constraint_name = _suggest_constraint_name(settings)
        return {'FINISHED'}


class ACTD_OT_guess_prefixes(Operator):
    """Deduce i prefissi piu' probabili dai nomi delle ossa."""

    bl_idname = "actd.guess_prefixes"
    bl_label = "Indovina prefissi"
    bl_description = (
        "Compila i token sorgente e destinazione con i prefissi piu' frequenti "
        "nelle due armature, senza cambiare i default se la stima non e' sicura"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'ARMATURE'

    def execute(self, context):
        arm_obj = context.object
        settings = _settings(context)
        if arm_obj is None or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Seleziona un'armatura attiva.")
            return {'CANCELLED'}

        src_obj = _source_obj(arm_obj, settings)
        src_token, dst_token, reliable, detail = _guess_prefixes(
            src_obj, arm_obj
        )

        settings.source_token = src_token
        settings.dest_token = dst_token
        settings.source_token_type = 'PREFIX'
        settings.dest_token_type = 'PREFIX'
        _set_preview_report(
            settings,
            f"Prefissi: sorgente '{src_token}', destinazione '{dst_token}'.\n"
            f"{detail}",
        )

        if reliable:
            self.report({'INFO'}, f"Prefissi: {src_token} / {dst_token}")
        else:
            self.report({'WARNING'}, detail)
        return {'FINISHED'}


class ACTD_OT_learn_pattern(Operator):
    """Impara la regola di mappatura da un constraint di copia esistente."""

    bl_idname = "actd.learn_pattern"
    bl_label = "Impara da constraint"
    bl_description = (
        "Ricava token, tipo, spazi, influenza e mix dal constraint attivo "
        "sull'osso selezionato e li riusa sul resto del rig"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is None or obj.type != 'ARMATURE' or obj.mode != 'POSE':
            return False
        for pb in obj.pose.bones:
            if not _is_pose_bone_selected(pb):
                continue
            if any(c.type in CONSTRAINT_TYPE_LABELS for c in pb.constraints):
                return True
        return False

    def execute(self, context):
        arm_obj = context.object
        settings = _settings(context)
        if arm_obj is None or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Seleziona un'armatura attiva in Pose Mode.")
            return {'CANCELLED'}

        candidati = []
        for pb in arm_obj.pose.bones:
            if not _is_pose_bone_selected(pb):
                continue
            copie = [
                c for c in pb.constraints if c.type in CONSTRAINT_TYPE_LABELS
            ]
            if not copie:
                continue
            active = getattr(pb.constraints, "active", None)
            if active is not None and active.type in CONSTRAINT_TYPE_LABELS:
                candidati.append((pb, active))
            else:
                candidati.append((pb, copie[0]))

        if not candidati:
            self.report(
                {'ERROR'}, "Nessun constraint di copia sull'osso selezionato."
            )
            return {'CANCELLED'}

        regole = [
            _infer_token_rule(pb.name, con.subtarget)
            for pb, con in candidati
        ]
        regola = _majority_token_rule(regole)
        primary_pb, primary_con = candidati[0]
        note = _apply_learned_settings(settings, primary_con)

        righe = [f"Imparato da '{primary_pb.name}' / '{primary_con.name}':"]
        if regola:
            src, dst, src_type, dst_type = regola
            settings.source_token = src
            settings.dest_token = dst
            settings.source_token_type = src_type
            settings.dest_token_type = dst_type
            righe.append(
                f"Token: sorgente '{src}', destinazione '{dst}' "
                f"({src_type}/{dst_type})."
            )
            if _META_RX & (set(src) | set(dst)):
                note.append(
                    "I token contengono metacaratteri: usati letteralmente."
                )
        else:
            righe.append(
                "Token non deducibili con maggioranza: campi invariati."
            )

        righe.extend(note)
        _set_preview_report(settings, "\n".join(righe))
        settings.preview_is_stale = True

        if regola:
            self.report(
                {'INFO'}, f"Pattern appreso: {regola[0]} / {regola[1]}"
            )
        else:
            self.report({'WARNING'}, "Token non deducibili: campi invariati.")
        return {'FINISHED'}


class ACTD_OT_preview(Operator):
    """Calcola e mostra la mappatura senza applicare nulla."""

    bl_idname = "actd.preview"
    bl_label = "Anteprima mappatura"
    bl_description = "Mostra le coppie sorgente -> destinazione rilevate"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def execute(self, context):
        arm_obj = context.object
        settings = _settings(context)

        pattern_err = _validate_pattern(settings)
        if pattern_err:
            self.report({'ERROR'}, pattern_err)
            return {'CANCELLED'}

        results = compute_mapping(arm_obj, settings)
        _store_preview(settings, arm_obj, results)

        ambiguous = sum(1 for r in results if r.status == 'ambiguous')
        unm_src = sum(1 for r in results if r.status == 'unmatched_src')
        unm_dst = sum(1 for r in results if r.status == 'unmatched_dst')
        valid = sum(1 for r in results if r.status in ('match', 'resolved'))

        _set_preview_report(
            settings,
            f"Anteprima completata su '{arm_obj.name}'.\n"
            f"Coppie valide: {valid}\n"
            f"Coppie ambigue: {ambiguous}\n"
            f"Ossa sorgente senza match: {unm_src}\n"
            f"Ossa destinazione senza match: {unm_dst}",
        )

        self.report(
            {'INFO'},
            f"Anteprima: {valid} coppie valide, {ambiguous} ambigue, {unm_src + unm_dst} senza match.",
        )
        return {'FINISHED'}


def validate_source_object(arm_obj, target_obj):
    """Controlla che l'armatura sorgente sia utilizzabile.

    Ritorna una stringa di errore oppure None. Tenuto separato da apply()
    per poterlo testare anche quando l'operatore non e' invocabile.
    """
    if target_obj is None:
        return "Armatura sorgente non valida."
    if target_obj.type != 'ARMATURE':
        return "L'oggetto sorgente non e' un'armatura."
    if target_obj is arm_obj:
        return None
    if target_obj.mode == 'EDIT':
        return "L'armatura sorgente e' in Edit Mode."
    if target_obj.hide_viewport:
        return "L'armatura sorgente e' nascosta."
    if not len(target_obj.data.bones):
        return "L'armatura sorgente non ha ossa."
    return None


class ACTD_OT_diagnose(Operator):
    """Analizza il rig e segnala i problemi prima di applicare"""

    bl_idname = "actd.diagnose"
    bl_label = "Verifica rig"
    bl_description = (
        "Controlla mappatura, orientamento di rest, driver concorrenti e "
        "spazio consigliato senza modificare nulla"
    )
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def execute(self, context):
        arm_obj = context.object
        settings = _settings(context)
        findings = diagnose_rig(arm_obj, settings)
        # La diagnostica scrive solo il proprio stato: il report di anteprima
        # resta intatto (prima entrambi usavano last_report).
        _store_diagnostics(settings, findings)

        errors = sum(1 for level, _ in findings if level == 'error')
        warnings = sum(1 for level, _ in findings if level == 'warning')
        infos = sum(1 for level, _ in findings if level == 'info')

        # `last_report` resta l'ultimo report generico (compatibilita').
        settings.last_report = settings.diagnostic_report

        self.report(
            {'INFO'} if not errors else {'WARNING'},
            f"Verifica: {errors} errori, {warnings} avvisi, {infos} suggerimenti.",
        )
        return {'FINISHED'}


class ACTD_OT_apply(Operator):
    """Crea i constraint di copia sulle ossa destinazione."""

    bl_idname = "actd.apply_transforms"
    bl_label = "Applica constraint"
    bl_description = (
        "Crea i constraint di copia sulle ossa destinazione, secondo il tipo "
        "selezionato"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def execute(self, context):
        arm_obj = context.object
        settings = _settings(context)

        if arm_obj is None or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Seleziona un'armatura attiva in Pose Mode.")
            return {'CANCELLED'}

        pattern_err = _validate_pattern(settings)
        if pattern_err:
            self.report({'ERROR'}, pattern_err)
            return {'CANCELLED'}

        # Modulo 1: il target del constraint e' l'armatura sorgente (se impostata)
        target_obj = _source_obj(arm_obj, settings)
        src_err = validate_source_object(arm_obj, target_obj)
        if src_err:
            self.report({'ERROR'}, src_err)
            return {'CANCELLED'}

        results = compute_mapping(arm_obj, settings)

        ambiguous = sum(1 for r in results if r.status == 'ambiguous')
        unm_src = sum(1 for r in results if r.status == 'unmatched_src')
        unm_dst = sum(1 for r in results if r.status == 'unmatched_dst')

        selected = None
        if settings.apply_mode == 'SELECTED':
            selected = {pb.name for pb in arm_obj.pose.bones if _is_pose_bone_selected(pb)}
            if not selected:
                self.report({'WARNING'}, "Nessuna osso selezionato in Pose Mode.")
                _set_preview_report(
                    settings,
                    "Applicazione annullata: nessun osso selezionato.",
                )
                return {'CANCELLED'}

        created = 0
        updated = 0
        skipped = 0
        replaced = 0
        errors = []
        warnings = []
        con_name = _effective_constraint_name(settings)
        con_type = _constraint_type(settings)

        for res in results:
            if res.status not in ('match', 'resolved'):
                continue

            if selected is not None:
                if res.source not in selected and res.dest not in selected:
                    skipped += 1
                    continue

            pose_bone = arm_obj.pose.bones.get(res.dest)
            if pose_bone is None:
                errors.append(f"Osso '{res.dest}' non trovato in Pose Mode.")
                continue

            # 1. Modalità REPLACE: rimuove i constraint esistenti dello stesso tipo
            if settings.existing_mode == 'REPLACE':
                for con in list(pose_bone.constraints):
                    if con.type == con_type:
                        _forget_generated(arm_obj, pose_bone, con.name)
                        pose_bone.constraints.remove(con)
                        replaced += 1

                con = pose_bone.constraints.new(con_type)
                warnings.extend(
                    _configure_constraint(con, con_name, target_obj, res.source, settings)
                )
                _apply_stack_position(pose_bone, con, settings)
                _mark_generated(arm_obj, pose_bone, con, target_obj, res.source)
                created += 1
                continue

            # 2. Modalità KEEP: controlla prima i constraint generati dall'addon
            generated_all = _find_all_generated(arm_obj, pose_bone)
            same_type = [c for c in generated_all if c.type == con_type]
            other_type = [c for c in generated_all if c.type != con_type]

            # Cambio di tipo: i constraint generati con un tipo diverso vengono
            # sostituiti, altrimenti resterebbero due copie sovrapposte.
            if not same_type and other_type:
                for stale in other_type:
                    _forget_generated(arm_obj, pose_bone, stale.name)
                    pose_bone.constraints.remove(stale)
                    replaced += 1
                warnings.append(
                    f"Osso '{res.dest}': sostituiti {len(other_type)} constraint "
                    f"generati di tipo diverso."
                )

            if same_type:
                generated = same_type[0]
                extras = same_type[1:]
                if extras:
                    for extra in extras:
                        _forget_generated(arm_obj, pose_bone, extra.name)
                        pose_bone.constraints.remove(extra)
                    warnings.append(
                        f"Osso '{res.dest}': rimossi {len(extras)} constraint generati duplicati."
                    )

                if settings.update_mode == 'UPDATE':
                    old_name = generated.name
                    warnings.extend(_configure_constraint(
                        generated, con_name, target_obj, res.source, settings
                    ))
                    _apply_stack_position(pose_bone, generated, settings)
                    if generated.name != old_name:
                        _forget_generated(arm_obj, pose_bone, old_name)
                    _mark_generated(arm_obj, pose_bone, generated, target_obj, res.source)
                    updated += 1
                else:
                    skipped += 1
                continue

            # 3. Controllo duplicati manuali equivalenti
            if settings.avoid_duplicates:
                duplicate = _find_matching_copy(pose_bone, target_obj, res.source, settings)
                if duplicate is not None:
                    skipped += 1
                    warnings.append(
                        f"Osso '{res.dest}': esiste già un constraint manuale equivalente."
                    )
                    continue

            # 4. Creazione nuovo constraint
            con = pose_bone.constraints.new(con_type)
            warnings.extend(
                _configure_constraint(con, con_name, target_obj, res.source, settings)
            )
            _apply_stack_position(pose_bone, con, settings)
            _mark_generated(arm_obj, pose_bone, con, target_obj, res.source)
            created += 1

        # Gli avvisi di configurazione (mix non supportato, shear ignorato) sono
        # identici per ogni osso: si riportano una sola volta, e in testa, cosi'
        # non affogano quelli specifici di un osso.
        unique_warnings = []
        for warn in warnings:
            if warn not in unique_warnings:
                unique_warnings.append(warn)

        _store_preview(settings, arm_obj, results)
        _set_preview_report(
            settings,
            _build_report(
                created, updated, skipped, replaced,
                ambiguous, unm_src, unm_dst, errors, unique_warnings,
            ),
        )

        self.report(
            {'INFO'},
            f"Creati {created}, aggiornati {updated}, saltati {skipped}, ambigui {ambiguous}.",
        )
        return {'FINISHED'}


class ACTD_OT_remove(Operator):
    """Rimuove i constraint creati dall'addon per il tipo selezionato."""

    bl_idname = "actd.remove_generated"
    bl_label = "Rimuovi constraint creati"
    bl_description = (
        "Rimuove solo i constraint generati dall'addon del tipo selezionato"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def execute(self, context):
        arm_obj = context.object
        settings = _settings(context)

        if arm_obj is None or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Seleziona un'armatura attiva in Pose Mode.")
            return {'CANCELLED'}

        selected = None
        if settings.apply_mode == 'SELECTED':
            selected = {pb.name for pb in arm_obj.pose.bones if _is_pose_bone_selected(pb)}
            if not selected:
                self.report({'WARNING'}, "Nessun osso selezionato: rimozione annullata.")
                _set_preview_report(
                    settings,
                    "Rimozione annullata: nessun osso selezionato.",
                )
                return {'CANCELLED'}

        removed = 0
        con_type = _constraint_type(settings)
        for pose_bone in arm_obj.pose.bones:
            if selected is not None and pose_bone.name not in selected:
                continue
            for con in list(pose_bone.constraints):
                # Solo il tipo selezionato: gli altri generati restano intatti.
                if con.type == con_type and _is_generated(
                    arm_obj, pose_bone, con
                ):
                    _forget_generated(arm_obj, pose_bone, con.name)
                    pose_bone.constraints.remove(con)
                    removed += 1

        _prune_registry(arm_obj)

        _set_preview_report(settings, f"Constraint rimossi: {removed}")
        self.report({'INFO'}, f"Rimossi {removed} constraint.")
        return {'FINISHED'}


class ACTD_OT_clean_registry(Operator):
    """Pulisce il registro dei constraint generati da voci orfane."""

    bl_idname = "actd.clean_registry"
    bl_label = "Pulisci registro"
    bl_description = (
        "Rimuove dal registro interno i riferimenti a ossa o constraint "
        "che non esistono piu'"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def execute(self, context):
        arm_obj = context.object
        settings = _settings(context)
        if arm_obj is None or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Seleziona un'armatura attiva.")
            return {'CANCELLED'}

        removed = _prune_registry(arm_obj)
        _set_maintenance_report(
            settings, f"Voci orfane rimosse dal registro: {removed}"
        )
        self.report({'INFO'}, f"Registro pulito: {removed} voci orfane rimosse.")
        return {'FINISHED'}


# --- Export del registro -----------------------------------------------------
_EXPORT_FIELDS = (
    "armatura", "osso", "constraint", "tipo", "sorgente",
    "target_object", "influenza", "mix_mode", "spazi", "stato",
)


def _export_base_dir():
    """Cartella del .blend, oppure la cwd se il file non e' ancora salvato."""
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    return os.getcwd()


def _export_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _collect_generated_rows():
    """Una riga per ogni voce del registro, incluse quelle orfane."""
    rows = []
    for arm in bpy.data.objects:
        if getattr(arm, "type", None) != 'ARMATURE':
            continue
        for bone_name, entries in _read_registry(arm).items():
            if not isinstance(entries, dict):
                continue
            pose_bone = arm.pose.bones.get(bone_name)
            constraints = (
                {c.name: c for c in pose_bone.constraints}
                if pose_bone is not None else {}
            )
            for con_name, entry in entries.items():
                entry = entry if isinstance(entry, dict) else {}
                con = constraints.get(con_name)
                target = getattr(con, "target", None) if con is not None else None
                rows.append({
                    "armatura": arm.name,
                    "osso": bone_name,
                    "constraint": con_name,
                    "tipo": con.type if con is not None else "",
                    "sorgente": (
                        getattr(con, "subtarget", "")
                        if con is not None else entry.get("bone", "")
                    ),
                    "target_object": (
                        target.name if target is not None
                        else entry.get("obj", "")
                    ),
                    "influenza": (
                        "%.3f" % con.influence if con is not None else ""
                    ),
                    "mix_mode": (
                        getattr(con, "mix_mode", "") if con is not None else ""
                    ),
                    "spazi": (
                        "%s/%s" % (
                            getattr(con, "target_space", ""),
                            getattr(con, "owner_space", ""),
                        ) if con is not None else ""
                    ),
                    "stato": (
                        ("muto" if con.mute else "attivo")
                        if con is not None else "orfano"
                    ),
                })
    return rows


def _write_export_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(_EXPORT_FIELDS))
        writer.writeheader()
        writer.writerows(rows)


def _write_export_json(path, rows):
    payload = {
        "versione": "1.1.5",
        "generato_il": datetime.now().isoformat(timespec="seconds"),
        "righe": rows,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return payload


class ACTD_OT_convert_to_manual(Operator):
    """Toglie dal registro i constraint generati, lasciandoli sulla riga."""

    bl_idname = "actd.convert_to_manual"
    bl_label = "Converti in manuali"
    bl_description = (
        "I constraint generati restano identici ma escono dal registro: non "
        "verranno piu' rimossi dall'addon"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def execute(self, context):
        arm_obj = context.object
        settings = _settings(context)
        if arm_obj is None or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Seleziona un'armatura attiva in Pose Mode.")
            return {'CANCELLED'}

        converted = 0
        for pose_bone in arm_obj.pose.bones:
            for con in list(pose_bone.constraints):
                if _is_generated(arm_obj, pose_bone, con):
                    _forget_generated(arm_obj, pose_bone, con.name)
                    converted += 1
        _prune_registry(arm_obj)

        _set_maintenance_report(
            settings, f"Constraint convertiti in manuali: {converted}"
        )
        self.report({'INFO'}, f"Convertiti {converted} constraint in manuali.")
        return {'FINISHED'}


class ACTD_OT_mute_all(Operator):
    """Muta o smuta tutti i constraint generati nella scena."""

    bl_idname = "actd.mute_all"
    bl_label = "Mute/Unmute generati"
    bl_description = (
        "Attiva o disattiva il mute su tutti i constraint generati, senza "
        "toccare quelli manuali"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def execute(self, context):
        settings = _settings(context)
        state = not bool(settings.mute_state)
        settings.mute_state = state

        changed = 0
        for arm in bpy.data.objects:
            if getattr(arm, "type", None) != 'ARMATURE':
                continue
            for pose_bone in arm.pose.bones:
                for con in pose_bone.constraints:
                    if _is_generated(arm, pose_bone, con):
                        con.mute = state
                        changed += 1

        azione = "mutati" if state else "riattivati"
        _set_maintenance_report(
            settings, f"Constraint generati {azione}: {changed}"
        )
        self.report({'INFO'}, f"Constraint generati {azione}: {changed}.")
        return {'FINISHED'}


class ACTD_OT_export_csv(Operator):
    """Esporta il registro dei constraint generati in CSV."""

    bl_idname = "actd.export_csv"
    bl_label = "Export CSV"
    bl_description = "Salva una riga per ogni constraint generato nel registro"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def execute(self, context):
        settings = _settings(context)
        rows = _collect_generated_rows()
        path = os.path.join(
            _export_base_dir(), f"actd_export_{_export_timestamp()}.csv"
        )
        try:
            _write_export_csv(path, rows)
        except OSError as exc:
            self.report({'ERROR'}, f"Impossibile scrivere il CSV: {exc}")
            return {'CANCELLED'}

        _set_maintenance_report(
            settings,
            f"Report salvato in: {path}\nRighe esportate: {len(rows)}",
        )
        self.report({'INFO'}, f"CSV salvato: {path}")
        return {'FINISHED'}


class ACTD_OT_export_json(Operator):
    """Esporta il registro dei constraint generati in JSON."""

    bl_idname = "actd.export_json"
    bl_label = "Export JSON"
    bl_description = "Salva il registro dei constraint generati in JSON"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def execute(self, context):
        settings = _settings(context)
        rows = _collect_generated_rows()
        path = os.path.join(
            _export_base_dir(), f"actd_export_{_export_timestamp()}.json"
        )
        try:
            _write_export_json(path, rows)
        except OSError as exc:
            self.report({'ERROR'}, f"Impossibile scrivere il JSON: {exc}")
            return {'CANCELLED'}

        _set_maintenance_report(
            settings,
            f"Report salvato in: {path}\nRighe esportate: {len(rows)}",
        )
        self.report({'INFO'}, f"JSON salvato: {path}")
        return {'FINISHED'}


class ACTD_OT_show_info(Operator):
    """Mostra README, licenza e informazioni sull'autore."""

    bl_idname = "actd.show_info"
    bl_label = "Informazioni"
    bl_description = "Mostra README, licenza e creatore dell'addon"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=640)

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        english = _is_english_ui()
        layout.label(text="AUTO COPY TRANSFORMS DEF", icon='INFO')
        layout.label(
            text=bpy.app.translations.pgettext("Creatore: ") + CREATOR_NAME
        )

        row = layout.row(align=True)
        # Link cliccabile con etichetta umana/localizzata: l'ID numerico non
        # dice nulla all'utente.
        op = row.operator(
            "wm.url_open",
            text=bpy.app.translations.pgettext("Profilo Discord"),
            icon='URL',
        )
        op.url = DISCORD_URL
        op = row.operator(
            "wm.url_open", text="Licenza GPL completa", icon='URL'
        )
        op.url = LICENSE_URL

        box = layout.box()
        box.label(text="README", icon='TEXT')
        readme = README_TEXT_EN if english else README_TEXT
        for line in _wrap_text(readme):
            box.label(text=line if line else " ")

        box = layout.box()
        box.label(
            text=bpy.app.translations.pgettext("Licenza: ") + LICENSE_NAME,
            icon='INFO',
        )
        notice = LICENSE_NOTICE_EN if english else LICENSE_NOTICE
        for line in _wrap_text(notice):
            box.label(text=line if line else " ")

        row = layout.row(align=True)
        for label, filename, icon in (
            ("README EN", "README.txt", 'TEXT'),
            ("README IT", "README.it.txt", 'TEXT'),
            ("LICENSE", "LICENSE.txt", 'INFO'),
        ):
            doc_url = _local_doc_url(filename)
            if doc_url:
                op = row.operator(
                    "wm.url_open", text="Apri " + label, icon=icon
                )
                op.url = doc_url


# =============================================================================
#  TESTO DINAMICO DEI PANNELLI
# =============================================================================

def _token_display(token, token_type):
    """Token come compare nel nome osso: 'DEF_*' (prefisso) o '*_ctrl' (suffisso)."""
    token = (token or "").strip()
    if not token:
        return "-"
    if token_type == 'SUFFIX':
        return "*" + token
    return token + "*"


def _mapping_label_text(settings):
    """Riga con la mappatura attualmente impostata.

    Sostituisce la vecchia label statica "Default: DEF_ → MCH_", che restava
    vera solo finché l'utente non cambiava i token.
    """
    source = _token_display(settings.source_token, settings.source_token_type)
    dest = _token_display(settings.dest_token, settings.dest_token_type)
    prefix = bpy.app.translations.pgettext("Token attuali: ")
    return f"{prefix}{source} → {dest}"


def _learn_condition_note(context):
    """Testo e icona della condizione che abilita "Impara da constraint".

    Usa lo stesso poll dell'operatore, senza modificarne la semantica: serve
    solo a spiegare accanto al pulsante perché risulta grigio.
    """
    if ACTD_OT_learn_pattern.poll(context):
        return (
            bpy.app.translations.pgettext(
                "Legge il constraint di copia attivo sull'osso selezionato"
            ),
            'CHECKMARK',
        )
    return (
        bpy.app.translations.pgettext(
            "Serve un osso in Pose Mode con un constraint di copia"
        ),
        'INFO',
    )
