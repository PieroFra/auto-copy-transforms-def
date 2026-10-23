# NON MODIFICARE DIRETTAMENTE.
# Generato automaticamente da packaging\build_monolith.py: edita i moduli in actd\actd_mods\ e ricostruisci.

# -*- coding: utf-8 -*-
"""
=============================================================================
 Auto Copy Transforms DEF (v1.1.5)
=============================================================================

Addon per Blender 3.6.x, 4.x e 5.x che automatizza la creazione di constraint
"Copy Transforms" sulle ossa di un'armatura, mappando automaticamente le ossa
sorgente (target del constraint) sulle ossa destinazione (owner che ricevono
il constraint) tramite una mappatura intelligente dei nomi.

-----------------------------------------------------------------------------
 ISTRUZIONI DI INSTALLAZIONE
-----------------------------------------------------------------------------
1. Salva questo file come "auto_copy_transforms_def.py".
2. Apri Blender.
3. Vai in Edit > Preferences > Add-ons > Install... (Blender 4.x+: freccia in
   alto a destra > "Install from Disk...").
4. Seleziona il file "auto_copy_transforms_def.py".
5. Attiva la casella accanto a "Rigging: Auto Copy Transforms DEF".
6. Apri la 3D View, premi N per mostrare la sidebar e cerca la scheda
   "Auto Copy Transforms".
=============================================================================

Copyright (C) 2026 Pierfrancesco Diodato
SPDX-License-Identifier: GPL-3.0-or-later
Discord: https://discord.com/users/1176582483165327382
Sviluppato con l'assistenza di AI (OpenCode) sotto la direzione dell'autore.
=============================================================================
"""

import csv
import difflib
import json
import math
import os
import re
import textwrap
from datetime import datetime
from urllib.parse import quote

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup, UIList


# =============================================================================
#  BL_INFO
# =============================================================================
bl_info = {
    "name": "Auto Copy Transforms DEF",
    "author": "Pierfrancesco Diodato",
    "version": (1, 1, 5),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N) > Auto Copy Transforms",
    "description": (
        "Crea automaticamente constraint Copy Transforms mappando "
        "intelligentemente i nomi tra ossa sorgente (target) e destinazione (owner). "
        "Sviluppato con assistenza AI."
    ),
    "warning": "",
    "doc_url": "",
    "category": "Rigging",
}

# Matrice versioni definitiva: l'estensione Blender richiede almeno 4.2
# (allineata al manifest dell'estensione), l'addon legacy resta installabile
# da Blender 4.2 in su ma è testato ufficialmente solo su Blender 5.2 LTS.


# =============================================================================
#  INFORMAZIONI AUTORE / LICENZA
# =============================================================================

CREATOR_NAME = "Pierfrancesco Diodato"
DISCORD_ID = "1176582483165327382"
DISCORD_URL = "https://discord.com/users/1176582483165327382"
LICENSE_NAME = "GPL-3.0-or-later"
LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.html"

README_TEXT = """Crea constraint di copia tra le ossa sorgente (DEF_) e le ossa
di destinazione (MCH_, ORG_, ecc.).

USO: seleziona l'armatura in Pose Mode > sidebar N > Auto Copy Transforms >
imposta i token > Anteprima > Applica constraint.

FUNZIONI: Copy Transforms/Rotation/Location/Scale, mix, spazi, influenza,
offset, filtri per bone collection, diagnostica, auto-prefisso, apprendimento
del pattern, manutenzione, export CSV/JSON.

Testato ufficialmente su Blender 5.2 LTS. Compatibilita' dichiarata: Blender 4.2+. Le versioni precedenti a Blender 5.2 non sono state verificate.
Sviluppato con l'assistenza di AI (OpenCode)."""

LICENSE_NOTICE = """GPL-3.0-or-later - Copyright (C) 2026 Pierfrancesco Diodato.
Software libero, distribuito SENZA GARANZIA. Vedi il testo completo."""

README_TEXT_EN = """Creates copy constraints between source bones (DEF_) and destination bones
(MCH_, ORG_, ...).

USAGE: select the armature in Pose Mode > sidebar N > Auto Copy Transforms >
set the tokens > Preview > Apply constraints.

FEATURES: Copy Transforms/Rotation/Location/Scale, mix, spaces, influence,
offset, bone-collection filters, diagnostics, auto-prefix, pattern learning,
maintenance, CSV/JSON export.

Officially tested on Blender 5.2 LTS. Declared compatibility: Blender 4.2+. Versions older than 5.2 have not been verified.
Developed with AI assistance (OpenCode)."""

