# MODULO actd_i18n.py — traduzioni e localizzazione IT/EN (intestazione di build, non fa parte del monolite)


def _is_english_ui():
    """True quando la lingua dell'interfaccia Blender e' inglese."""
    try:
        locale = bpy.app.translations.locale or ""
    except Exception:
        locale = ""
    return locale.lower().startswith("en")


# Il report testuale viene generato in italiano (utile per i test e per i log).
# In UI inglese traduciamo solo le righe note al momento della visualizzazione.
_REPORT_PATTERNS = (
    (re.compile(r"^Anteprima completata su '(.+)'\.$"),
     r"Preview completed on '\1'."),
    (re.compile(r"^Coppie valide: (\d+)$"), r"Valid pairs: \1"),
    (re.compile(r"^Coppie ambigue: (\d+)$"), r"Ambiguous pairs: \1"),
    (re.compile(r"^Ossa sorgente senza match: (\d+)$"),
     r"Source bones without match: \1"),
    (re.compile(r"^Ossa destinazione senza match: (\d+)$"),
     r"Target bones without match: \1"),
    (re.compile(r"^Constraint creati: (\d+)$"), r"Constraints created: \1"),
    (re.compile(r"^Constraint aggiornati: (\d+)$"),
     r"Constraints updated: \1"),
    (re.compile(r"^Constraint saltati: (\d+)$"), r"Constraints skipped: \1"),
    (re.compile(r"^Constraint sostituiti \(rimossi\): (\d+)$"),
     r"Constraints replaced (removed): \1"),
    (re.compile(r"^Avvisi \((\d+)\):$"), r"Warnings (\1):"),
    (re.compile(r"^Errori \((\d+)\):$"), r"Errors (\1):"),
    (re.compile(r"^Righe esportate: (\d+)$"), r"Rows exported: \1"),
    (re.compile(r"^Report salvato in: (.+)$"), r"Report saved to: \1"),
    (re.compile(r"^Constraint rimossi: (\d+)$"), r"Constraints removed: \1"),
    (re.compile(r"^Nessun problema rilevato\.$"), r"No issues found."),
)


# -----------------------------------------------------------------------------
#  TRADUZIONE DELLA DIAGNOSTICA (solo visualizzazione)
# -----------------------------------------------------------------------------
# I messaggi di diagnose_rig restano in italiano: sono dati usati dai test e
# dal registro dei report. La traduzione avviene solo quando si disegna la UI.

# Frammenti dinamici annidati dentro i messaggi (es. "3 ambigue, 2 senza
# destinazione" dentro "Nessuna coppia valida (...)").
_DETAIL_PATTERNS = (
    (re.compile(r"^(\d+) ambigue$"), r"\1 ambiguous"),
    (re.compile(r"^(\d+) senza destinazione$"), r"\1 without target"),
    (re.compile(r"^nessuna corrispondenza$"), r"no match"),
    (re.compile(r"^nessuna$"), r"none"),
)

# Motivazioni dello spazio consigliato.
_SPACE_WHY_TRANSLATIONS = {
    "tutte le coppie hanno lo stesso parent": (
        "all pairs share the same parent"
    ),
    "le coppie stanno in gerarchie diverse": (
        "the pairs live in different hierarchies"
    ),
    "gerarchie miste: WORLD è il compromesso più sicuro": (
        "mixed hierarchies: WORLD is the safest compromise"
    ),
}


def _translate_detail(text):
    """Traduce un frammento dinamico di un messaggio diagnostico."""
    for pattern, replacement in _DETAIL_PATTERNS:
        new_text = pattern.sub(replacement, text)
        if new_text != text:
            return new_text
    return text


def _translate_missing_collection(match):
    """Collection sorgente/destinazione non trovata sull'armatura."""
    which = "source" if match.group(1) == "sorgente" else "destination"
    available = _translate_detail(match.group(4).strip())
    return (
        f"Collection {which} '{match.group(2)}' missing on "
        f"'{match.group(3)}'. Available: {available}"
    )


def _translate_no_valid_pair(match):
    """Nessuna coppia valida: il dettaglio e' una lista di conteggi."""
    detail = ", ".join(
        _translate_detail(part.strip())
        for part in match.group(1).split(",")
    )
    return (
        f"No valid pair ({detail}): nothing would be created. "
        f"Check the tokens and the pattern."
    )


