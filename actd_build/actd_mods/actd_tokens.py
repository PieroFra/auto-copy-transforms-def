# MODULO actd_tokens.py — token, nomi, normalizzazione e calcolo mappatura (intestazione di build, non fa parte del monolite)


# =============================================================================
#  COSTANTI / ENUM
# =============================================================================

TOKEN_TYPE_ITEMS = [
    ('PREFIX', "Prefisso", "Il token si trova all'inizio del nome"),
    ('SUFFIX', "Suffisso", "Il token si trova alla fine del nome"),
]

APPLY_MODE_ITEMS = [
    ('ALL', "Tutte le ossa", "Applica a tutte le ossa corrispondenti"),
    ('SELECTED', "Solo selezionate", "Applica solo alle ossa selezionate in Pose Mode"),
]

EXISTING_MODE_ITEMS = [
    ('KEEP', "Mantieni", "Mantiene i constraint Copy Transforms già presenti"),
    ('REPLACE', "Sostituisci", "Rimuove tutti i Copy Transforms presenti sull'osso destinazione prima di creare il nuovo"),
]

UPDATE_MODE_ITEMS = [
    ('MISSING_ONLY', "Solo se mancante", "Crea il constraint solo se non esiste già"),
    ('UPDATE', "Aggiorna esistente", "Aggiorna i constraint già creati dall'addon"),
]

SPACE_ITEMS = [
    ('WORLD', "World", "Spazio globale"),
    ('POSE', "Pose", "Spazio pose"),
    ('LOCAL_WITH_PARENT', "Local With Parent", "Spazio locale con parent"),
    ('LOCAL', "Local", "Spazio locale"),
]

SPACE_ITEMS = [
    ('WORLD', "World", "Spazio globale"),
    ('POSE', "Pose", "Spazio pose"),
    ('LOCAL_WITH_PARENT', "Local With Parent", "Spazio locale con parent"),
    ('LOCAL', "Local", "Spazio locale"),
]

MIX_MODE_ITEMS = [
    ('REPLACE', "Replace", "Usa solo il risultato del constraint: nessun mix"),
    ('BEFORE', "Before Original", "Metti il risultato prima della trasformazione originale"),
    ('AFTER', "After Original", "Applica il risultato dopo la trasformazione originale"),
    ('BEFORE_SPLIT', "Before Original (Split)", "Come Before, con spazi separati"),
    ('AFTER_SPLIT', "After Original (Split)", "Come After, con spazi separati"),
    ('BEFORE_FULL', "Before Original (Full)", "Come Before, mantenendo l'influenza sui canali"),
    ('AFTER_FULL', "After Original (Full)", "Come After, mantenendo l'influenza sui canali"),
    ('ADD', "Add", "Somma la trasformazione copiata (solo Copy Rotation)"),
    ('OFFSET', "Offset", "Applica la trasformazione come offset (solo Copy Rotation)"),
]

# Tipi di constraint supportati. 'bl_type' e' l'identificatore Blender,
# 'use_channels' elenca le opzioni canale che il tipo espone.
CONSTRAINT_TYPE_ITEMS = [
    ('COPY_TRANSFORMS', "Copy Transforms", "Copia posizione, rotazione e scala"),
    ('COPY_ROTATION', "Copy Rotation", "Copia solo la rotazione"),
    ('COPY_LOCATION', "Copy Location", "Copia solo la posizione"),
    ('COPY_SCALE', "Copy Scale", "Copia solo la scala"),
]

CONSTRAINT_TYPE_LABELS = {item[0]: item[1] for item in CONSTRAINT_TYPE_ITEMS}

# I tipi che espongono mix_mode, con i rispettivi valori ammessi.
# Copy Location e Copy Scale non hanno mix_mode: per loro si usa 'use_offset'.
MIX_MODES_BY_TYPE = {
    'COPY_TRANSFORMS': {
        'REPLACE', 'BEFORE', 'AFTER', 'BEFORE_SPLIT', 'AFTER_SPLIT',
        'BEFORE_FULL', 'AFTER_FULL',
    },
    'COPY_ROTATION': {'REPLACE', 'ADD', 'BEFORE', 'AFTER', 'OFFSET'},
}

STACK_POSITION_ITEMS = [
    ('BOTTOM', "In fondo", "Aggiunge il constraint in fondo alla lista (comportamento classico)"),
    ('TOP', "In cima", "Mette il constraint in cima: vince sugli altri"),
    ('BEFORE_IK', "Prima del primo IK", "Lo inserisce subito prima del primo constraint IK"),
]

# Stato delle righe di mappatura: etichetta sorgente in italiano e icona.
# La traduzione avviene al momento del disegno (vedi `_mapping_row_data`), così
# la lista segue la lingua dell'interfaccia senza duplicare le tabelle.
STATUS_META = {
    'match': ("OK", 'CHECKMARK'),
    'resolved': ("Risolto", 'INFO'),
    'ambiguous': ("Ambiguo", 'ERROR'),
    'unmatched_src': ("Senza match", 'CANCEL'),
    'unmatched_dst': ("Senza match", 'CANCEL'),
}

