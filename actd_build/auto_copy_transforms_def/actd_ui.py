# --- inizio blocco generato dalla build (non modificare a mano) ---
# Importa i nomi dei moduli precedenti del pacchetto: nel monolite erano
# nello stesso spazio dei nomi, qui vanno riportati a mano.
import importlib as _actd_imp

_actd_prec = ("actd_header", "actd_i18n", "actd_tokens", "actd_registry", "actd_logic", "actd_properties", "actd_operators",)
for _actd_nome in _actd_prec:
    for _actd_k, _actd_v in vars(
            _actd_imp.import_module("." + _actd_nome, __package__)).items():
        if not _actd_k.startswith("__"):
            globals().setdefault(_actd_k, _actd_v)
del _actd_imp, _actd_prec, _actd_nome, _actd_k, _actd_v
# --- fine blocco generato dalla build ---



# =============================================================================
#  PANNELLI UI
# =============================================================================

class ACTD_PT_main(Panel):
    """Pannello principale nella sidebar della 3D View."""

    bl_label = "Auto Copy Transforms"
    bl_idname = "ACTD_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Auto Copy Transforms"

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def draw(self, context):
        layout = self.layout
        settings = _settings(context)

        # ---------------- Avvio rapido ----------------
        # Anteprima e Applica stanno qui, in cima: prima erano in fondo al
        # pannello e serviva lo scroll per raggiungerle.
        box = layout.box()
        box.label(text="Avvio rapido", icon='INFO')
        # Avvio rapido spezzato in due label: una riga unica superava la
        # larghezza della sidebar e veniva troncata con '…'.
        box.label(text="1. Scegli i token")
        box.label(text="2. Anteprima  3. Applica")
        actions = box.column(align=True)
        actions.operator("actd.preview", icon='ZOOM_SELECTED')
        actions.operator("actd.apply_transforms", icon='CONSTRAINT')

        # ---------------- Token di mappatura ----------------
        box = layout.box()
        box.label(text="Token di mappatura", icon='SORTALPHA')

        box.label(text="Sorgente (Target)")
        row = box.row(align=True)
        row.prop(settings, "source_token", text="")
        row.prop(settings, "source_token_type", text="")

        box.label(text="Destinazione (Owner)")
        row = box.row(align=True)
        row.prop(settings, "dest_token", text="")
        row.prop(settings, "dest_token_type", text="")

        # Preset: un solo menu a tendina al posto dei quattro pulsanti.
        # Label del concetto a tutta larghezza e menu senza label propria:
        # nella colonna stretta del prop la label lunga veniva troncata.
        box.label(text="Preset destinazione:")
        box.row().prop(settings, "dest_preset_choice", text="")
        # Avviso sotto il menu: il preset scelto coincide con la sorgente.
        notice = getattr(settings, "dest_preset_notice", "")
        if notice:
            for line in _ui_report_lines(notice) or [" "]:
                box.label(text=line, icon='ERROR')

        col = box.column(align=True)
        col.operator(
            "actd.guess_prefixes", text="Indovina prefissi", icon='AUTO'
        )
        col.operator(
            "actd.learn_pattern", text="Impara da constraint", icon='IMPORT'
        )
        # Condizione concreta accanto al pulsante: senza questa riga il
        # pulsante appare grigio senza spiegare cosa manca (stesso poll
        # dell'operatore, nessun cambio di semantica).
        learn_text, learn_icon = _learn_condition_note(context)
        learn_lines = _ui_report_lines(learn_text) or [" "]
        box.label(text=learn_lines[0], icon=learn_icon)
        for line in learn_lines[1:]:
            box.label(text=line)

        # Mappatura corrente: la vecchia label statica "Default: DEF_ → MCH_"
        # restava falsa appena si cambiavano i token.
        # Pattern, filtro e mix stanno nel pannello figlio "Avanzate": il
        # rimando testuale è stato tolto perché si troncava e ridondava.
        box.label(text=_mapping_label_text(settings), icon='INFO')

        # ---------------- Armatura sorgente (Modulo 1) ----------------
        box = layout.box()
        box.label(text="Armatura sorgente", icon='ARMATURE_DATA')
        row = box.row(align=True)
        row.prop(settings, "source_object", text="")
        op = row.operator("actd.set_source_object", text="", icon='RESTRICT_SELECT_OFF')
        op.clear = False
        op = row.operator("actd.set_source_object", text="", icon='X')
        op.clear = True
        src_obj = _source_obj(context.object, settings) if context.object else None
        if settings.source_object is None:
            box.label(text="Stessa armatura (default)", icon='INFO')
        elif src_obj is not None:
            box.label(
                text=_translate_report_text(f"Sorgente: {src_obj.name}"),
                icon='LINKED',
            )

        # ---------------- Opzioni constraint ----------------
        box = layout.box()
        box.label(text="Opzioni constraint", icon='CONSTRAINT')

        col = box.column(align=True)
        col.prop(settings, "apply_mode", text="Applica a")
        col.prop(settings, "influence", text="Influenza")
        # Etichette corte e stabili: le parole "Target"/"Owner" vengono tradotte
        # da Blender ("Proprietario") e troncano la riga nella sidebar.
        col.prop(settings, "target_space", text="Src")
        col.prop(settings, "owner_space", text="Dest")
        col.prop(settings, "resolve_ambiguous", text="Risolvi ambiguità")

        # Filtro bone collection, opzioni avanzate e pattern sono diventati il
        # pannello figlio "Avanzate": qui restano solo i pulitori dei constraint
        # già creati.
        # ---------------- Constraint generati ----------------
        box = layout.box()
        box.label(text="Constraint generati", icon='PLAY')
        col = box.column(align=True)
        col.operator("actd.remove_generated", icon='TRASH')
        row = col.row(align=True)
        row.operator("actd.clean_registry", icon='BRUSH_DATA')

        # ---------------- Informazioni / README ----------------
        row = layout.row()
        row.operator(
            "actd.show_info", text="Informazioni / README", icon='INFO'
        )