LICENSE_NOTICE_EN = """GPL-3.0-or-later - Copyright (C) 2026 Pierfrancesco Diodato.
Free software, distributed WITHOUT WARRANTY. See the full text."""


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
    # Riga del popup di conferma della modalità Sostituisci.
    (re.compile(r"^Saranno rimossi: (\d+) generati dall'add-on / (\d+) manuali$"),
     r"Will remove: \1 generated by the add-on / \2 manual"),
    # Righe del report di backup della modalità Sostituisci.
    (re.compile(r"^Backup creato: (.+)$"), r"Backup created: \1"),
    (re.compile(r"^Backup non riuscito: sostituzione annullata$"),
     r"Backup failed: replacement aborted"),
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
    # Popup di conferma della modalità Sostituisci (REPLACE).
    "Conferma sostituzione constraint": "Confirm constraint replacement",
    "Annulla": "Cancel",
    "Rimuovi solo generati": "Remove generated only",
    "Rimuovi tutto": "Remove all",
    "Conferma rimozione manuali": "Confirm manual removal",
    # Descrizione della checkbox: senza conferma i constraint manuali restano.
    "Abilita 'Rimuovi tutto' nel popup di conferma della modalità "
    "Sostituisci: senza questa conferma i constraint manuali non "
    "vengono rimossi": (
        "Enables 'Remove all' in the Replace confirmation popup: without "
        "this confirmation manual constraints are not removed"
    ),
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

DEFAULT_CONSTRAINT_NAME = "AUTO_COPY_DEF_to_MCH"
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


# --- Marcatura dei constraint generati -------------------------------------
# I Constraint NON supportano le ID properties (con['x'] = y solleva
# "id properties not supported for this type"), quindi il marcatore non puo'
# stare sul constraint. Usiamo un registro JSON salvato sull'armatura
# destinazione: {osso_dest: {nome_constraint: {"obj": ..., "bone": ...}}}.
_GENERATED_PROP = 'actd_generated'


def _read_registry(owner):
    """Legge il registro dei constraint generati dall'addon."""
    if owner is None:
        return {}
    try:
        raw = owner.get(_GENERATED_PROP)
    except Exception:
        return {}
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_registry(owner, data):
    """Scrive il registro, rimuovendo la proprieta' quando e' vuoto."""
    if owner is None:
        return
    try:
        if data:
            owner[_GENERATED_PROP] = json.dumps(data, sort_keys=True)
        elif _GENERATED_PROP in owner:
            del owner[_GENERATED_PROP]
    except Exception:
        pass


def _mark_generated(owner, pose_bone, con, src_obj, src_bone):
    """Registra un constraint come generato dall'addon."""
    reg = _read_registry(owner)
    reg.setdefault(pose_bone.name, {})[con.name] = {
        "obj": src_obj.name if src_obj is not None else "",
        "bone": src_bone,
        "type": con.type,
    }
    _write_registry(owner, reg)


def _forget_generated(owner, pose_bone, con_name):
    """Rimuove una voce dal registro."""
    reg = _read_registry(owner)
    bones = reg.get(pose_bone.name)
    if not bones or con_name not in bones:
        return
    bones.pop(con_name, None)
    if not bones:
        reg.pop(pose_bone.name, None)
    _write_registry(owner, reg)


def _is_generated(owner, pose_bone, con):
    """True se il constraint e' stato creato dall'addon.

    Oltre al nome, accetta anche il caso in cui l'utente abbia rinominato il
    constraint: se target/subtarget coincidono con una voce registrata per
    quell'osso, il constraint viene riconosciuto e la voce aggiornata.
    """
    reg = _read_registry(owner)
    bones = reg.get(pose_bone.name)
    if not bones:
        return False
    if con.name in bones:
        return True
    for old_name, entry in list(bones.items()):
        if not isinstance(entry, dict):
            continue
        target_obj = getattr(con, "target", None)
        target_name = target_obj.name if target_obj is not None else ""
        if entry.get("bone") != getattr(con, "subtarget", ""):
            continue
        if entry.get("obj") and entry.get("obj") != target_name:
            continue
        bones.pop(old_name, None)
        bones[con.name] = entry
        _write_registry(owner, reg)
        return True
    return False


def _constraint_subtarget_valid(con):
    """True se il subtarget del constraint esiste ancora nell'armatura target."""
    subtarget = getattr(con, "subtarget", "")
    if not subtarget:
        return True
    target = getattr(con, "target", None)
    if target is None or getattr(target, "type", None) != 'ARMATURE':
        return False
    # In Edit Mode le ossa non sono ancora nella collezione data.bones:
    # non e' un errore, si rimanda il controllo.
    if getattr(target, "mode", None) == 'EDIT':
        return True
    try:
        return subtarget in target.data.bones
    except (AttributeError, TypeError):
        return False