def _translate_suggested_space(match):
    """Spazio consigliato: traduce anche la motivazione tra parentesi."""
    why = _SPACE_WHY_TRANSLATIONS.get(match.group(2), match.group(2))
    return (
        f"Suggested space: {match.group(1)} ({why}). "
        f"Current: {match.group(3)}."
    )


# Messaggi dinamici della diagnostica pre-flight.
_DIAGNOSTIC_PATTERNS = (
    (re.compile(r"^Nessuna armatura attiva\.$"), r"No active armature."),
    (re.compile(r"^Armatura sorgente non valida\.$"),
     r"Source armature is not valid."),
    (re.compile(r"^L'oggetto sorgente non e' un'armatura\.$"),
     r"The source object is not an armature."),
    (re.compile(r"^L'armatura sorgente e' in Edit Mode\.$"),
     r"The source armature is in Edit Mode."),
    (re.compile(r"^L'armatura sorgente e' nascosta\.$"),
     r"The source armature is hidden."),
    (re.compile(r"^L'armatura sorgente non ha ossa\.$"),
     r"The source armature has no bones."),
    (re.compile(r"^Regex non valida: (.+)$"), r"Invalid regex: \1"),
    (re.compile(r"^La regex deve includere il gruppo \(\?P<name>\.\.\.\)\.$"),
     r"The regex must include the (?P<name>...) group."),
    (re.compile(r"^Placeholder non riconosciuto: (.+)$"),
     r"Unrecognized placeholder: \1"),
    (re.compile(r"^Il template deve contenere esattamente un \{name\}\.$"),
     r"The template must contain exactly one {name}."),
    (re.compile(r"^Il template può contenere al massimo un \{side\}\.$"),
     r"The template can contain at most one {side}."),
    (re.compile(
        r"^Collection (sorgente|destinazione) '(.+)' inesistente su "
        r"'(.+)'\. Disponibili: (.+)$"),
     _translate_missing_collection),
    (re.compile(
        r"^Nessuna coppia valida \((.+)\): non verrebbe creato nulla\. "
        r"Controlla i token e il pattern\.$"),
     _translate_no_valid_pair),
    (re.compile(
        r"^(\d+) ossa ambigue \((.+)\)\. Con 'Risolvi ambiguità' l'addon "
        r"sceglie automaticamente\.$"),
     r"\1 ambiguous bones (\2). With 'Resolve ambiguity' the add-on picks "
     r"one automatically."),
    (re.compile(r"^(\d+) ossa sorgente non trovate in Pose: (.+)$"),
     r"\1 source bones not found in Pose: \2"),
    (re.compile(
        r"^(\d+) coppie con orientamento di rest molto diverso \(>15°\): "
        r"(.+)\. Con spazi LOCAL la posa potrebbe risultare ruotata: "
        r"valuta WORLD o riallinea i roll\.$"),
     r"\1 pairs with very different rest orientation (>15°): \2. With "
     r"LOCAL spaces the pose may look rotated: use WORLD or realign the "
     r"rolls."),
    (re.compile(
        r"^(\d+) ossa destinazione hanno già driver sulle trasformazioni: "
        r"(.+)\. Il constraint si sommerà al driver\.$"),
     r"\1 target bones already have drivers on transforms: \2. The "
     r"constraint will add to the driver."),
    (re.compile(
        r"^(\d+) ossa sorgente sono animate da driver \(l'addon copierà il "
        r"risultato finale, non il driver\)\.$"),
     r"\1 source bones are driven (the add-on copies the final result, not "
     r"the driver)."),
    (re.compile(r"^Spazio consigliato: (.+) \((.+)\)\. Attuale: (.+)\.$"),
     _translate_suggested_space),
)

# Etichette di livello dei report di diagnostica. I tag restano identici nelle
# due lingue: qui serve riconoscerli per tradurre il testo che li segue e per
# normalizzare eventuali tag legacy scritti in italiano.
_LEVEL_TAGS = {
    "INFO": "[INFO]",
    "ERROR": "[ERROR]",
    "WARNING": "[WARNING]",
    "AVVISO": "[WARNING]",
    "ERRORE": "[ERROR]",
    "SUGGERIMENTO": "[INFO]",
}
_LEVEL_TAG_RX = re.compile(r"^\[([A-Za-z]+)\]\s*(.*)$")


def _translate_message(text):
    """Traduce una singola riga di report/diagnostica, se riconosciuta."""
    for patterns in (_REPORT_PATTERNS, _DIAGNOSTIC_PATTERNS):
        for pattern, replacement in patterns:
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                return new_text
    return text