DEFAULT_CONSTRAINT_NAME = "AUTO_COPY_MCH_to_DEF"
_INFLUENCE_TOL = 1e-4


# =============================================================================
#  UTILITÀ DI NORMALIZZAZIONE DEI NOMI
# =============================================================================

# Side finale con separatore: "Hand.L", "Hand_L", "Hand-L", "Hand L"
_SIDE_SUFFIX_SEP_RX = re.compile(r'^(.*?)[._\- ]([LRlr])$')
# Side iniziale con separatore: "L_Hand", "L.Hand", "L-Hand"
_SIDE_PREFIX_SEP_RX = re.compile(r'^([LRlr])[._\- ](.+)$')
# Side finale camelCase senza separatore (evita falsi positivi su UPPERCASE tipo "TAIL" o "SHOULDER")
_SIDE_BARE_RX = re.compile(r'^(.*[a-z0-9])([LR])$')

# Preserva caratteri alfanumerici Unicode (lettere accentate, ecc.) rimuovendo simboli e underscore
_CLEAN_RX = re.compile(r'[\W_]+', re.UNICODE)
_SEPARATORS = "._- "


def _clean(text: str) -> str:
    """Normalizza una stringa per il confronto: minuscole e solo alfanumerici Unicode."""
    return _CLEAN_RX.sub('', (text or '').lower())


def _wrap_text(text: str, width: int = 78):
    """Spezza il testo in righe adatte alle label della UI Blender."""
    lines = []
    for paragraph in (text or "").split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    return lines


def _local_doc_url(filename):
    """URL file:// di un documento affiancato all'addon, se esiste."""
    if "__file__" not in globals():
        return ""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, filename)
    if not os.path.isfile(path):
        return ""
    return "file:///" + quote(path.replace("\\", "/"), safe="/:")


def _split_side(name: str):
    """
    Separa un eventuale marcatore di lato (L/R) dal nome osso.
    Supporta suffissi con separatore (.L), prefissi con separatore (L_) e camelCase (HandL).
    Ritorna (base, side, trovato).
    """
    if not name:
        return name, None, False

    # 1. Suffisso con separatore: Hand.L, Hand_R
    match = _SIDE_SUFFIX_SEP_RX.match(name)
    if match and match.group(1):
        return match.group(1), match.group(2).upper(), True

    # 2. Prefisso con separatore: L_Hand, R.Hand
    match = _SIDE_PREFIX_SEP_RX.match(name)
    if match and match.group(2):
        return match.group(2), match.group(1).upper(), True

    # 3. Suffisso camelCase senza separatore: HandL, finger01R
    match = _SIDE_BARE_RX.match(name)
    if match and match.group(1):
        return match.group(1), match.group(2).upper(), True

    return name, None, False


def _name_has_token(name: str, token: str, token_type: str) -> bool:
    """Verifica (case-insensitive) se il nome contiene il token configurato."""
    if not token:
        return True
    low = name.lower()
    tok = token.lower()
    if token_type == 'PREFIX':
        return low.startswith(tok)
    return low.endswith(tok)


def _strip_token(name: str, token: str, token_type: str) -> str:
    """Rimuove il token configurato dal nome e gli eventuali separatori adiacenti."""
    if not token or not name:
        return name

    low = name.lower()
    tok = token.lower()

    if token_type == 'PREFIX' and low.startswith(tok):
        rest = name[len(token):]
        return rest.lstrip(_SEPARATORS)

    if token_type == 'SUFFIX' and low.endswith(tok):
        rest = name[:len(name) - len(token)]
        return rest.rstrip(_SEPARATORS)

    return name


def _build_template_regex(pattern: str, token: str):
    """
    Converte un template tipo "{token}{name}{side}" in una regex compilata.
    Richiede esattamente un {name} e al massimo un {side}.
    """
    if not pattern:
        return None

    # Rileva placeholder sconosciuti
    unknown = [u for u in re.findall(r'\{[^}]*\}', pattern) if u not in ('{token}', '{name}', '{side}')]
    if unknown:
        return None

    parts = re.split(r'(\{token\}|\{name\}|\{side\})', pattern)
    if parts.count('{name}') != 1 or parts.count('{side}') > 1:
        return None

    chunks = []
    for part in parts:
        if part == '{token}':
            if token:
                chunks.append(f'(?:{re.escape(token)})?')
        elif part == '{name}':
            chunks.append('(?P<name>.+?)')
        elif part == '{side}':
            # Il separatore prima del side nel template è obbligatorio per evitare che
            # (?P<name>.+?) mangi l'ultima lettera di nomi che finiscono in L/R (es. "Shoulder")
            chunks.append(r'(?:[._\- ](?P<side>[LRlr]))?')
        elif part:
            chunks.append(re.escape(part))

    try:
        return re.compile('^' + ''.join(chunks) + '$', re.IGNORECASE)
    except re.error:
        return None