class ACTD_PT_advanced(Panel):
    """Sotto-pannello richiudibile con i controlli avanzati.

    Raccoglie le opzioni che prima erano stipate nel pannello principale
    (mix/posizione nello stack, filtro bone collection, pattern): restano
    tutte disponibili, ma non occupano più la parte alta della sidebar.
    """

    bl_label = "Avanzate"
    bl_idname = "ACTD_PT_advanced"
    bl_parent_id = "ACTD_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Auto Copy Transforms"
    # Richiudibile e chiuso di default: sono regolazioni facoltative.
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def draw(self, context):
        layout = self.layout
        settings = _settings(context)

        # ---------------- Tipo e nome constraint (Modulo 5) ----------------
        box = layout.box()
        box.label(text="Tipo e nome constraint", icon='CONSTRAINT')

        typ = box.column(align=True)
        typ.row().prop(settings, "constraint_type", text="Tipo")
        if settings.constraint_type != 'COPY_TRANSFORMS':
            typ.label(
                text="Copy Rotation e' il caso tipico DEF → MCH",
                icon='INFO',
            )

        # Nome constraint: label esterna e campo a tutta larghezza, così il
        # nome resta leggibile invece di essere troncato dal pulsante.
        box.label(text="Nome constraint", icon='CONSTRAINT')
        name_row = box.row(align=True)
        name_row.prop(settings, "constraint_name", text="")
        name_row.operator("actd.refresh_constraint_name", text="", icon='FILE_REFRESH')

        # ---------------- Constraint esistenti ----------------
        box = layout.box()
        box.label(text="Constraint esistenti", icon='DUPLICATE')

        # Il concetto sta su una label a tutta larghezza; le tre proprieta'
        # usano etichette corte per non essere troncate nella colonna stretta.
        box.label(text="Se esiste già")
        exi = box.column(align=True)
        exi.prop(settings, "existing_mode", text="Esistenti")
        # L'avviso e' spezzato come gli altri report: una label unica veniva
        # troncata dalla sidebar stretta.
        for line in _ui_report_lines(
            bpy.app.translations.pgettext(
                "Sostituisci rimuove anche i constraint manuali dello stesso tipo"
            )
        ):
            exi.label(text=line, icon='ERROR')

        # Disabilita update_mode e avoid_duplicates se si è in modalità REPLACE
        keep_col = exi.column(align=True)
        keep_col.enabled = (settings.existing_mode == 'KEEP')
        keep_col.prop(settings, "update_mode", text="Aggiorna")
        keep_col.prop(settings, "avoid_duplicates", text="Evita duplicati")

        # ---------------- Mix e posizione nello stack (Modulo 2) ----------------
        box = layout.box()
        box.label(text="Mix e posizione nello stack", icon='PREFERENCES')

        adv = box.column(align=True)
        adv.prop(settings, "mix_mode", text="Mix")
        if _constraint_supports_offset(settings.constraint_type):
            adv.prop(settings, "use_offset", text="Usa offset")
        elif settings.use_offset:
            adv.label(text="'Usa offset' non disponibile per questo tipo", icon='ERROR')
        adv.prop(settings, "stack_position", text="Posizione")
        adv.prop(settings, "remove_target_shear", text="Rimuovi shear")

        # Avvisi contestuali: mostrano subito cosa verra' ignorato
        _, mix_note = _resolved_mix_mode(settings, settings.constraint_type)
        if mix_note:
            mix_lines = _ui_report_lines(mix_note) or [" "]
            adv.label(text=mix_lines[0], icon='ERROR')
            for line in mix_lines[1:]:
                adv.label(text=line)
        elif settings.mix_mode != 'REPLACE':
            adv.label(
                text="Il mix cambia il risultato: verifica in viewport",
                icon='INFO',
            )
        if settings.remove_target_shear and not _constraint_supports(
            settings.constraint_type, "remove_target_shear"
        ):
            adv.label(text="'Rimuovi shear' non esiste per questo tipo", icon='ERROR')
        if settings.stack_position == 'BEFORE_IK':
            has_ik = any(
                c.type == 'IK'
                for pb in (context.object.pose.bones if context.object else ())
                for c in pb.constraints
            )
            if not has_ik:
                adv.label(text="Nessun constraint IK: posizione ignorata", icon='ERROR')

        # ---------------- Filtro bone collection (Modulo 3) ----------------
        box = layout.box()
        box.label(text="Filtro bone collection", icon='GROUP_BONE')

        flt = box.column(align=True)
        flt.prop(settings, "use_collection_filter", text="Filtra per bone collection")
        sub = flt.column(align=True)
        sub.enabled = settings.use_collection_filter
        sub.label(text="Collection sorgente")
        # Sulle armature con bone collection (Blender 4.x/5.x) il campo è un
        # prop_search sulle collection reali; senza API (3.6) o senza armatura
        # valida si ripiega esplicitamente sul campo testo.
        src_search = _collection_search_armature(context, settings, True)
        if src_search is not None:
            sub.prop_search(
                settings, "collection_source",
                src_search.data, "collections", text="",
            )
        else:
            sub.prop(settings, "collection_source", text="")
        sub.label(text="Collection destinazione")
        dst_search = _collection_search_armature(context, settings, False)
        if dst_search is not None:
            sub.prop_search(
                settings, "collection_dest",
                dst_search.data, "collections", text="",
            )
        else:
            sub.prop(settings, "collection_dest", text="")
        sub.prop(settings, "deform_only", text="Solo ossa deform")

        if settings.use_collection_filter:
            arm_owner = context.object
            if arm_owner is not None and arm_owner.type == 'ARMATURE':
                names = _collection_names(arm_owner.data)
                if names:
                    shown = ", ".join(names[:6]) + ("…" if len(names) > 6 else "")
                    sub.label(text="Collection: " + shown, icon='GROUP_BONE')
                elif not hasattr(arm_owner.data, "collections"):
                    sub.label(text="Bone collections non disponibili", icon='ERROR')
                else:
                    sub.label(text="Nessuna bone collection nell'armatura", icon='INFO')

        # ---------------- Pattern di mappatura ----------------
        box = layout.box()
        box.label(text="Pattern di mappatura", icon='SORTALPHA')

        col = box.column(align=True)
        col.prop(settings, "custom_pattern", text="Pattern")
        col.prop(settings, "use_regex", text="Usa regex")

        pattern_warning = _validate_pattern(settings)
        if pattern_warning:
            # Il messaggio nasce in italiano: qui si traduce solo per la UI.
            pat_lines = _ui_report_lines(
                _translate_report_text(pattern_warning)) or [" "]
            box.label(text=pat_lines[0], icon='ERROR')
            for line in pat_lines[1:]:
                box.label(text=line)


