# -*- coding: utf-8 -*-
"""
=============================================================================
 Auto Copy Transforms DEF (v1.1.0)
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
    "version": (1, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar (N) > Auto Copy Transforms",
    "description": (
        "Crea automaticamente constraint Copy Transforms mappando "
        "intelligentemente i nomi tra ossa sorgente (target) e destinazione (owner)."
    ),
    "warning": "",
    "doc_url": "",
    "category": "Rigging",
}


# =============================================================================
#  INFORMAZIONI AUTORE / LICENZA
# =============================================================================

CREATOR_NAME = "Pierfrancesco Diodato"
DISCORD_ID = "1176582483165327382"
DISCORD_URL = "https://discord.com/users/1176582483165327382"
LICENSE_NAME = "GPL-3.0-or-later"
LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.html"

README_TEXT = """Crea constraint di copia tra le ossa sorgente (DEF-) e le ossa
di destinazione (MCH-, ORG-, ecc.).

USO: seleziona l'armatura in Pose Mode > sidebar N > Auto Copy Transforms >
imposta i token > Anteprima > Applica constraint.

FUNZIONI: Copy Transforms/Rotation/Location/Scale, mix, spazi, influenza,
offset, filtri per bone collection, diagnostica, auto-prefisso, apprendimento
del pattern, manutenzione, export CSV/JSON.

Testato su Blender 5.2. Fallback 3.6/4.x non verificati."""

LICENSE_NOTICE = """GPL-3.0-or-later - Copyright (C) 2026 Pierfrancesco Diodato.
Software libero, distribuito SENZA GARANZIA. Vedi il testo completo."""

README_TEXT_EN = """Creates copy constraints between source bones (DEF-) and destination bones
(MCH-, ORG-, ...).

USAGE: select the armature in Pose Mode > sidebar N > Auto Copy Transforms >
set the tokens > Preview > Apply constraints.

FEATURES: Copy Transforms/Rotation/Location/Scale, mix, spaces, influence,
offset, bone-collection filters, diagnostics, auto-prefix, pattern learning,
maintenance, CSV/JSON export.