def _validate_pattern(settings) -> str:
    """Ritorna un messaggio di warning se il pattern personalizzato è invalido, altrimenti ''."""
    pattern = settings.custom_pattern
    if not pattern:
        return ""

    if settings.use_regex:
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            return f"Regex non valida: {exc}"
        if "name" not in rx.groupindex:
            return "La regex deve includere il gruppo (?P<name>...)."
        return ""

    unknown = [u for u in re.findall(r'\{[^}]*\}', pattern) if u not in ('{token}', '{name}', '{side}')]
    if unknown:
        return f"Placeholder non riconosciuto: {', '.join(unknown)}"

    parts = re.split(r'(\{token\}|\{name\}|\{side\})', pattern)
    if parts.count('{name}') != 1:
        return "Il template deve contenere esattamente un {name}."
    if parts.count('{side}') > 1:
        return "Il template può contenere al massimo un {side}."
    return ""


class _Normalizer:
    """Estrae la chiave di confronto (core) e il side da un nome osso."""

    def __init__(self, token: str, token_type: str, custom_pattern: str, use_regex: bool):
        self.token = token or ''
        self.token_type = token_type
        self.rx = None
        self.rx_is_raw = False

        if custom_pattern:
            if use_regex:
                try:
                    compiled = re.compile(custom_pattern, re.IGNORECASE)
                    if "name" in compiled.groupindex:
                        self.rx = compiled
                        self.rx_is_raw = True
                except re.error:
                    self.rx = None
            else:
                self.rx = _build_template_regex(custom_pattern, self.token)
                self.rx_is_raw = False

    def has_token(self, name: str) -> bool:
        return _name_has_token(name, self.token, self.token_type)

    def core(self, name: str):
        """Ritorna (core_key, side)."""
        # 1) Pattern personalizzato
        if self.rx is not None:
            match = self.rx.search(name) if self.rx_is_raw else self.rx.match(name)
            if match:
                groups = match.groupdict()
                extracted = groups.get('name')
                if extracted:
                    side = groups.get('side')
                    side = side.upper() if side else None
                    return _clean(extracted), side

        # 2) Tentativo A: prima rimuove il side esterno, poi il token (es. "L_DEF_hand" o "DEF_hand.L")
        base_a, side_a, _ = _split_side(name)
        base_a = _strip_token(base_a, self.token, self.token_type)

        # 3) Tentativo B: prima rimuove il token, poi il side (es. "DEF_L_hand" o "hand.L_DEF")
        tmp = _strip_token(name, self.token, self.token_type)
        base_b, side_b, _ = _split_side(tmp)

        if side_a is not None and side_b is None:
            return _clean(base_a), side_a
        if side_b is not None and side_a is None:
            return _clean(base_b), side_b

        # Se entrambi trovano un side, preferisce quello che lascia il nome base più corto/pulito
        if side_a is not None and side_b is not None:
            clean_a, clean_b = _clean(base_a), _clean(base_b)
            if len(clean_b) < len(clean_a):
                return clean_b, side_b
            return clean_a, side_a

        return _clean(base_b), None


def _side_compatible(src_side, dst_side) -> bool:
    if src_side is None or dst_side is None:
        return True
    return src_side == dst_side


def _float_close(a, b, tol=_INFLUENCE_TOL) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def _suggest_constraint_name(settings) -> str:
    src = (settings.source_token or "").strip(_SEPARATORS)
    dst = (settings.dest_token or "").strip(_SEPARATORS)
    return f"AUTO_COPY_{src or 'SRC'}_to_{dst or 'DST'}"


def _effective_constraint_name(settings) -> str:
    name = (settings.constraint_name or "").strip()
    if not name or name == DEFAULT_CONSTRAINT_NAME:
        return _suggest_constraint_name(settings)
    return name


# --- Auto-prefisso -----------------------------------------------------------
# Il prefisso e' la porzione di nome che precede il primo separatore (incluso)
# oppure la prima run di maiuscole nei nomi camelCase tipo "DEFHand".
_UPPER_PREFIX_RX = re.compile(r'^([A-Z]+)(?=[A-Z][a-z]|$)')


def _extract_prefix(name):
    """Estrae il prefisso probabile da un nome osso, separatore incluso."""
    base, _side, _found = _split_side(name or "")
    base = base or ""
    positions = [base.find(sep) for sep in _SEPARATORS if sep in base]
    if positions:
        return base[:min(positions) + 1]
    match = _UPPER_PREFIX_RX.match(base)
    if match:
        return match.group(1)
    return ""


