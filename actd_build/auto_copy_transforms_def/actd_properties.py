# --- inizio blocco generato dalla build (non modificare a mano) ---
# Importa i nomi dei moduli precedenti del pacchetto: nel monolite erano
# nello stesso spazio dei nomi, qui vanno riportati a mano.
import importlib as _actd_imp

_actd_prec = ("actd_header", "actd_i18n", "actd_tokens", "actd_registry", "actd_logic",)
for _actd_nome in _actd_prec:
    for _actd_k, _actd_v in vars(
            _actd_imp.import_module("." + _actd_nome, __package__)).items():
        if not _actd_k.startswith("__"):
            globals().setdefault(_actd_k, _actd_v)
del _actd_imp, _actd_prec, _actd_nome, _actd_k, _actd_v
# --- fine blocco generato dalla build ---



class ACTD_DiagnosticItem(PropertyGroup):
    """Singolo esito della diagnostica pre-flight."""

    level: StringProperty(name="Livello", default='info')
    text: StringProperty(name="Messaggio", default="")


class ACTD_MappingItem(PropertyGroup):
    """Singola riga dell'anteprima di mappatura."""
    source_name: StringProperty(name="Sorgente")
    dest_name: StringProperty(name="Destinazione")
    status: StringProperty(name="Stato")
    note: StringProperty(name="Nota")