def _prune_registry(owner, pose_bones=None):
    """Elimina dal registro le voci orfane o non piu' coerenti.

    Una voce viene rimossa se il constraint non esiste, se il tipo e' cambiato
    rispetto a quello registrato o se il subtarget non esiste piu'.
    """
    reg = _read_registry(owner)
    if not reg:
        return 0
    if pose_bones is None:
        pose_bones = owner.pose.bones if owner is not None else ()
    removed = 0
    for bone_name in list(reg.keys()):
        pose_bone = pose_bones.get(bone_name)
        if pose_bone is None:
            removed += len(reg.pop(bone_name, {}) or {})
            continue
        existing = {con.name: con for con in pose_bone.constraints}
        entries = reg.get(bone_name, {})
        if not isinstance(entries, dict):
            reg.pop(bone_name, None)
            continue
        for con_name in list(entries.keys()):
            con = existing.get(con_name)
            entry = entries.get(con_name)
            stale = con is None
            if not stale:
                registered_type = (
                    entry.get("type") if isinstance(entry, dict) else None
                )
                if registered_type and registered_type != con.type:
                    stale = True
                elif not _constraint_subtarget_valid(con):
                    stale = True
            if stale:
                entries.pop(con_name, None)
                removed += 1
        if not entries:
            reg.pop(bone_name, None)
    _write_registry(owner, reg)
    return removed


def _is_pose_bone_selected(pb) -> bool:
    """Compatibilità selezione PoseBone tra Blender 3.6 (pb.bone.select) e 4.0+/5.x (pb.select)."""
    if hasattr(pb, "select"):
        return bool(pb.select)
    return bool(pb.bone and pb.bone.select)


def _find_all_generated(arm_obj, pose_bone, con_type=None):
    """Ritorna i constraint creati da questo addon sull'osso."""
    return [
        con for con in pose_bone.constraints
        if (con_type is None or con.type == con_type)
        and _is_generated(arm_obj, pose_bone, con)
    ]


def _find_generated_constraint(arm_obj, pose_bone, con_type=None):
    """Ritorna il primo constraint creato da questo addon."""
    generated = _find_all_generated(arm_obj, pose_bone, con_type)
    return generated[0] if generated else None


def _find_matching_copy(pose_bone, target_obj, src_name, settings):
    """Cerca un constraint equivalente a quello che si vorrebbe creare.

    Considera anche il tipo: con Copy Rotation selezionato, un Copy Transforms
    presente sull'osso non e' un duplicato, e viceversa.
    """
    for con in pose_bone.constraints:
        if _configured_constraint_matches(con, target_obj, src_name, settings):
            return con
    return None


def _apply_stack_position(pose_bone, con, settings):
    """Sposta il constraint nella posizione richiesta dentro lo stack dell'osso.

    Blender indicizza lo stack dall'alto: 0 = primo eseguito, vince sugli altri.
    """
    position = getattr(settings, "stack_position", 'BOTTOM') or 'BOTTOM'
    constraints = pose_bone.constraints
    if len(constraints) < 2 or position == 'BOTTOM':
        return

    current_index = constraints.find(con.name)
    if current_index == -1:
        return

    if position == 'TOP':
        target_index = 0
    elif position == 'BEFORE_IK':
        # Primo constraint IK eseguito prima del nostro: ci mettiamo davanti
        target_index = None
        for i, other in enumerate(constraints):
            if other is con:
                continue
            if other.type == 'IK' and i < current_index:
                target_index = i
                break
        if target_index is None:
            return
    else:
        return

    if current_index == target_index:
        return
    constraints.move(current_index, target_index)