def _rank_prefixes(arm_obj):
    """Classifica i prefissi per frequenza: conteggio, lunghezza, alfabetico."""
    counts = {}
    if arm_obj is None or getattr(arm_obj, "type", None) != 'ARMATURE':
        return []
    for bone in arm_obj.data.bones:
        prefix = _extract_prefix(bone.name)
        if prefix:
            counts[prefix] = counts.get(prefix, 0) + 1
    return sorted(
        counts.items(),
        key=lambda item: (-item[1], -len(item[0]), item[0]),
    )


def _best_prefix(rank):
    """Primo prefisso ripetuto almeno due volte, oppure None."""
    for prefix, count in rank:
        if count >= 2:
            return prefix
    return None


def _guess_prefixes(src_obj, dst_obj):
    """Stima (sorgente, destinazione, affidabile, dettaglio) dai nomi osso.

    Con la stessa armatura le due stime non possono essere indipendenti: si
    prendono i due prefissi piu' frequenti, privilegiando i default storici
    DEF_/MCH_ in caso di parita' (l'ordine alfabetico li mette davanti).
    """
    src_rank = _rank_prefixes(src_obj)
    dst_rank = _rank_prefixes(dst_obj)

    if src_obj is dst_obj:
        reliable = [prefix for prefix, count in src_rank if count >= 2]
        if len(reliable) >= 2:
            return (
                reliable[0], reliable[1], True,
                "Prefissi ricavati dalla stessa armatura.",
            )
        if len(reliable) == 1:
            return (
                reliable[0], "MCH_", False,
                "Un solo prefisso ripetuto: destinazione lasciata a MCH_.",
            )
        return (
            "DEF_", "MCH_", False,
            "Nessun prefisso ripetuto almeno 2 volte.",
        )

    src = _best_prefix(src_rank)
    dst = _best_prefix(dst_rank)
    if not src or not dst:
        return (
            "DEF_", "MCH_", False,
            "Prefissi non affidabili in una delle due armature.",
        )

    if src == dst:
        alternative = next(
            (p for p, count in dst_rank if count >= 2 and p != src), None
        )
        if alternative:
            return (
                src, alternative, True,
                "Prefisso destinazione uguale alla sorgente: usato il secondo.",
            )
        return (
            src, "MCH_", False,
            "Prefisso destinazione uguale alla sorgente: usato MCH_.",
        )

    return (
        src, dst, True,
        "Prefissi ricavati dalle due armature.",
    )


# =============================================================================
#  MAPPATURA
# =============================================================================

class MappingResult:
    __slots__ = ("source", "dest", "status", "note")

    def __init__(self, source: str, dest: str, status: str, note: str = ""):
        self.source = source
        self.dest = dest
        self.status = status
        self.note = note


def _collection_names(armature):
    """Nomi delle bone collection disponibili (vuoto su Blender 3.6)."""
    collections = getattr(armature, "collections", None)
    if collections is None:
        return []
    try:
        return sorted(c.name for c in collections)
    except (AttributeError, TypeError):
        return []


def _bone_collection_names(bone, armature):
    """Nomi delle bone collection a cui appartiene un osso.

    Blender 4.x/5.x usano Armature.collections; su 3.6 esistono ancora i layer,
    quindi facciamo fallback sui layer per non rompere le versioni vecchie.
    """
    collections = getattr(bone, "collections", None)
    if collections is not None:
        try:
            return {c.name for c in collections}
        except (AttributeError, TypeError):
            pass
    # Fallback 3.6: layer dell'armatura -> ossa del layer
    layers = getattr(armature, "layers", None)
    if layers is None:
        return set()
    names = set()
    try:
        for layer in layers:
            for layer_bone in layer.bones:
                if layer_bone.name == bone.name:
                    names.add(layer.name)
    except (AttributeError, TypeError):
        pass
    return names


def _collection_filter_passes(bone, armature, wanted):
    """True se l'osso passa il filtro di collection richiesto."""
    if not wanted:
        return True
    return wanted in _bone_collection_names(bone, armature)


def _bone_passes_filters(bone, armature, settings, is_source):
    """Applica tutti i filtri (collection + deform) a un osso."""
    if not getattr(settings, "use_collection_filter", False):
        return True

    if getattr(settings, "deform_only", False) and not getattr(bone, "use_deform", True):
        return False

    wanted = (
        getattr(settings, "collection_source", "")
        if is_source
        else getattr(settings, "collection_dest", "")
    )
    return _collection_filter_passes(bone, armature, (wanted or "").strip())


def _matrix_axes_diff(mat_a, mat_b):
    """Differenza massima di orientamento (in gradi) tra due matrici 3x3."""
    try:
        quat_a = mat_a.to_quaternion()
        quat_b = mat_b.to_quaternion()
    except (AttributeError, ValueError):
        return 0.0
    delta = quat_a.rotation_difference(quat_b).angle
    return math.degrees(abs(delta))


def _bone_has_driver(pose_bone, owner_obj):
    """True se qualche canale di trasformazione dell'osso ha un driver."""
    anim = getattr(owner_obj, "animation_data", None)
    if anim is None:
        return False
    path_prefix = f'pose.bones["{pose_bone.name}"]'
    for fcurve in anim.drivers:
        if fcurve.data_path.startswith(path_prefix):
            return True
    return False