class ACTD_Settings(PropertyGroup):
    """Impostazioni principali dell'addon, salvate nella Scene."""

    # Modulo 1: armatura sorgente separata. Vuoto = stessa armatura dell'owner,
    # quindi il comportamento di default resta identico alla 1.0.x.
    source_object: PointerProperty(
        name="Armatura sorgente",
        description=(
            "Armatura da cui copiare le trasformazioni. Lasciare vuoto per usare "
            "la stessa armatura su cui vengono creati i constraint"
        ),
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE',
        update=_mark_preview_stale,
    )

    # Modulo 2: controllo fine del constraint
    mix_mode: EnumProperty(
        name="Modalità mix",
        description=(
            "Come combinare il risultato del Copy Transforms con i constraint "
            "precedenti sullo stesso osso. Con un solo constraint il risultato "
            "non cambia; conta quando ci sono catene IK/FK o più constraint"
        ),
        items=MIX_MODE_ITEMS,
        default='REPLACE',
    )
    use_offset: BoolProperty(
        name="Usa offset",
        description=(
            "Somma il valore copiato alla trasformazione originale invece di "
            "sostituirla (Copy Location e Copy Scale)"
        ),
        default=False,
    )
    remove_target_shear: BoolProperty(
        name="Rimuovi shear",
        description=(
            "Corregge lo shear introdotto dal target quando le sue ossa hanno "
            "scale non uniformi (evita distorsioni visibili)"
        ),
        default=False,
    )
    stack_position: EnumProperty(
        name="Posizione nello stack",
        description=(
            "Dove inserire il constraint nella lista dell'osso. Un Copy "
            "Transforms messo dopo un IK viene sovrascritto: meglio metterlo "
            "prima, oppure in cima quando si vuole che vinca"
        ),
        items=STACK_POSITION_ITEMS,
        default='BOTTOM',
    )

    # Modulo 5: tipo di constraint da creare.
    # Default COPY_TRANSFORMS: comportamento identico alla 1.0.x.
    constraint_type: EnumProperty(
        name="Tipo di constraint",
        description=(
            "Quale trasformazione copiare. Copy Transforms copia posizione, "
            "rotazione e scala; Copy Rotation solo la rotazione, che e' il caso "
            "piu' comune per ossa di deformazione"
        ),
        items=CONSTRAINT_TYPE_ITEMS,
        default='COPY_TRANSFORMS',
    )

    # Modulo 4: diagnostica pre-flight
    diagnostic_items: CollectionProperty(type=ACTD_DiagnosticItem)
    diagnostic_is_stale: BoolProperty(default=True)
    show_diagnostics: BoolProperty(
        name="Mostra diagnostica",
        description="Apre il pannello di verifica del rig",
        default=False,
    )
    mute_state: BoolProperty(
        name="Generati mutati",
        description="Stato dell'ultimo mute globale dei constraint generati",
        default=False,
    )

    source_token: StringProperty(
        name="Token sorgente (Target)",
        description="Token che identifica le ossa sorgente da cui copiare la trasformazione (es. 'DEF_' o 'MCH_')",
        default="MCH_",
        update=_mark_preview_stale,
    )
    source_token_type: EnumProperty(
        name="Tipo token sorgente",
        description="Se il token sorgente è un prefisso o un suffisso",
        items=TOKEN_TYPE_ITEMS,
        default='PREFIX',
        update=_mark_preview_stale,
    )

    dest_token: StringProperty(
        name="Token destinazione (Owner)",
        description="Token che identifica le ossa destinazione su cui viene aggiunto il constraint (es. 'MCH_')",
        default="DEF_",
        update=_mark_preview_stale,
    )
    dest_token_type: EnumProperty(
        name="Tipo token destinazione",
        description="Se il token destinazione è un prefisso o un suffisso",
        items=TOKEN_TYPE_ITEMS,
        default='PREFIX',
        update=_mark_preview_stale,
    )

    # Menu rapido dei preset destinazione (stessa tabella _DEST_PRESETS).
    # La name resta corta ("Preset"): la label esplicativa e' disegnata a
    # tutta larghezza nel pannello, altrimenti la sidebar la tronca.
    dest_preset_choice: EnumProperty(
        name="Preset",
        description="Imposta rapidamente il token di destinazione",
        items=DEST_PRESET_ITEMS,
        # Allineato al default owner (DEF_), cosi' il menu non mostra un
        # preset diverso dal token destinazione iniziale.
        default='DEF_',
        update=_on_dest_preset_chosen,
    )
    # Avviso mostrato sotto il menu quando il preset scelto coincide con la
    # sorgente e quindi non viene applicato (vuoto = nessun avviso).
    dest_preset_notice: StringProperty(
        name="Avviso preset",
        description="Avviso sul preset di destinazione non applicato",
        default="",
    )

    custom_pattern: StringProperty(
        name="Pattern personalizzato",
        description=(
            "Template tipo '{token}{name}{side}' oppure regex con gruppo '(?P<name>...)'. "
            "Lasciare vuoto per usare la mappatura standard"
        ),
        default="",
        update=_mark_preview_stale,
    )
    use_regex: BoolProperty(
        name="Usa regex",
        description="Interpreta il pattern personalizzato come espressione regolare",
        default=False,
        update=_mark_preview_stale,
    )

    apply_mode: EnumProperty(
        name="Applica a",
        description="A quali ossa applicare i constraint",
        items=APPLY_MODE_ITEMS,
        default='ALL',
    )

    # Modulo 3: filtro per bone collection
    # Vuoto = nessun filtro: comportamento identico alla 1.0.x.
    use_collection_filter: BoolProperty(
        name="Filtra per bone collection",
        description=(
            "Limita l'operazione alle ossa che appartengono a una specifica "
            "bone collection. Utile su rig grandi per non toccare meccaniche "
            "e controller"
        ),
        default=False,
        update=_mark_preview_stale,
    )
    collection_source: StringProperty(
        name="Collection sorgente",
        description=(
            "Nome della bone collection a cui devono appartenere le ossa "
            "sorgente (vuoto = nessun filtro sulla sorgente)"
        ),
        default="",
        update=_mark_preview_stale,
    )
    collection_dest: StringProperty(
        name="Collection destinazione",
        description=(
            "Nome della bone collection a cui devono appartenere le ossa "
            "destinazione (vuoto = nessun filtro sulla destinazione)"
        ),
        default="",
        update=_mark_preview_stale,
    )
    deform_only: BoolProperty(
        name="Solo ossa deform",
        description=(
            "Considera solo le ossa con 'Deform' attivo, escludendo le ossa "
            "di controllo e le meccaniche"
        ),
        default=False,
        update=_mark_preview_stale,
    )
    influence: FloatProperty(
        name="Influenza",
        description="Influenza del constraint (0-1)",
        default=1.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )
    target_space: EnumProperty(
        name="Spazio target",
        description="Spazio del target per Copy Transforms",
        items=SPACE_ITEMS,
        default='WORLD',
    )
    owner_space: EnumProperty(
        name="Spazio owner",
        description="Spazio dell'owner per Copy Transforms",
        items=SPACE_ITEMS,
        default='WORLD',
    )
    existing_mode: EnumProperty(
        name="Constraint esistenti",
        description="Mantieni o sostituisci i constraint Copy Transforms già presenti sull'osso destinazione",
        items=EXISTING_MODE_ITEMS,
        default='KEEP',
    )
    # Protezione REPLACE: senza questa conferma esplicita il popup non
    # permette di rimuovere anche i constraint manuali.
    replace_conferma_manuali: BoolProperty(
        name="Conferma rimozione manuali",
        description=(
            "Abilita 'Rimuovi tutto' nel popup di conferma della modalità "
            "Sostituisci: senza questa conferma i constraint manuali non "
            "vengono rimossi"
        ),
        default=False,
    )
    update_mode: EnumProperty(
        name="Modalità",
        description="Crea solo se mancante oppure aggiorna quelli esistenti generati dall'addon",
        items=UPDATE_MODE_ITEMS,
        default='MISSING_ONLY',
    )
    avoid_duplicates: BoolProperty(
        name="Evita duplicati",
        description="Non creare un constraint se sull'osso ne esiste già uno manuale equivalente",
        default=True,
    )
    resolve_ambiguous: BoolProperty(
        name="Risolvi ambiguità",
        description=(
            "Se attivo, le ambiguità vengono risolte automaticamente "
            "scegliendo il candidato migliore; se disattivo vengono saltate"
        ),
        default=False,
        update=_mark_preview_stale,
    )
    constraint_name: StringProperty(
        name="Nome constraint",
        description="Nome assegnato ai constraint creati",
        default=DEFAULT_CONSTRAINT_NAME,
    )

    # --- Anteprima / report ---
    preview_items: CollectionProperty(type=ACTD_MappingItem)
    preview_index: IntProperty(default=0)
    # Report generico: resta allineato all'ultima azione eseguita per
    # compatibilita' con la 1.1.x e con le suite di test. La UI legge invece le
    # proprieta' dedicate qui sotto: cosi' anteprima, diagnostica e
    # manutenzione non si sovrascrivono piu' a vicenda.
    last_report: StringProperty(default="")
    # Stato isolato per pannello (testo mostrato dalla UI).
    preview_report: StringProperty(default="")
    diagnostic_report: StringProperty(default="")
    maintenance_report: StringProperty(default="")
    preview_is_stale: BoolProperty(default=False)
    preview_armature: StringProperty(default="")


