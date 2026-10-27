# MODULO actd_header.py — intestazione: docstring, import, bl_info e metadati (intestazione di build, non fa parte del monolite)
# -*- coding: utf-8 -*-
"""
=============================================================================
 Auto Copy Transforms DEF (v1.2.0)
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
    "version": (1, 2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N) > Auto Copy Transforms",
    "description": (
        "Automatically creates Copy Transforms constraints by mapping "
        "bone names between source (target) and destination (owner) bones. "
        "Developed with AI assistance."
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