def diagnose_rig(arm_obj, settings):
    """Analisi pre-flight della mappatura. Ritorna una lista di (livello, testo).

    Livelli: 'error' (blocca il risultato corretto), 'warning' (probabile
    problema), 'info' (suggerimento). Non modifica nulla.
    """
    findings = []

    if arm_obj is None or arm_obj.type != 'ARMATURE':
        findings.append(('error', "Nessuna armatura attiva."))
        return findings

    src_obj = _source_obj(arm_obj, settings)
    src_err = validate_source_object(arm_obj, src_obj)
    if src_err:
        findings.append(('error', src_err))
        return findings

    pattern_err = _validate_pattern(settings)
    if pattern_err:
        findings.append(('error', pattern_err))
        return findings

    # Filtri che non corrispondono a nulla: setup quasi sempre sbagliato
    if getattr(settings, "use_collection_filter", False):
        for which, name, owner in (
            ("sorgente", getattr(settings, "collection_source", ""), src_obj),
            ("destinazione", getattr(settings, "collection_dest", ""), arm_obj),
        ):
            wanted = (name or "").strip()
            if not wanted:
                continue
            available = _collection_names(owner.data)
            if wanted not in available:
                findings.append((
                    'warning',
                    f"Collection {which} '{wanted}' inesistente su "
                    f"'{owner.name}'. Disponibili: "
                    + (", ".join(available) if available else "nessuna"),
                ))

    results = compute_mapping(arm_obj, settings)
    valid = [r for r in results if r.status in ('match', 'resolved')]
    ambiguous = [r for r in results if r.status == 'ambiguous']

    if not valid:
        # Zero coppie significa quasi sempre token sbagliati: e' un errore.
        if results:
            detail = (
                f"{sum(1 for r in results if r.status == 'ambiguous')} ambigue, "
                f"{sum(1 for r in results if r.status == 'unmatched_src')} senza "
                f"destinazione"
            )
        else:
            detail = "nessuna corrispondenza"
        findings.append((
            'error',
            f"Nessuna coppia valida ({detail}): non verrebbe creato nulla. "
            f"Controlla i token e il pattern.",
        ))

    if ambiguous:
        preview = ", ".join(r.source for r in ambiguous[:5])
        if len(ambiguous) > 5:
            preview += ", …"
        findings.append((
            'warning',
            f"{len(ambiguous)} ossa ambigue ({preview}). "
            f"Con 'Risolvi ambiguità' l'addon sceglie automaticamente.",
        ))

    # --- Analisi per coppia ---
    src_bones = src_obj.data.bones
    dst_bones = arm_obj.data.bones
    rest_mismatch = []
    missing_src = []
    driven_dst = []
    driven_src = []
    same_parent = 0
    different_parent = 0

    for r in valid:
        src_bone = src_bones.get(r.source)
        dst_bone = dst_bones.get(r.dest)
        if src_bone is None:
            missing_src.append(r.source)
            continue
        if dst_bone is None:
            continue

        # Rest orientation: se le ossa hanno roll/orientamento molto diversi,
        # un Copy Transforms in Local_With_Parent produce pose inattese.
        try:
            diff = _matrix_axes_diff(src_bone.matrix_local.to_3x3(),
                                     dst_bone.matrix_local.to_3x3())
            if diff > 15.0:
                rest_mismatch.append((r.source, r.dest, round(diff, 1)))
        except (AttributeError, ValueError):
            pass

        # Posizione nella gerarchia: informazione per la scelta dello spazio
        src_parent = src_bone.parent.name if src_bone.parent else ""
        dst_parent = dst_bone.parent.name if dst_bone.parent else ""
        if src_parent == dst_parent:
            same_parent += 1
        else:
            different_parent += 1

        if _bone_has_driver(arm_obj.pose.bones[r.dest], arm_obj):
            driven_dst.append(r.dest)
        if src_obj is not arm_obj and _bone_has_driver(
            src_obj.pose.bones[r.source], src_obj
        ):
            driven_src.append(r.source)

    if missing_src:
        findings.append((
            'error',
            f"{len(missing_src)} ossa sorgente non trovate in Pose: "
            + ", ".join(missing_src[:5]),
        ))

    if rest_mismatch:
        detail = ", ".join(f"{s}→{d} ({deg}°)" for s, d, deg in rest_mismatch[:4])
        findings.append((
            'warning',
            f"{len(rest_mismatch)} coppie con orientamento di rest molto diverso "
            f"(>15°): {detail}."
            f" Con spazi LOCAL la posa potrebbe risultare ruotata: "
            f"valuta WORLD o riallinea i roll.",
        ))

    if driven_dst:
        findings.append((
            'warning',
            f"{len(driven_dst)} ossa destinazione hanno già driver sulle "
            f"trasformazioni: "
            + ", ".join(driven_dst[:5])
            + ". Il constraint si sommerà al driver.",
        ))

    if driven_src:
        findings.append((
            'info',
            f"{len(driven_src)} ossa sorgente sono animate da driver "
            f"(l'addon copierà il risultato finale, non il driver).",
        ))

    # Spazio consigliato
    if valid:
        if same_parent and not different_parent:
            suggested = 'LOCAL_WITH_PARENT'
            why = "tutte le coppie hanno lo stesso parent"
        elif different_parent and not same_parent:
            suggested = 'WORLD'
            why = "le coppie stanno in gerarchie diverse"
        else:
            suggested = 'WORLD'
            why = "gerarchie miste: WORLD è il compromesso più sicuro"
        current = getattr(settings, "owner_space", 'WORLD')
        if current != suggested:
            findings.append((
                'info',
                f"Spazio consigliato: {suggested} ({why}). Attuale: {current}.",
            ))

    # Conflitti simmetrici già rilevati dal mapping sono esposti nell'anteprima.

    return findings