def _configure_constraint(con, con_name, target_obj, src_name, settings):
    """Imposta nome, target, subtarget, spazi, influenza e opzioni fini.

    Ritorna una lista di avvisi (stringhe) relativi a opzioni che il tipo di
    constraint scelto non supporta, cosi' l'operatore puo' riportarle.
    """
    warnings = []
    con_type = getattr(con, "type", _constraint_type(settings))

    con.name = con_name
    con.target = target_obj
    con.subtarget = src_name

    try:
        con.target_space = settings.target_space
    except (TypeError, ValueError):
        pass
    try:
        con.owner_space = settings.owner_space
    except (TypeError, ValueError):
        pass

    con.influence = settings.influence

    # --- Modulo 2 + 5: mix adattato al tipo di constraint ---
    mix_value, mix_note = _resolved_mix_mode(settings, con_type)
    if mix_note:
        warnings.append(mix_note)
    if mix_value and mix_value != 'REPLACE':
        try:
            con.mix_mode = mix_value
        except (AttributeError, TypeError, ValueError):
            warnings.append(
                f"Impossibile impostare il mix '{mix_value}' su {con_type}."
            )

    # use_offset autonomo solo su Copy Location/Scale (su Copy Rotation è mix)
    wants_offset = bool(getattr(settings, "use_offset", False))
    if _constraint_supports_offset(con_type):
        try:
            con.use_offset = wants_offset
        except (AttributeError, TypeError, ValueError):
            warnings.append("Impossibile impostare 'Usa offset'.")
    elif wants_offset:
        label = CONSTRAINT_TYPE_LABELS.get(con_type, con_type)
        if _constraint_supports(con_type, "use_offset"):
            warnings.append(
                f"Su {label} 'Usa offset' dipende da Mix: usa 'Mix' = Offset."
            )
        else:
            warnings.append(f"'Usa offset' non esiste su {label}: ignorato.")

    # remove_target_shear esiste solo su Copy Transforms
    if getattr(settings, "remove_target_shear", False):
        if _constraint_supports(con_type, "remove_target_shear"):
            try:
                con.remove_target_shear = True
            except (AttributeError, TypeError, ValueError):
                warnings.append("Impossibile impostare 'Rimuovi shear'.")
        else:
            warnings.append(
                f"'Rimuovi shear' non esiste su "
                f"{CONSTRAINT_TYPE_LABELS.get(con_type, con_type)}: ignorato."
            )

    return warnings


def _configured_constraint_matches(con, target_obj, src_name, settings):
    """True se il constraint esistente corrisponde gia' alla configurazione.

    Usato dal controllo duplicati: se il tipo o le opzioni differiscono, il
    constraint non e' equivalente e va aggiornato o ignorato, non riusato.
    """
    if con.type != _constraint_type(settings):
        return False
    if con.target != target_obj or con.subtarget != src_name:
        return False
    if getattr(con, "owner_space", None) != settings.owner_space:
        return False
    if getattr(con, "target_space", None) != settings.target_space:
        return False
    if not _float_close(con.influence, settings.influence):
        return False

    mix_value, _ = _resolved_mix_mode(settings, con.type)
    if mix_value and getattr(con, "mix_mode", 'REPLACE') != mix_value:
        return False

    wants_offset = bool(getattr(settings, "use_offset", False))
    if _constraint_supports_offset(con.type):
        if bool(getattr(con, "use_offset", False)) != wants_offset:
            return False

    wants_shear = bool(getattr(settings, "remove_target_shear", False))
    if _constraint_supports(con.type, "remove_target_shear"):
        if bool(getattr(con, "remove_target_shear", False)) != wants_shear:
            return False

    return True


# =============================================================================
#  PRESET DEL TOKEN DESTINAZIONE
# =============================================================================

# Preset del token destinazione mostrati nella UI: (testo, token, tipo).
# La tabella resta una sola: la usano il menu a tendina e l'operatore storico.
_DEST_PRESETS = (
    ("MCH_", "MCH_", 'PREFIX'),
    ("ORG_", "ORG_", 'PREFIX'),
    ("DEF_", "DEF_", 'PREFIX'),
    ("_ctrl", "_ctrl", 'SUFFIX'),
)

# Voci statiche dell'EnumProperty del menu preset. Sono fisse (non una callback
# dinamica) perche' Blender 5.2 rifiuta la registrazione degli enum con items
# da callback nelle PropertyGroup; l'identificatore e' il token stesso.
DEST_PRESET_ITEMS = [
    (token, label, f"Token destinazione {token}")
    for label, token, _t in _DEST_PRESETS
]


def _dest_preset_is_self_match(settings, preset, token_type):
    """True se il preset coinciderebbe con il token sorgente attivo.

    Un preset uguale alla sorgente (stesso token e stesso tipo) porterebbe a
    mappare ogni osso su se stesso: la UI lo nasconde, senza rimuovere
    l'operatore.
    """
    if settings is None:
        return False
    # `self` puo' non essere ancora un'istanza valida durante la registrazione:
    # qualsiasi accesso fallito vale "non e' un conflitto".
    try:
        source = (getattr(settings, "source_token", "") or "").strip()
        source_type = getattr(settings, "source_token_type", 'PREFIX')
    except Exception:
        return False
    return bool(source) and source == preset and source_type == token_type