# =============================================================================
#  UTILITÀ CONTEXT E REPORT
# =============================================================================

def _poll_armature(context) -> bool:
    obj = context.object
    return obj is not None and obj.type == 'ARMATURE' and obj.mode == 'POSE'


def _settings(context) -> ACTD_Settings:
    return context.scene.actd_settings


def _clear_collection(collection):
    try:
        collection.clear()
    except Exception:
        for i in range(len(collection) - 1, -1, -1):
            collection.remove(i)


def _store_preview(settings, arm_obj, results):
    _clear_collection(settings.preview_items)
    for res in results:
        item = settings.preview_items.add()
        item.source_name = res.source
        item.dest_name = res.dest
        item.status = res.status
        item.note = res.note
    settings.preview_is_stale = False
    settings.preview_armature = arm_obj.name if arm_obj else ""
    if settings.preview_index >= len(settings.preview_items):
        settings.preview_index = max(0, len(settings.preview_items) - 1)


def _build_report(created, updated, skipped, replaced,
                  ambiguous, unm_src, unm_dst, errors, warnings=None) -> str:
    lines = [
        f"Constraint creati: {created}",
        f"Constraint aggiornati: {updated}",
        f"Constraint saltati: {skipped}",
        f"Constraint sostituiti (rimossi): {replaced}",
        f"Coppie ambigue: {ambiguous}",
        f"Ossa sorgente senza match: {unm_src}",
        f"Ossa destinazione senza match: {unm_dst}",
    ]
    if warnings:
        lines.append(f"Avvisi ({len(warnings)}):")
        for warn in warnings[:10]:
            lines.append(f"  - {warn}")
    if errors:
        lines.append(f"Errori ({len(errors)}):")
        for err in errors[:10]:
            lines.append(f"  - {err}")
    return "\n".join(lines)