Tested on Blender 5.2. 3.6/4.x fallbacks are unverified."""

LICENSE_NOTICE_EN = """GPL-3.0-or-later - Copyright (C) 2026 Pierfrancesco Diodato.
Free software, distributed WITHOUT WARRANTY. See the full text."""


def _is_english_ui():
    """True quando la lingua dell'interfaccia Blender e' inglese."""
    try:
        locale = bpy.app.translations.locale or ""
    except Exception:
        locale = ""
    return locale.lower().startswith("en")


# Traduzioni italiane -> inglesi. Le chiavi vengono replicate per i contesti
# usati da Blender (label, proprietà, operatori), così la UI segue la lingua
# dell'interfaccia senza duplicare il codice.
_EN_TRANSLATIONS = {
    "Token di mappatura": "Mapping tokens",
    "Sorgente (Target)": "Source (Target)",
    "Dest. (Owner)": "Destination (Owner)",
    "Preset destinazione:": "Destination presets:",
    "Preset destinazione": "Destination preset",
    "Indovina prefissi": "Guess prefixes",
    "Impara da constraint": "Learn from constraint",
    "Usa regex": "Use regex",
    "Pattern personalizzato": "Custom pattern",
    "Opzioni constraint": "Constraint options",
    "Applica a": "Apply to",
    "Influenza": "Influence",
    "Spazio target": "Target space",
    "Spazio owner": "Owner space",
    "Esistenti": "Existing",
    "Constraint esistenti": "Existing constraints",
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

STATUS_META = {
    'match': ("OK", 'CHECKMARK'),
    'resolved': ("Risolto", 'INFO'),
    'ambiguous': ("Ambiguo", 'ERROR'),
    'unmatched_src': ("No match", 'CANCEL'),
    'unmatched_dst': ("No match", 'CANCEL'),
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

        # 2) Tentativo A: prima rimuove il side esterno, poi il token (es. "L_DEF_hand" o "DEF-hand.L")
        base_a, side_a, _ = _split_side(name)
        base_a = _strip_token(base_a, self.token, self.token_type)

        # 3) Tentativo B: prima rimuove il token, poi il side (es. "DEF-L_hand" o "hand.L_DEF")
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
    DEF-/MCH- in caso di parita' (l'ordine alfabetico li mette davanti).
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
                reliable[0], "MCH-", False,
                "Un solo prefisso ripetuto: destinazione lasciata a MCH-.",
            )
        return (
            "DEF-", "MCH-", False,
            "Nessun prefisso ripetuto almeno 2 volte.",
        )

    src = _best_prefix(src_rank)
    dst = _best_prefix(dst_rank)
    if not src or not dst:
        return (
            "DEF-", "MCH-", False,
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
            src, "MCH-", False,
            "Prefisso destinazione uguale alla sorgente: usato MCH-.",
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
        findings.append((
            'warning',
            f"{len(ambiguous)} ossa ambigue ({preview}"
            + ("…" if len(ambiguous) > 5 else ")")
            + ". Con 'Risolvi ambiguità' l'addon sceglie automaticamente.",
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
    """Salva i risultati della diagnostica nelle proprietà della Scene."""
    _clear_collection(settings.diagnostic_items)
    for level, text in findings:
        item = settings.diagnostic_items.add()
        item.level = level
        item.text = text
    settings.diagnostic_is_stale = False


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

    # La LCS puo' inglobare il separatore adiacente ("MCH-Hand" vs "DEF-Hand"
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
        description="Token che identifica le ossa sorgente da cui copiare la trasformazione (es. 'DEF-' o 'MCH-')",
        default="DEF-",
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
        description="Token che identifica le ossa destinazione su cui viene aggiunto il constraint (es. 'MCH-')",
        default="MCH-",
        update=_mark_preview_stale,
    )
    dest_token_type: EnumProperty(
        name="Tipo token destinazione",
        description="Se il token destinazione è un prefisso o un suffisso",
        items=TOKEN_TYPE_ITEMS,
        default='PREFIX',
        update=_mark_preview_stale,
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
    last_report: StringProperty(default="")
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


# =============================================================================
#  UI LIST
# =============================================================================

class ACTD_UL_mapping(UIList):
    """Lista delle coppie di mappatura con stato evidenziato."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index=0, flt_flag=0):
        label, icon_name = STATUS_META.get(item.status, ("?", 'QUESTION'))

        split = layout.split(factor=0.38, align=True)
        split.label(text=item.source_name or "-")

        right = split.split(factor=0.62, align=True)
        right.label(text=item.dest_name or "-")

        status_row = right.row(align=True)
        status_row.alignment = 'RIGHT'
        status_row.label(text=label, icon=icon_name)


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
        settings = _settings(context)
        settings.dest_token = self.preset
        settings.dest_token_type = self.token_type
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
        settings.last_report = (
            f"Prefissi: sorgente '{src_token}', destinazione '{dst_token}'.\n"
            f"{detail}"
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
        settings.last_report = "\n".join(righe)
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

        settings.last_report = (
            f"Anteprima completata su '{arm_obj.name}'.\n"
            f"Coppie valide: {valid}\n"
            f"Coppie ambigue: {ambiguous}\n"
            f"Ossa sorgente senza match: {unm_src}\n"
            f"Ossa destinazione senza match: {unm_dst}"
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
        _store_diagnostics(settings, findings)

        errors = sum(1 for level, _ in findings if level == 'error')
        warnings = sum(1 for level, _ in findings if level == 'warning')
        infos = sum(1 for level, _ in findings if level == 'info')

        settings.last_report = "\n".join(
            f"[{level.upper()}] {text}" for level, text in findings
        ) or "Nessun problema rilevato."

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
                settings.last_report = "Applicazione annullata: nessun osso selezionato."
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
        settings.last_report = _build_report(
            created, updated, skipped, replaced,
            ambiguous, unm_src, unm_dst, errors, unique_warnings,
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
                settings.last_report = "Rimozione annullata: nessun osso selezionato."
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

        settings.last_report = f"Constraint rimossi: {removed}"
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
        settings.last_report = f"Voci orfane rimosse dal registro: {removed}"
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
        "versione": "1.1.0",
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

        settings.last_report = (
            f"Constraint convertiti in manuali: {converted}"
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
        settings.last_report = f"Constraint generati {azione}: {changed}"
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

        settings.last_report = (
            f"Report salvato in: {path}\nRighe esportate: {len(rows)}"
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

        settings.last_report = (
            f"Report salvato in: {path}\nRighe esportate: {len(rows)}"
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
        op = row.operator(
            "wm.url_open", text="Discord: " + DISCORD_ID, icon='URL'
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

        # ---------------- Token di mappatura ----------------
        box = layout.box()
        box.label(text="Token di mappatura", icon='SORTALPHA')

        row = box.row(align=True)
        split = row.split(factor=0.38)
        split.label(text="Sorgente (Target)")
        sub = split.row(align=True)
        sub.prop(settings, "source_token", text="")
        sub.prop(settings, "source_token_type", text="")

        row = box.row(align=True)
        split = row.split(factor=0.38)
        split.label(text="Dest. (Owner)")
        sub = split.row(align=True)
        sub.prop(settings, "dest_token", text="")
        sub.prop(settings, "dest_token_type", text="")

        box.label(text="Preset destinazione:")
        row = box.row(align=True)
        op = row.operator("actd.dest_preset", text="MCH_")
        op.preset = "MCH_"
        op.token_type = "PREFIX"
        op = row.operator("actd.dest_preset", text="ORG_")
        op.preset = "ORG_"
        op.token_type = "PREFIX"
        op = row.operator("actd.dest_preset", text="DEF_")
        op.preset = "DEF_"
        op.token_type = "PREFIX"
        op = row.operator("actd.dest_preset", text="_ctrl")
        op.preset = "_ctrl"
        op.token_type = "SUFFIX"

        row = box.row(align=True)
        row.operator(
            "actd.guess_prefixes", text="Indovina prefissi", icon='SORTALPHA'
        )
        row.operator(
            "actd.learn_pattern", text="Impara da constraint", icon='IMPORT'
        )

        col = box.column(align=True)
        col.prop(settings, "custom_pattern", text="Pattern")
        col.prop(settings, "use_regex", text="Usa regex")

        pattern_warning = _validate_pattern(settings)
        if pattern_warning:
            box.label(text=pattern_warning, icon='ERROR')

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
        col.prop(settings, "target_space", text="Spazio target")
        col.prop(settings, "owner_space", text="Spazio owner")
        col.prop(settings, "existing_mode", text="Esistenti")

        # Disabilita update_mode e avoid_duplicates se si è in modalità REPLACE
        keep_col = col.column(align=True)
        keep_col.enabled = (settings.existing_mode == 'KEEP')
        keep_col.prop(settings, "update_mode", text="Modalità")
        keep_col.prop(settings, "avoid_duplicates", text="Evita duplicati")

        col.prop(settings, "resolve_ambiguous", text="Risolvi ambiguità")

        # ---------------- Filtro bone collection (Modulo 3) ----------------
        flt = box.column(align=True)
        flt.prop(settings, "use_collection_filter", text="Filtra per bone collection")
        sub = flt.column(align=True)
        sub.enabled = settings.use_collection_filter
        sub.prop(settings, "collection_source", text="Sorgente")
        sub.prop(settings, "collection_dest", text="Destinazione")
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

        # ---------------- Tipo di constraint (Modulo 5) ----------------
        typ = box.column(align=True)
        typ.row().prop(settings, "constraint_type", text="Tipo")
        if settings.constraint_type != 'COPY_TRANSFORMS':
            typ.label(
                text="Copy Rotation e' il caso tipico DEF → MCH",
                icon='INFO',
            )

        # ---------------- Opzioni avanzate constraint (Modulo 2) ----------------
        adv = box.column(align=True)
        adv.label(text="Avanzate", icon='PREFERENCES')
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

        # Nome constraint con pulsante refresh integrato sulla stessa riga
        name_row = box.row(align=True)
        name_row.prop(settings, "constraint_name", text="Nome")
        name_row.operator("actd.refresh_constraint_name", text="", icon='FILE_REFRESH')

        # ---------------- Azioni ----------------
        box = layout.box()
        box.label(text="Azioni", icon='PLAY')
        col = box.column(align=True)
        col.operator("actd.preview", icon='ZOOM_SELECTED')
        col.operator("actd.apply_transforms", icon='CONSTRAINT')
        col.operator("actd.remove_generated", icon='TRASH')
        row = col.row(align=True)
        row.operator("actd.clean_registry", icon='BRUSH_DATA')

        # ---------------- Informazioni / README ----------------
        row = layout.row()
        row.operator(
            "actd.show_info", text="Informazioni / README", icon='INFO'
        )


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
        row.operator("actd.export_csv", text="Export CSV", icon='FILE_TEXT')
        row.operator(
            "actd.export_json", text="Export JSON", icon='FILEBROWSER'
        )

        if settings.last_report:
            box = layout.box()
            box.label(text="Report:", icon='TEXT')
            for line in settings.last_report.split("\n"):
                box.label(text=line if line else " ")


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
        row.operator("actd.diagnose", icon='VIEWZOOM')

        if settings.diagnostic_is_stale:
            layout.label(text="Diagnostica non aggiornata", icon='INFO')

        if not len(settings.diagnostic_items):
            layout.label(text="Nessun problema rilevato", icon='CHECKMARK')
            return

        icons = {
            'error': ('ERROR', 'ERROR'),
            'warning': ('WARNING', 'ERROR'),
            'info': ('INFO', 'NONE'),
        }
        for item in settings.diagnostic_items:
            icon = icons.get(item.level, ('INFO', 'NONE'))[0]
            box = layout.box()
            box.label(text=item.text, icon=icon)


class ACTD_PT_preview(Panel):
    """Sotto-pannello con lista di anteprima e report finale."""

    bl_label = "Mappatura e report"
    bl_idname = "ACTD_PT_preview"
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
                col.label(text=item.note, icon='INFO')

        if settings.last_report:
            box = layout.box()
            box.label(text="Report:", icon='TEXT')
            for line in settings.last_report.split("\n"):
                box.label(text=line if line else " ")


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