def _dest_preset_token_type(preset):
    """Tipo (prefisso/suffisso) associato a un preset, PREFIX se sconosciuto."""
    for _label, token, token_type in _DEST_PRESETS:
        if token == preset:
            return token_type
    return 'PREFIX'


def _apply_dest_preset(settings, preset, token_type):
    """Imposta token e tipo destinazione da un preset (uso unico in UI)."""
    if settings is None or not preset:
        return
    settings.dest_token = preset
    settings.dest_token_type = token_type


def _on_dest_preset_chosen(self, context):
    """Update del menu preset: applica il token scelto alla destinazione.

    Se il preset coincide con il token sorgente attivo (stesso token e stesso
    tipo) la mappatura porterebbe ogni osso su se stesso: in quel caso il
    token destinazione resta invariato e la UI mostra un avviso tradotto.
    """
    settings = None
    scene = getattr(context, "scene", None)
    if scene is not None:
        settings = getattr(scene, "actd_settings", None)
    if settings is None:
        settings = self
    preset = getattr(self, "dest_preset_choice", "")
    token_type = _dest_preset_token_type(preset)
    if _dest_preset_is_self_match(settings, preset, token_type):
        # Il template si traduce prima della sostituzione: la chiave contiene
        # il segnaposto %s, cosi' la UI inglese usa la voce in _EN_TRANSLATIONS.
        template = "Preset '%s' coincide con il token sorgente: non applicato"
        try:
            template = bpy.app.translations.pgettext_iface(template) or template
        except Exception:
            pass
        settings.dest_preset_notice = template % preset
        return
    _apply_dest_preset(settings, preset, token_type)
    settings.dest_preset_notice = ""


# =============================================================================
#  PROPERTY GROUPS
# =============================================================================

def _mark_preview_stale(self, context):
    self.preview_is_stale = True


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
        default="DEF_",
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
        default="MCH_",
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
        default='MCH_',
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


def _classifica_replace(arm_obj, results, selected, con_type):
    """Classifica i constraint toccati dalla modalita' REPLACE.

    Restituisce una lista di terne ``(pose_bone, constraint, generato)``
    applicando gli stessi risultati e lo stesso filtro ``selected`` del ciclo di
    applicazione: conteggi, backup e rimozione vedono cosi' la stessa
    classificazione (fonte di verita' unica).

    Un constraint e' "generato" solo se il suo nome compare nel registro
    dell'armatura: il fallback per rinomina di ``_is_generated`` riconoscerebbe
    come generato anche un manuale con lo stesso subtarget, falsando il
    conteggio (e scrivendo nel registro durante una semplice classificazione).
    """
    voci = []
    registro = _read_registry(arm_obj)
    for res in results:
        if res.status not in ('match', 'resolved'):
            continue

        if selected is not None:
            if res.source not in selected and res.dest not in selected:
                continue

        pose_bone = arm_obj.pose.bones.get(res.dest)
        if pose_bone is None:
            continue

        # Solo le voci del registro contano come generate: il registro si legge
        # una volta e non si modifica durante la classificazione.
        marcati = registro.get(pose_bone.name) or {}
        for con in pose_bone.constraints:
            if con.type != con_type:
                continue
            voci.append((pose_bone, con, con.name in marcati))

    return voci


def _count_replace_targets(arm_obj, results, selected, con_type):
    """Conta i constraint toccati dalla modalita' REPLACE di ``actd.apply_transforms``.

    Restituisce ``(generati, manuali)`` applicando gli stessi risultati e lo
    stesso filtro ``selected`` del ciclo di applicazione, cosi' i conteggi del
    popup corrispondono a quello che verrebbe davvero rimosso. La
    classificazione arriva da ``_classifica_replace``.
    """
    generated = 0
    manual = 0
    for _pose_bone, _con, generato in _classifica_replace(
        arm_obj, results, selected, con_type
    ):
        if generato:
            generated += 1
        else:
            manual += 1

    return generated, manual


def _replace_conferma_ok(settings, scelta, background):
    """True se la scelta REPLACE puo' procedere con la rimozione.

    'ALL' rimuove anche i constraint manuali solo con la checkbox
    ``replace_conferma_manuali`` attiva, tranne nel bypass headless dove non
    esiste popup; 'CANCEL' non rimuove nulla. Funzione pura: dipende solo dai
    parametri, cosi' il rifiuto e' verificabile senza toccare ``bpy``.
    """
    if scelta == 'ALL' and not background:
        return bool(settings.replace_conferma_manuali)
    if scelta == 'CANCEL':
        return False
    return True