# --- Report isolati per pannello ---------------------------------------------
# Ogni azione aggiorna la propria proprieta' e, per compatibilita' con la 1.1.x
# e con le suite di test, anche `last_report` (ultimo report generico). La UI
# legge solo la proprieta' dedicata al pannello: la diagnostica non cancella il
# report di anteprima e la manutenzione non duplica quello dell'anteprima.

def _set_preview_report(settings, text):
    """Scrive il report del pannello anteprima/mappatura."""
    settings.preview_report = text
    settings.last_report = text


def _set_maintenance_report(settings, text):
    """Scrive il report del pannello manutenzione."""
    settings.maintenance_report = text
    settings.last_report = text


def _diagnostic_report_text(findings):
    """Testo del report di diagnostica, con prefisso di livello."""
    return "\n".join(
        f"[{level.upper()}] {text}" for level, text in findings
    ) or "Nessun problema rilevato."


# --- Helper di visualizzazione ------------------------------------------------
# Blender tronca le label piu' larghe della sidebar (troncamento con '…' oltre
# ~40 caratteri): i report vanno spezzati in righe corte e disegnati una label
# per riga. La larghezza 34 entra nella sidebar reale anche con i margini.
_UI_TEXT_WIDTH = 34


def _ui_report_lines(text, width=_UI_TEXT_WIDTH):
    """Righe pronte per le label della UI: testo tradotto e spezzato.

    Usato da anteprima, diagnostica e manutenzione. Le righe vuote diventano
    uno spazio, altrimenti Blender non disegna la label e il paragrafo si
    compatta.
    """
    if not text:
        return []
    lines = _wrap_text(_translate_report_text(text), width=width)
    return [line if line else " " for line in lines]


def _draw_report_text(layout, text, width=_UI_TEXT_WIDTH):
    """Disegna un report tradotto e spezzato su piu' label Blender."""
    for line in _ui_report_lines(text, width=width):
        layout.label(text=line)


# =============================================================================
#  UI LIST
# =============================================================================

# Freccia che associa sorgente e destinazione nella lista di mappatura e punto
# medio che separa la destinazione dall'etichetta di stato.
_MAPPING_ARROW = "→"
_MAPPING_DOT = "·"


def _mapping_row_data(item):
    """Testi e icona di una riga della lista di mappatura.

    Restituisce `(sorgente, destinazione, stato, icona)`. Lo stato viene
    tradotto solo al momento del disegno con `pgettext`: i dati salvati in
    `ACTD_MappingItem` (e quindi i `MappingResult` da cui derivano) restano
    invariati. Un nome assente diventa "-" per non lasciare la cella vuota.
    Tenuta separata da `draw_item` per poterla verificare nei test headless.
    """
    label, icon_name = STATUS_META.get(item.status, ("?", 'QUESTION'))
    return (
        item.source_name or "-",
        item.dest_name or "-",
        bpy.app.translations.pgettext(label),
        icon_name,
    )


class ACTD_UL_mapping(UIList):
    """Lista delle coppie di mappatura con stato evidenziato."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index=0, flt_flag=0):
        source, dest, status_label, status_icon = _mapping_row_data(item)

        # La UIList impila le voci su una sola riga: le chiamate dirette su
        # `layout` finiscono affiancate (era il caso dello split fisso
        # 0.38/0.62, che troncava entrambi i nomi). La `column` fa crescere
        # l'altezza della voce e permette due righe vere, una per nome.
        column = layout.column(align=True)

        # Prima riga: icona di stato + nome sorgente, a tutta larghezza.
        column.label(text=source, icon=status_icon)

        # Seconda riga: freccia di associazione, destinazione e stato. Lo
        # stato sta in coda alla stessa label: senza colonne fisse i due nomi
        # usano tutta la larghezza e, quando lo spazio finisce, il troncamento
        # colpisce l'etichetta di stato (già anticipata dall'icona), non i nomi.
        column.label(
            text=(
                f"{_MAPPING_ARROW} {dest}"
                f"  {_MAPPING_DOT}  {status_label}"
            )
        )