class ACTD_PT_maintenance(Panel):
    """Sotto-pannello di manutenzione dei constraint generati."""

    bl_label = "Manutenzione"
    bl_idname = "ACTD_PT_maintenance"
    bl_parent_id = "ACTD_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Auto Copy Transforms"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def draw(self, context):
        layout = self.layout
        settings = _settings(context)

        box = layout.box()
        row = box.row(align=True)
        row.operator(
            "actd.convert_to_manual", text="Converti in manuali",
            icon='UNLOCKED',
        )
        row.operator(
            "actd.clean_registry", text="Pulisci registro", icon='BRUSH_DATA'
        )

        row = box.row(align=True)
        row.operator(
            "actd.mute_all",
            text="Smuta generati" if settings.mute_state else "Muta generati",
            icon='MUTE_IPO_ON' if settings.mute_state else 'MUTE_IPO_OFF',
        )

        row = box.row(align=True)
        row.operator("actd.export_csv", text="Export CSV", icon='EXPORT')
        row.operator(
            "actd.export_json", text="Export JSON", icon='EXPORT'
        )

        # Solo il report di manutenzione: l'anteprima ha il suo pannello.
        if settings.maintenance_report:
            box = layout.box()
            box.label(text="Report:", icon='TEXT')
            _draw_report_text(box, settings.maintenance_report)