def _store_diagnostics(settings, findings):
    """Salva esito e report della diagnostica nelle proprietà della Scene."""
    _clear_collection(settings.diagnostic_items)
    for level, text in findings:
        item = settings.diagnostic_items.add()
        item.level = level
        item.text = text
    settings.diagnostic_is_stale = False
    # Report testuale della sola diagnostica: non tocca preview_report, cosi'
    # il pannello di anteprima conserva il suo esito dopo "Verifica rig".
    settings.diagnostic_report = _diagnostic_report_text(findings)


def compute_mapping(arm_obj, settings):
    """Calcola la mappatura sorgente -> destinazione."""
    src_norm = _Normalizer(
        settings.source_token, settings.source_token_type,
        settings.custom_pattern, settings.use_regex,
    )
    dst_norm = _Normalizer(
        settings.dest_token, settings.dest_token_type,
        settings.custom_pattern, settings.use_regex,
    )

    # Modulo 1: le ossa sorgente possono appartenere a un'altra armatura
    src_obj = _source_obj(arm_obj, settings)
    src_bones = src_obj.data.bones
    all_bone_names = [b.name for b in arm_obj.data.bones]

    # Gestione intelligente dei token vuoti per evitare auto-collisioni
    if src_norm.token and not dst_norm.token:
        src_names = [n for n in all_bone_names if src_norm.has_token(n)]
        src_set = set(src_names)
        dst_names = [n for n in all_bone_names if n not in src_set]
    elif dst_norm.token and not src_norm.token:
        dst_names = [n for n in all_bone_names if dst_norm.has_token(n)]
        dst_set = set(dst_names)
        src_names = [n for n in all_bone_names if n not in dst_set]
    else:
        src_names = [n for n in all_bone_names if src_norm.has_token(n)]
        dst_names = [n for n in all_bone_names if dst_norm.has_token(n)]

    # Con armature separate le ossa sorgente sono quelle dell'armatura sorgente:
    # così la destinazione non deve contenere per forza una copia delle ossa DEF.
    if src_obj is not arm_obj:
        src_names = [b.name for b in src_bones if src_norm.has_token(b.name)]

    # Indice delle destinazioni per chiave di confronto
    dst_index = {}
    for name in dst_names:
        # Modulo 3: filtri applicati alle ossa destinazione
        if not _bone_passes_filters(
            arm_obj.data.bones[name], arm_obj.data, settings, is_source=False
        ):
            continue
        core, side = dst_norm.core(name)
        if core:
            dst_index.setdefault(core, []).append((name, side))

    results = []
    used_dst = set()
    dst_assignments = {}

    for src_name in src_names:
        # Modulo 3: filtri applicati alle ossa sorgente
        src_bone = src_bones.get(src_name)
        if src_bone is not None and not _bone_passes_filters(
            src_bone, src_obj.data, settings, is_source=True
        ):
            continue
        core, side = src_norm.core(src_name)
        if not core:
            results.append(MappingResult(src_name, "", 'unmatched_src', "Nome base vuoto"))
            continue

        # Esclude sempre il self-matching (un osso non può copiare da se stesso)
        candidates = [c for c in dst_index.get(core, []) if c[0] != src_name]

        if side is not None:
            candidates = [c for c in candidates if _side_compatible(side, c[1])]

        if len(candidates) == 1:
            dst = candidates[0][0]
            results.append(MappingResult(src_name, dst, 'match'))
            used_dst.add(dst)
            dst_assignments.setdefault(dst, []).append(src_name)
        elif len(candidates) > 1:
            note = "Candidati: " + ", ".join(c[0] for c in candidates)
            if settings.resolve_ambiguous:
                # Preferisce chi ha lo stesso side esplicito, poi il nome più corto
                ordered = sorted(
                    candidates,
                    key=lambda c: (0 if (side and c[1] == side) else 1, len(c[0]), c[0]),
                )
                chosen = ordered[0][0]
                results.append(MappingResult(src_name, chosen, 'resolved', note))
                used_dst.add(chosen)
                dst_assignments.setdefault(chosen, []).append(src_name)
            else:
                results.append(MappingResult(src_name, "", 'ambiguous', note))
        else:
            results.append(MappingResult(src_name, "", 'unmatched_src'))

    # Rilevamento conflitti simmetrici: più sorgenti che puntano alla stessa destinazione
    conflicts = {d: s for d, s in dst_assignments.items() if len(s) > 1}
    if conflicts:
        for res in results:
            if res.status in ('match', 'resolved') and res.dest in conflicts:
                contended_dst = res.dest
                res.status = 'ambiguous'
                res.dest = ""
                res.note = (
                    f"Destinazione '{contended_dst}' contesa da: "
                    + ", ".join(conflicts[contended_dst])
                )
                used_dst.discard(contended_dst)

    # Ossa destinazione rimaste senza sorgente
    for name in dst_names:
        if name not in used_dst:
            results.append(MappingResult("", name, 'unmatched_dst'))

    return results