def _replace_backup_dir():
    """Cartella del .blend salvato, altrimenti la TEMP di Blender."""
    path = getattr(bpy.context.blend_data, "filepath", "")
    if path:
        return os.path.dirname(path)
    return bpy.app.tempdir


def _collect_replace_targets(arm_obj, results, selected, con_type, scelta):
    """Righe di backup dei constraint che la modalita' REPLACE rimuovera'.

    Usa la stessa classificazione del ciclo di applicazione
    (``_classifica_replace``): con 'GENERATED_ONLY' i constraint manuali restano
    sull'osso e non entrano nel backup. Ogni riga segue lo schema di
    ``actd.export_json`` e in piu' dichiara se il constraint e' generato e
    l'istante della rilevazione.
    """
    rows = []
    stamp = datetime.now().isoformat(timespec="seconds")
    for pose_bone, con, generato in _classifica_replace(
        arm_obj, results, selected, con_type
    ):
        if scelta == 'GENERATED_ONLY' and not generato:
            continue
        target = getattr(con, "target", None)
        rows.append({
            "armatura": arm_obj.name,
            "osso": pose_bone.name,
            "constraint": con.name,
            "tipo": con.type,
            "sorgente": getattr(con, "subtarget", ""),
            "target_object": target.name if target is not None else "",
            "influenza": "%.3f" % con.influence,
            "mix_mode": getattr(con, "mix_mode", ""),
            "spazi": "%s/%s" % (
                getattr(con, "target_space", ""),
                getattr(con, "owner_space", ""),
            ),
            "stato": "muto" if con.mute else "attivo",
            "generato": generato,
            "timestamp": stamp,
        })
    return rows


def _write_replace_backup(arm_obj, rows):
    """Scrive il backup JSON dei constraint in procinto di essere rimossi.

    Usa lo stesso schema di ``actd.export_json``. Restituisce il percorso
    scritto; solleva ``OSError`` se il file non si puo' creare, cosi' il
    chiamante annulla la sostituzione.
    """
    path = os.path.join(
        _replace_backup_dir(),
        "actd_replace_backup_%s_%s.json" % (
            arm_obj.name, datetime.now().strftime("%Y%m%d-%H%M%S")
        ),
    )
    _write_export_json(path, rows)
    return path