def _translate_report_text(text):
    """Traduce per la UI le righe di report note, senza toccare i dati.

    Riconosce anche le righe di diagnostica con prefisso di livello
    ([INFO]/[ERROR]/[WARNING]): il tag resta in testa e viene tradotto solo il
    messaggio che lo segue.
    """
    if not text or not _is_english_ui():
        return text
    translated = []
    for line in text.split("\n"):
        match = _LEVEL_TAG_RX.match(line)
        if match:
            raw_tag = match.group(1)
            tag = _LEVEL_TAGS.get(raw_tag.upper(), f"[{raw_tag}]")
            message = _translate_message(match.group(2))
            translated.append((tag + " " + message).rstrip())
            continue
        translated.append(_translate_message(line))
    return "\n".join(translated)


# Traduzioni italiane -> inglesi. Le chiavi vengono replicate per i contesti
# usati da Blender (label, proprietà, operatori), così la UI segue la lingua
# dell'interfaccia senza duplicare il codice.
_EN_TRANSLATIONS = {
    "Token di mappatura": "Mapping tokens",
    "1. Token di mappatura": "1. Mapping tokens",
    "Avvio rapido": "Quick start",
    "1. Scegli i token  2. Anteprima  3. Applica": (
        "1. Choose tokens  2. Preview  3. Apply"
    ),
    # L'avvio rapido ora usa due etichette separate: servono chiavi dedicate,
    # altrimenti in UI inglese restano in italiano.
    "1. Scegli i token": "1. Choose tokens",
    "2. Anteprima  3. Applica": "2. Preview  3. Apply",
    "Default: DEF_ → MCH_": "Default: DEF_ → MCH_",
    "Sviluppato con assistenza AI": "Developed with AI assistance",
    "2. Opzioni constraint": "2. Constraint options",
    "3. Azioni": "3. Actions",
    "Sorgente (Target)": "Source (Target)",
    "Destinazione (Owner)": "Destination (Owner)",
    "Preset destinazione:": "Destination presets:",
    "Preset destinazione": "Destination preset",
    # Nota mostrata quando un preset coinciderebbe col token sorgente attivo.
    "Preset '%s' coincide con il token sorgente: non applicato": (
        "Preset '%s' matches the source token: not applied"
    ),
    "Indovina prefissi": "Guess prefixes",
    "Impara da constraint": "Learn from constraint",
    "Usa regex": "Use regex",
    "Pattern personalizzato": "Custom pattern",
    "Opzioni constraint": "Constraint options",
    "Applica a": "Apply to",
    "Influenza": "Influence",
    # Etichette corte delle righe spazio/owner: identiche nelle due lingue,
    # così la traduzione automatica di Blender non le allunga e non le tronca.
    "Src": "Src",
    "Dest": "Dest",
    "Spazio target": "Target space",
    "Spazio owner": "Owner space",
    "Esistenti": "Existing",
    "Constraint esistenti": "Existing constraints",
    "Se esiste già": "If already present",
    "Sostituisci rimuove anche i constraint manuali dello stesso tipo": (
        "Replace also removes manual constraints of the same type"
    ),
    "Tipo e nome constraint": "Type and constraint name",
    "Aggiorna": "Update",
    "Modalità": "Mode",
    "Modalità mix": "Mix mode",
    "Evita duplicati": "Avoid duplicates",
    "Risolvi ambiguità": "Resolve ambiguity",
    "Filtra per bone collection": "Filter by bone collection",
    "Collection sorgente": "Source collection",
    "Collection destinazione": "Destination collection",
    "Sorgente": "Source",
    "Destinazione": "Destination",
    "Solo ossa deform": "Deform bones only",
    "Tipo": "Type",
    "Tipo di constraint": "Constraint type",
    "Tipo token sorgente": "Source token type",
    "Tipo token destinazione": "Destination token type",
    "Token sorgente (Target)": "Source token (Target)",
    "Token destinazione (Owner)": "Destination token (Owner)",
    "Copy Rotation e' il caso tipico DEF → MCH": (
        "Copy Rotation is the typical DEF → MCH case"
    ),
    "Avanzate": "Advanced",
    "Constraint generati": "Generated constraints",
    "Mix e posizione nello stack": "Mix and stack position",
    "Filtro bone collection": "Bone collection filter",
    "Pattern di mappatura": "Mapping pattern",
    "Filtro, mix e pattern: pannello Avanzate": (
        "Filter, mix and pattern: Advanced panel"
    ),
    "Token attuali: ": "Current tokens: ",
    "Legge il constraint di copia attivo sull'osso selezionato": (
        "Reads the active copy constraint on the selected bone"
    ),
    # La nota cita la Pose Mode: è la condizione reale richiesta dal poll.
    "Serve un osso in Pose Mode con un constraint di copia": (
        "Needs a bone in Pose Mode with a copy constraint"
    ),
    "Usa offset": "Use offset",
    "Posizione": "Position",
    "Posizione nello stack": "Stack position",
    "Rimuovi shear": "Remove shear",
    "Nome": "Name",
    "Nome constraint": "Constraint name",
    "Azioni": "Actions",
    "Informazioni / README": "Info / README",
    "Informazioni": "Information",
    "Anteprima mappatura": "Mapping preview",
    "Applica constraint": "Apply constraints",
    "Rimuovi constraint creati": "Remove generated constraints",
    "Pulisci registro": "Clean registry",
    "Converti in manuali": "Convert to manual",
    "Muta generati": "Mute generated",
    "Smuta generati": "Unmute generated",
    "Mute/Unmute generati": "Mute/Unmute generated",
    "Generati mutati": "Generated muted",
    "Manutenzione": "Maintenance",
    "Verifica rig": "Rig check",
    "Mappatura e report": "Mapping and report",
    "Anteprima non aggiornata": "Preview out of date",
    "Diagnostica non aggiornata": "Diagnostics out of date",
    "Nessun problema rilevato": "No issues found",
    "Nessun constraint IK: posizione ignorata": (
        "No IK constraint: position ignored"
    ),
    "Nessuna bone collection nell'armatura": (
        "No bone collections in the armature"
    ),
    "Bone collections non disponibili": "Bone collections not available",
    "Il mix cambia il risultato: verifica in viewport": (
        "Mix changes the result: check the viewport"
    ),
    "'Usa offset' non disponibile per questo tipo": (
        "'Use offset' is not available for this type"
    ),
    "'Rimuovi shear' non esiste per questo tipo": (
        "'Remove shear' does not exist for this type"
    ),
    "Creatore: ": "Creator: ",
    "Discord: ": "Discord: ",
    # Etichetta umana del link Discord nel popup informazioni: al posto
    # dell'ID numerico mostriamo il nome del profilo.
    "Profilo Discord": "Discord profile",
    "Licenza: ": "License: ",
    "Licenza GPL completa": "Full GPL license",
    "Apri ": "Open ",
    "Azzera": "Clear",
    "Imposta armatura sorgente": "Set source armature",
    "Armatura sorgente": "Source armature",
    "Stessa armatura (default)": "Same armature (default)",
    "Aggiorna nome constraint dai token": (
        "Refresh constraint name from tokens"
    ),
    "Livello": "Level",
    "Messaggio": "Message",
    "Stato": "Status",
    "Nota": "Note",
    "Report:": "Report:",
    "Collection: ": "Collection: ",
    "Mostra diagnostica": "Show diagnostics",
    "Rimuovi solo i constraint generati dall'addon del tipo selezionato": (
        "Removes only generated constraints of the selected type"
    ),
    "Prefisso": "Prefix",
    "Suffisso": "Suffix",
    "Tutte le ossa": "All bones",
    "Solo selezionate": "Selected only",
    "Mantieni": "Keep",
    "Solo se mancante": "Missing only",
    "Aggiorna esistente": "Update existing",
    "In fondo": "Bottom",
    "In cima": "Top",
    "Prima del primo IK": "Before first IK",
    "Risolto": "Resolved",
    "Ambiguo": "Ambiguous",
    # Stato delle righe della lista di mappatura: la sorgente resta in italiano
    # (come i report, che usano già "senza match") e in UI inglese diventa
    # "No match", così la colonna di stato parla una sola lingua.
    "Senza match": "No match",
}

TRANSLATIONS = {
    "en_US": {
        (context, source): target
        for source, target in _EN_TRANSLATIONS.items()
        for context in ("*", "Property", "Operator", "UI")
    },
}

_translations_registered = False


def _register_translations():
    """Registra le traduzioni una sola volta, anche con register() ripetuti."""
    global _translations_registered
    if _translations_registered:
        return
    try:
        bpy.app.translations.register(__name__, TRANSLATIONS)
        _translations_registered = True
    except Exception:
        pass


def _unregister_translations():
    global _translations_registered
    if not _translations_registered:
        return
    try:
        bpy.app.translations.unregister(__name__)
    except Exception:
        pass
    _translations_registered = False