# =============================================================================
#  GESTIONE CONSTRAINT E SELEZIONE
# =============================================================================

def _constraint_type(settings) -> str:
    """Tipo di constraint richiesto, con fallback sul default storico."""
    value = getattr(settings, "constraint_type", 'COPY_TRANSFORMS')
    if value not in CONSTRAINT_TYPE_LABELS:
        return 'COPY_TRANSFORMS'
    return value


def _resolved_mix_mode(settings, con_type):
    """Ritorna (valore_da_impostare, nota) per il mix, adattato al tipo.

    I tipi di constraint hanno enum di mix diversi: COPY_ROTATION non conosce
    le varianti *_SPLIT e *_FULL, mentre COPY_LOCATION e COPY_SCALE non hanno
    proprio mix_mode. In quei casi si degrada al valore piu' vicino invece di
    far fallire l'assegnazione in silenzio.
    """
    requested = getattr(settings, "mix_mode", 'REPLACE') or 'REPLACE'
    if requested == 'REPLACE':
        return ('REPLACE', "")

    allowed = MIX_MODES_BY_TYPE.get(con_type)
    if not allowed:
        return (
            None,
            f"Il tipo {CONSTRAINT_TYPE_LABELS.get(con_type, con_type)} non "
            f"supporta 'Mix': l'opzione viene ignorata.",
        )

    if requested in allowed:
        return (requested, "")

    # BEFORE_SPLIT / BEFORE_FULL -> BEFORE, AFTER_SPLIT / AFTER_FULL -> AFTER
    fallback = None
    for prefix in ("BEFORE", "AFTER"):
        if requested.startswith(prefix) and prefix in allowed:
            fallback = prefix
            break
    if fallback is None:
        return (
            'REPLACE',
            f"Il valore di mix '{requested}' non e' valido per "
            f"{CONSTRAINT_TYPE_LABELS.get(con_type, con_type)}: usato REPLACE.",
        )
    return (
        fallback,
        f"Mix '{requested}' non disponibile per "
        f"{CONSTRAINT_TYPE_LABELS.get(con_type, con_type)}: usato '{fallback}'.",
    )


def _constraint_supports(con_type, prop_name):
    """True se il tipo di constraint espone la proprieta' indicata."""
    rna = {
        'COPY_TRANSFORMS': bpy.types.CopyTransformsConstraint,
        'COPY_ROTATION': bpy.types.CopyRotationConstraint,
        'COPY_LOCATION': bpy.types.CopyLocationConstraint,
        'COPY_SCALE': bpy.types.CopyScaleConstraint,
    }.get(con_type)
    if rna is None:
        return False
    return prop_name in rna.bl_rna.properties


def _constraint_supports_offset(con_type):
    """True se use_offset e' indipendente dal mix.

    Su Copy Rotation use_offset e' solo una scorciatoia di mix_mode OFFSET:
    impostarlo sovrascriverebbe il mix scelto. Restano Copy Location e
    Copy Scale, dove use_offset e' una proprieta' autonoma.
    """
    return (
        _constraint_supports(con_type, "use_offset")
        and not _constraint_supports(con_type, "mix_mode")
    )


# --- Apprendimento del pattern da un constraint esistente -------------------
# Metacaratteri regex che renderebbero un token non letterale. I separatori
# . _ - e lo spazio sono esclusi: nei token sono normali caratteri letterali.
_META_RX = set("*+?[](){}|^$\\")