class ACTD_PT_diagnostics(Panel):
    """Sotto-pannello di diagnostica pre-flight del rig."""

    bl_label = "Verifica rig"
    bl_idname = "ACTD_PT_diagnostics"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Auto Copy Transforms"
    bl_parent_id = "ACTD_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def draw(self, context):
        layout = self.layout
        settings = _settings(context)

        row = layout.row(align=True)
        row.operator("actd.diagnose", icon='CHECKMARK')

        if settings.diagnostic_is_stale:
            layout.label(text="Diagnostica non aggiornata", icon='INFO')

        if not len(settings.diagnostic_items):
            layout.label(text="Nessun problema rilevato", icon='CHECKMARK')
            return

        icons = {
            'error': ('ERROR', 'ERROR'),
            # 'WARNING' non e' un'icona valida in Blender 5.x: usiamo l'icona
            # di stato equivalente, che esiste su tutte le versioni.
            'warning': ('STATUS_WARNING', 'ERROR'),
            'info': ('INFO', 'NONE'),
        }
        for item in settings.diagnostic_items:
            icon = icons.get(item.level, ('INFO', 'NONE'))[0]
            box = layout.box()
            # Anche i messaggi di diagnostica sono tradotti e spezzati: la
            # sidebar e' stretta e Blender tronca le label lunghe.
            lines = _ui_report_lines(item.text) or [" "]
            box.label(text=lines[0], icon=icon)
            for line in lines[1:]:
                box.label(text=line)


class ACTD_PT_preview(Panel):
    """Sotto-pannello con lista di anteprima e report finale."""

    bl_label = "Mappatura e report"
    bl_idname = "ACTD_PT_preview"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Auto Copy Transforms"
    bl_parent_id = "ACTD_PT_main"
    # Aperto di default: la lista di anteprima e il report sono l'esito
    # dell'operazione e devono essere visibili subito, non dopo un click.
    # `set()` esplicito evita di ereditare un DEFAULT_CLOSED futuro.
    bl_options = set()

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def draw(self, context):
        layout = self.layout
        settings = _settings(context)
        arm_obj = context.object

        is_wrong_armature = (
            bool(settings.preview_armature)
            and arm_obj is not None
            and settings.preview_armature != arm_obj.name
        )

        if settings.preview_is_stale or is_wrong_armature:
            layout.label(text="Anteprima non aggiornata", icon='ERROR')

        row = layout.row()
        row.template_list(
            "ACTD_UL_mapping", "",
            settings, "preview_items",
            settings, "preview_index",
            rows=8,
        )

        if 0 <= settings.preview_index < len(settings.preview_items):
            item = settings.preview_items[settings.preview_index]
            if item.note:
                col = layout.column(align=True)
                # Anche le note seguono il wrapping: sono testi lunghi.
                lines = _ui_report_lines(item.note) or [" "]
                col.label(text=lines[0], icon='INFO')
                for line in lines[1:]:
                    col.label(text=line)

        # Solo il report di anteprima: la manutenzione ha il suo pannello.
        if settings.preview_report:
            box = layout.box()
            box.label(text="Report:", icon='TEXT')
            _draw_report_text(box, settings.preview_report)