class ACTD_OT_apply(Operator):
    """Crea i constraint di copia sulle ossa destinazione."""

    bl_idname = "actd.apply_transforms"
    bl_label = "Applica constraint"
    bl_description = (
        "Crea i constraint di copia sulle ossa destinazione, secondo il tipo "
        "selezionato"
    )
    bl_options = {'REGISTER', 'UNDO'}

    # Scelta della conferma in modalita' REPLACE: 'ASK' apre il popup,
    # 'GENERATED_ONLY' conserva i constraint manuali, 'ALL' li rimuove solo con
    # la checkbox di conferma (fuori dal bypass headless). SKIP_SAVE: e' un
    # parametro di una singola esecuzione, non uno stato da salvare nel file.
    replace_scelta: EnumProperty(
        name="Sostituzione",
        description=(
            "Cosa fare con i constraint già presenti in modalità Sostituisci"
        ),
        items=(
            ('ASK', "Chiedi conferma", "Chiedi conferma prima di rimuovere"),
            ('CANCEL', "Annulla", "Non rimuovere alcun constraint"),
            ('GENERATED_ONLY', "Rimuovi solo generati",
             "Rimuovi solo i constraint creati dall'add-on"),
            ('ALL', "Rimuovi tutto",
             "Rimuovi anche i constraint manuali, se confermato"),
        ),
        default='ASK',
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        return _poll_armature(context)

    def invoke(self, context, event):
        arm_obj = context.object
        settings = _settings(context)

        # Fuori dalla modalita' REPLACE, oppure con una scelta gia' esplicita,
        # non c'e' nulla da confermare.
        if arm_obj is None or arm_obj.type != 'ARMATURE':
            return self.execute(context)
        if settings.existing_mode != 'REPLACE' or self.replace_scelta != 'ASK':
            return self.execute(context)

        # In background/headless non c'e' popup da mostrare: execute applica il
        # bypass deterministico ASK -> ALL.
        if getattr(bpy.app, "background", False):
            return self.execute(context)

        results = compute_mapping(arm_obj, settings)
        selected = None
        if settings.apply_mode == 'SELECTED':
            selected = {
                pb.name for pb in arm_obj.pose.bones if _is_pose_bone_selected(pb)
            }

        generated, manual = _count_replace_targets(
            arm_obj, results, selected, _constraint_type(settings)
        )
        if manual <= 0:
            return self.execute(context)

        # I conteggi restano sull'istanza dell'operatore: draw li mostra,
        # execute li ricalcola prima di rimuovere.
        self._replace_counts = (generated, manual)
        return context.window_manager.invoke_popup(self, width=460)

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

        # Modalita' REPLACE: i constraint manuali si rimuovono solo su scelta
        # esplicita. Senza UI non c'e' popup da confermare, quindi 'ASK' vale
        # 'ALL' e la checkbox non viene richiesta (bypass deterministico).
        replace_choice = self.replace_scelta
        headless = bool(getattr(bpy.app, "background", False))
        if settings.existing_mode == 'REPLACE':
            _, replace_manual = _count_replace_targets(
                arm_obj, results, selected, con_type
            )
            if replace_manual > 0:
                if replace_choice == 'ASK' and headless:
                    replace_choice = 'ALL'
                if replace_choice == 'ASK':
                    self.report(
                        {'WARNING'},
                        "Sostituzione annullata: serve la conferma nel popup "
                        "per rimuovere i constraint manuali.",
                    )
                    return {'CANCELLED'}
                if not _replace_conferma_ok(settings, replace_choice, headless):
                    if replace_choice == 'CANCEL':
                        self.report(
                            {'INFO'},
                            "Sostituzione annullata: nessun constraint rimosso.",
                        )
                    else:
                        self.report(
                            {'WARNING'},
                            "Rimozione dei constraint manuali non confermata: "
                            "nessun constraint rimosso.",
                        )
                    return {'CANCELLED'}

        # Backup obbligatorio: prima di rimuovere qualunque constraint si salva
        # su JSON l'elenco di quelli in procinto di sparire (stesso schema di
        # actd.export_json). Se la scrittura fallisce la sostituzione si annulla.
        backup_path = ""
        if settings.existing_mode == 'REPLACE':
            backup_rows = _collect_replace_targets(
                arm_obj, results, selected, con_type, replace_choice
            )
            try:
                backup_path = _write_replace_backup(arm_obj, backup_rows)
            except OSError:
                # Livello WARNING e non ERROR: un report ERROR su un operatore
                # che ritorna CANCELLED diventa RuntimeError per chi lo chiama
                # da script, mentre qui serve un annullamento pulito.
                self.report(
                    {'WARNING'},
                    "Backup non riuscito: sostituzione annullata",
                )
                _set_preview_report(
                    settings, "Backup non riuscito: sostituzione annullata"
                )
                return {'CANCELLED'}

        # Stessa classificazione anche per la rimozione: in 'GENERATED_ONLY' un
        # constraint fuori dal registro resta sull'osso, come dice il backup.
        generati_replace = set()
        if settings.existing_mode == 'REPLACE':
            for pb, con, generato in _classifica_replace(
                arm_obj, results, selected, con_type
            ):
                if generato:
                    generati_replace.add((pb.name, con.name))

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
                keep_manual = False
                for con in list(pose_bone.constraints):
                    if con.type != con_type:
                        continue
                    if replace_choice == 'GENERATED_ONLY' and (
                        pose_bone.name, con.name
                    ) not in generati_replace:
                        # Scelta esplicita di conservare i manuali: non si crea
                        # un doppione sopra il constraint che resta.
                        keep_manual = True
                        continue
                    _forget_generated(arm_obj, pose_bone, con.name)
                    pose_bone.constraints.remove(con)
                    replaced += 1

                if keep_manual:
                    skipped += 1
                    warnings.append(
                        f"Osso '{res.dest}': constraint manuale conservato, "
                        "creazione saltata."
                    )
                    continue

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
        report_text = _build_report(
            created, updated, skipped, replaced,
            ambiguous, unm_src, unm_dst, errors, unique_warnings,
        )
        if backup_path:
            report_text += f"\nBackup creato: {backup_path}"
        _set_preview_report(settings, report_text)

        self.report(
            {'INFO'},
            f"Creati {created}, aggiornati {updated}, saltati {skipped}, ambigui {ambiguous}.",
        )
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        settings = _settings(context)
        # Il pannello esiste solo dentro il popup: nel pannello "Ultima
        # operazione" non ci sono conteggi da mostrare.
        counts = getattr(self, "_replace_counts", None)
        if counts is None:
            return
        generated, manual = counts

        layout.label(
            text=bpy.app.translations.pgettext("Conferma sostituzione constraint"),
            icon='ERROR',
        )
        layout.label(
            text=_translate_report_text(
                f"Saranno rimossi: {generated} generati dall'add-on / "
                f"{manual} manuali"
            )
        )
        layout.prop(settings, "replace_conferma_manuali")

        # I tre pulsanti rilanciano l'operatore con la scelta gia' decisa: il
        # popup si chiude e execute applica quella scelta.
        row = layout.row(align=True)
        op = row.operator(
            "actd.apply_transforms",
            text=bpy.app.translations.pgettext("Annulla"),
        )
        op.replace_scelta = 'CANCEL'
        op = row.operator(
            "actd.apply_transforms",
            text=bpy.app.translations.pgettext("Rimuovi solo generati"),
        )
        op.replace_scelta = 'GENERATED_ONLY'
        op = row.operator(
            "actd.apply_transforms",
            text=bpy.app.translations.pgettext("Rimuovi tutto"),
        )
        op.replace_scelta = 'ALL'


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
            box.label(text=f"Sorgente: {src_obj.name}", icon='LINKED')

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
            adv.label(text=mix_note, icon='ERROR')
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
            box.label(text=pattern_warning, icon='ERROR')


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


# =============================================================================
#  REGISTRAZIONE
# =============================================================================

_classes = (
    #  I PropertyGroup referenziati da CollectionProperty/PointerProperty
    #  devono stare PRIMA di chi li usa, altrimenti la registrazione fallisce
    #  con "missing bl_rna attribute from '_RNAMetaPropGroup' instance".
    ACTD_DiagnosticItem,
    ACTD_MappingItem,
    ACTD_Settings,
    ACTD_UL_mapping,
    ACTD_OT_dest_preset,
    ACTD_OT_set_source_object,
    ACTD_OT_refresh_constraint_name,
    ACTD_OT_guess_prefixes,
    ACTD_OT_learn_pattern,
    ACTD_OT_preview,
    ACTD_OT_apply,
    ACTD_OT_remove,
    ACTD_OT_clean_registry,
    ACTD_OT_diagnose,
    ACTD_OT_convert_to_manual,
    ACTD_OT_mute_all,
    ACTD_OT_export_csv,
    ACTD_OT_export_json,
    ACTD_OT_show_info,
    ACTD_PT_main,
    ACTD_PT_advanced,
    ACTD_PT_maintenance,
    ACTD_PT_diagnostics,
    ACTD_PT_preview,
)


def _registration_order():
    """Ordina le classi mettendo prima le PropertyGroup referenziate.

    Rete di sicurezza contro il caso in cui una PropertyGroup usata da una
    CollectionProperty non sia elencata in _classes: senza questo controllo la
    registrazione fallisce con un errore poco leggibile.
    """
    order = list(_classes)
    deps = []
    for cls in order:
        annotations = getattr(cls, "__annotations__", {}) or {}
        for prop in annotations.values():
            keywords = getattr(prop, "keywords", None)
            if not isinstance(keywords, dict):
                continue
            dep = keywords.get("type")
            if (
                isinstance(dep, type)
                and issubclass(dep, bpy.types.PropertyGroup)
                and dep not in order
                and dep not in deps
            ):
                deps.append(dep)
    return tuple(deps) + tuple(order)


def _class_is_registered(cls):
    """True se la classe e' gia' registrata in Blender (reload / doppio register)."""
    try:
        return bool(getattr(cls, "is_registered", False))
    except Exception:
        return False


def register():
    registered = []
    try:
        _register_translations()
        for cls in _registration_order():
            if _class_is_registered(cls):
                continue
            try:
                bpy.utils.register_class(cls)
            except ValueError as exc:
                # Classe registrata da una sessione precedente dell'addon:
                # non e' un errore, la consideriamo gia' a posto.
                if "already registered" not in str(exc):
                    raise
                continue
            registered.append(cls)

        if not hasattr(bpy.types.Scene, "actd_settings"):
            bpy.types.Scene.actd_settings = PointerProperty(type=ACTD_Settings)
    except Exception:
        if hasattr(bpy.types.Scene, "actd_settings"):
            try:
                del bpy.types.Scene.actd_settings
            except Exception:
                pass
        for cls in reversed(registered):
            try:
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
        _unregister_translations()
        raise


def unregister():
    _unregister_translations()
    if hasattr(bpy.types.Scene, "actd_settings"):
        try:
            del bpy.types.Scene.actd_settings
        except Exception:
            pass

    for cls in reversed(_registration_order()):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()