def _infer_token_rule(owner_name, source_name):
    """Deduce (src, dst, tipo_src, tipo_dst) dal nome owner e dal subtarget.

    Usa la longest common substring: cio' che resta ai lati e' il token.
    Ritorna None se i nomi sono identici, se il lato non e' univoco o se il
    residuo e' solo un marcatore di lato (L/R).
    """
    owner = owner_name or ""
    source = source_name or ""
    if not owner or not source or owner == source:
        return None

    matcher = difflib.SequenceMatcher(None, owner, source)
    match = matcher.find_longest_match(0, len(owner), 0, len(source))
    if match.size == 0:
        return None

    dst_prefix = owner[:match.a]
    dst_suffix = owner[match.a + match.size:]
    src_prefix = source[:match.b]
    src_suffix = source[match.b + match.size:]

    # La LCS puo' inglobare il separatore adiacente ("MCH_Hand" vs "DEF_Hand"
    # trova "-Hand"): il separatore va spostato nel token, non perso.
    if match.size:
        first = owner[match.a]
        last = owner[match.a + match.size - 1]
        if dst_prefix and src_prefix and first in _SEPARATORS:
            dst_prefix += first
            src_prefix += first
        if dst_suffix and src_suffix and last in _SEPARATORS:
            dst_suffix = last + dst_suffix
            src_suffix = last + src_suffix

    if dst_prefix and src_prefix and not dst_suffix and not src_suffix:
        src_token, dst_token, token_type = src_prefix, dst_prefix, 'PREFIX'
    elif dst_suffix and src_suffix and not dst_prefix and not src_prefix:
        src_token, dst_token, token_type = src_suffix, dst_suffix, 'SUFFIX'
    else:
        return None

    if not src_token or not dst_token or src_token == dst_token:
        return None

    # "Hand.L" -> "Hand.R" non deve produrre i token "R"/"L".
    if _clean(src_token) in ('l', 'r') or _clean(dst_token) in ('l', 'r'):
        return None

    return src_token, dst_token, token_type, token_type


def _majority_token_rule(rules):
    """Regola di token con maggioranza assoluta, oppure None."""
    valid = [rule for rule in rules if rule]
    if not valid:
        return None
    counts = {}
    for rule in valid:
        counts[rule] = counts.get(rule, 0) + 1
    best = max(counts.items(), key=lambda item: item[1])[0]
    if counts[best] / float(len(rules)) > 0.5:
        return best
    return None


def _apply_learned_settings(settings, con):
    """Copia tipo, influenza, spazi e mix dal constraint nelle impostazioni."""
    notes = []
    con_type = getattr(con, "type", "")
    if con_type not in CONSTRAINT_TYPE_LABELS:
        return [f"Tipo '{con_type}' non supportato: impostazioni invariate."]

    settings.constraint_type = con_type
    try:
        settings.influence = float(con.influence)
    except (TypeError, ValueError):
        notes.append("Influenza non leggibile.")

    for prop in ("target_space", "owner_space", "mix_mode"):
        if not _constraint_supports(con_type, prop):
            continue
        value = getattr(con, prop, None)
        if value is None:
            continue
        try:
            setattr(settings, prop, value)
        except (TypeError, ValueError):
            notes.append(f"Valore '{value}' non valido per {prop}.")

    if _constraint_supports_offset(con_type):
        settings.use_offset = bool(getattr(con, "use_offset", False))
    if _constraint_supports(con_type, "remove_target_shear"):
        settings.remove_target_shear = bool(
            getattr(con, "remove_target_shear", False)
        )

    target = getattr(con, "target", None)
    if target is not None:
        if target.type == 'ARMATURE':
            settings.source_object = target
        else:
            notes.append("Target non armatura: sorgente invariata.")
    return notes


def _source_obj(arm_obj, settings):
    """Oggetto da cui vengono copiate le trasformazioni.

    Modulo 1: se 'source_object' non e' impostato (o non e' un'armatura) si usa
    la stessa armatura di destinazione, quindi il default resta invariato.
    """
    src = getattr(settings, "source_object", None) if settings is not None else None
    if src is None or src.type != 'ARMATURE':
        return arm_obj
    return src


def _collection_search_available(owner):
    """True se l'armatura espone le bone collection ricercabili.

    Blender 4.x/5.x hanno Armature.collections; su 3.6 l'API non esiste e la
    UI deve ripiegare sul campo testo. Accetta anche None/oggetti non armatura:
    in quel caso non c'e' nulla su cui cercare.
    """
    if owner is None or getattr(owner, "type", None) != 'ARMATURE':
        return False
    data = getattr(owner, "data", None)
    return getattr(data, "collections", None) is not None


def _collection_search_armature(context, settings, is_source):
    """Armatura su cui cercare la bone collection per il prop_search.

    Ritorna l'armatura sorgente (o destinazione) quando l'API bone collection
    e' disponibile; ritorna None quando manca l'armatura o l'API (3.6/4.x):
    in quel caso il pannello usa esplicitamente il campo testo.
    """
    arm_obj = getattr(context, "object", None)
    if arm_obj is None:
        return None
    owner = _source_obj(arm_obj, settings) if is_source else arm_obj
    return owner if _collection_search_available(owner) else None
