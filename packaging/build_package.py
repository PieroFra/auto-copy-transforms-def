#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build del pacchetto A.C.T.D. (architettura Moduli + Build Step).

Uso:
    python packaging/build_package.py build    -> rigenera il pacchetto
    python packaging/build_package.py          -> messaggio d'uso

Sostituisce build_monolith.py: l'artefatto non e' piu' un monolite
concatenato ma un pacchetto Python, uguale in comportamento.

Regole di build:
- la fonte di verita' resta actd_build/actd_mods/*.py e non viene toccata;
- la prima riga di intestazione "# MODULO ..." di ogni modulo viene scartata;
- ogni modulo copiato mantiene lo stesso nome file e lo stesso codice;
- __init__.py e' generato (mai editato a mano) e importa i moduli nell'ordine
  esplicito di ORDINE_MODULI, fondendo i nomi in un solo spazio dei nomi;
- prima di scrivere, la build rifiuta i nomi top-level definiti da due moduli
  diversi (nel monolite si sovrascrivevano in silenzio).

Ordine dei moduli (logico, non alfabetico):
header, i18n, tokens, registry, logic, properties, operators, ui, main.
"""

import ast
import hashlib
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODS_DIR = os.path.join(ROOT, "actd_build", "actd_mods")
PKG_DIR = os.path.join(ROOT, "actd_build", "auto_copy_transforms_def")
PKG_NAME = "auto_copy_transforms_def"
INIT_FILE = os.path.join(PKG_DIR, "__init__.py")
HEADER_MARK = "# MODULO "

# Ordine di import dei moduli logici consolidati (senza estensione .py).
ORDINE_MODULI = [
    "actd_header.py",
    "actd_i18n.py",
    "actd_tokens.py",
    "actd_registry.py",
    "actd_logic.py",
    "actd_properties.py",
    "actd_operators.py",
    "actd_ui.py",
    "actd_main.py",
]

# Fonti della versione: packaging/version.json e' l'unica fonte di verita'.
VERSION_JSON = os.path.join(ROOT, "packaging", "version.json")
VERSION_MANIFEST = os.path.join(ROOT, "packaging", "blender_manifest.toml")
MODULO_HEADER = os.path.join(MODS_DIR, "actd_header.py")


def formatta_versione(versione):
    """Formatta una tupla di interi come stringa X.Y.Z."""
    return "%d.%d.%d" % tuple(versione)


def leggi_percorso(percorso):
    """Legge un file come testo utf-8 senza alterarne il contenuto."""
    with open(percorso, "r", encoding="utf-8", newline="") as f:
        return f.read()


def scrivi_percorso(percorso, testo):
    """Scrive un file come testo utf-8 senza alterarne il contenuto."""
    with open(percorso, "w", encoding="utf-8", newline="") as f:
        f.write(testo)


def leggi_versione_json():
    """Legge la versione da packaging/version.json (lista di interi)."""
    try:
        with open(VERSION_JSON, "r", encoding="utf-8") as f:
            dati = json.load(f)
        return tuple(int(parte) for parte in dati["version"])
    except (OSError, ValueError, KeyError, TypeError) as errore:
        sys.exit("Errore versione: impossibile leggere %s (%s)." % (VERSION_JSON, errore))


def leggi_versione_header():
    """Estrae la tupla "version" da bl_info in actd_header.py."""
    testo = leggi_percorso(MODULO_HEADER)
    corrispondenza = re.search(
        r'"version"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', testo
    )
    if corrispondenza is None:
        sys.exit('Errore versione: campo "version" assente in actd_header.py.')
    return tuple(int(gruppo) for gruppo in corrispondenza.groups())


def leggi_versione_manifest():
    """Estrae il campo version da packaging/blender_manifest.toml."""
    testo = leggi_percorso(VERSION_MANIFEST)
    corrispondenza = re.search(
        r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', testo, re.MULTILINE
    )
    if corrispondenza is None:
        sys.exit("Errore versione: campo version assente in blender_manifest.toml.")
    return tuple(int(gruppo) for gruppo in corrispondenza.groups())


def verifica_versione():
    """Confronta header, manifest e version.json prima della build."""
    versione_json = leggi_versione_json()
    versione_header = leggi_versione_header()
    versione_manifest = leggi_versione_manifest()
    if versione_header != versione_json:
        sys.exit(
            "Errore versione: actd_header ha %s, version.json ha %s. "
            "Aggiorna actd_header o version.json."
            % (formatta_versione(versione_header), formatta_versione(versione_json))
        )
    if versione_manifest != versione_json:
        sys.exit(
            "Errore versione: blender_manifest.toml ha %s, version.json ha %s. "
            "Aggiorna il manifest o version.json."
            % (formatta_versione(versione_manifest), formatta_versione(versione_json))
        )
    print("Versione coerente: %s" % formatta_versione(versione_json))
    return versione_json


def hash_testo(testo):
    """Restituisce l'impronta SHA256 del testo codificato in utf-8."""
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


def rimuovi_intestazione(testo):
    """Toglie la riga di intestazione "# MODULO ..." se e' la prima riga."""
    if testo.startswith(HEADER_MARK):
        taglio = testo.find("\n")
        return testo[taglio + 1:] if taglio >= 0 else ""
    return testo


def _nodi_top_level(nodi):
    """Elenca i nodi di primo livello, entrando nei blocchi if/try/with."""
    for nodo in nodi:
        yield nodo
        if isinstance(nodo, (ast.If, ast.Try, ast.With)):
            for campo in ("body", "orelse", "finalbody", "handlers"):
                for sotto in _nodi_top_level(getattr(nodo, campo, []) or []):
                    yield sotto


def nomi_top_level(testo):
    """Estrae i nomi definiti a livello top-level (def, class, assegnazioni).

    I nomi dunder sono esclusi: appartengono al modulo, non allo spazio dei
    nomi condiviso del pacchetto.
    """
    nomi = set()
    for nodo in _nodi_top_level(ast.parse(testo).body):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nomi.add(nodo.name)
        elif isinstance(nodo, ast.Assign):
            for target in nodo.targets:
                if isinstance(target, ast.Name):
                    nomi.add(target.id)
        elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            nomi.add(nodo.target.id)
    return {nome for nome in nomi if not (nome.startswith("__") and nome.endswith("__"))}


def verifica_nomi_univoci(moduli):
    """Rifiuta i nomi top-level definiti da due moduli diversi.

    Restituisce la lista degli errori (vuota se va tutto bene).
    """
    provenienza = {}
    errori = []
    for nome_modulo, testo in moduli:
        for nome in sorted(nomi_top_level(testo)):
            if nome in provenienza:
                errori.append(
                    "%s definito sia in %s sia in %s"
                    % (nome, provenienza[nome], nome_modulo)
                )
            else:
                provenienza[nome] = nome_modulo
    return errori


def preambolo_modulo(precedenti):
    """Blocco generato che rende visibili i nomi dei moduli precedenti.

    Nel monolite i moduli condividevano un unico spazio dei nomi, quindi i
    riferimenti valutati all'import (import, costanti, basi di classe) vedevano
    anche i nomi dei moduli precedenti. Nel pacchetto questa riga ricrea lo
    stesso spazio dei nomi prima che il corpo del modulo venga eseguito.
    """
    if not precedenti:
        return ""
    elenco = ", ".join('"%s"' % nome for nome in precedenti)
    return (
        "# --- inizio blocco generato dalla build (non modificare a mano) ---\n"
        "# Importa i nomi dei moduli precedenti del pacchetto: nel monolite erano\n"
        "# nello stesso spazio dei nomi, qui vanno riportati a mano.\n"
        "import importlib as _actd_imp\n"
        "\n"
        "_actd_prec = (%s,)\n"
        "for _actd_nome in _actd_prec:\n"
        "    for _actd_k, _actd_v in vars(\n"
        '            _actd_imp.import_module("." + _actd_nome, __package__)).items():\n'
        '        if not _actd_k.startswith("__"):\n'
        "            globals().setdefault(_actd_k, _actd_v)\n"
        "del _actd_imp, _actd_prec, _actd_nome, _actd_k, _actd_v\n"
        "# --- fine blocco generato dalla build ---\n"
        "\n" % elenco
    )


def testo_init(versione):
    """Compone il contenuto del __init__.py generato del pacchetto."""
    ordine = "".join('    "%s",\n' % nome[:-3] for nome in ORDINE_MODULI).rstrip(",\n")
    return (
        "# NON MODIFICARE DIRETTAMENTE.\n"
        "# Generato da packaging\\build_package.py - non modificare a mano.\n"
        "# A.C.T.D. (Auto Copy Transforms DEF) versione %s\n"
        "# Edita i moduli in actd_build\\actd_mods\\ e ricostruisci il pacchetto.\n"
        "import importlib\n"
        "\n"
        "_ORDER = (\n"
        "%s,\n"
        ")\n"
        "\n"
        "_mods = []\n"
        "for _name in _ORDER:\n"
        '    _m = importlib.import_module("." + _name, __name__)\n'
        "    globals().update(\n"
        '        {_k: _v for _k, _v in vars(_m).items() if not _k.startswith("__")})\n'
        "    _mods.append(_m)\n"
        "\n"
        "# Seconda passata: ogni modulo vede anche i nomi definiti piu' avanti\n"
        "# nell'ordine, cosi' i riferimenti a runtime si risolvono come nel monolite.\n"
        '_ns = {_k: _v for _k, _v in globals().items() if not _k.startswith("__")}\n'
        "for _m in _mods:\n"
        "    _m.__dict__.update(_ns)\n"
        "del _m, _mods, _name, _ns\n" % (formatta_versione(versione), ordine)
    )


def build():
    """Rigenera il pacchetto: copia i moduli e scrive __init__.py."""
    versione = verifica_versione()

    moduli = []
    for nome_file in ORDINE_MODULI:
        percorso = os.path.join(MODS_DIR, nome_file)
        if not os.path.isfile(percorso):
            print("ERRORE: modulo mancante %s." % percorso)
            return 1
        moduli.append((nome_file, rimuovi_intestazione(leggi_percorso(percorso))))

    errori = verifica_nomi_univoci(moduli)
    if errori:
        print("ERRORE: nomi top-level definiti da piu' moduli:")
        for errore in errori:
            print("  %s" % errore)
        print("Il pacchetto non e' stato generato.")
        return 1

    if os.path.isdir(PKG_DIR):
        shutil.rmtree(PKG_DIR)
    os.makedirs(PKG_DIR)

    generatori = []
    precedenti = []
    for nome_file, testo in moduli:
        contenuto = preambolo_modulo(precedenti) + testo
        percorso = os.path.join(PKG_DIR, nome_file)
        scrivi_percorso(percorso, contenuto)
        generatori.append((nome_file, contenuto))
        precedenti.append(nome_file[:-3])

    init = testo_init(versione)
    scrivi_percorso(INIT_FILE, init)
    generatori.insert(0, ("__init__.py", init))

    print("Pacchetto rigenerato in %s (%d moduli + __init__.py):" % (PKG_DIR, len(moduli)))
    impronte = []
    for nome_file, contenuto in generatori:
        impronta = hash_testo(contenuto)
        impronte.append(impronta)
        print("  %-26s %5d righe  %s" % (nome_file, contenuto.count("\n"), impronta[:16]))
    print("Hash pacchetto: %s" % hash_testo("".join(impronte)))
    print("Build: OK (%s %s)" % (PKG_NAME, formatta_versione(versione)))
    return 0


def main(argomenti):
    """Punto di ingresso: 'build' con argomento, altrimenti messaggio d'uso."""
    if argomenti[:1] == ["build"]:
        return build()
    print("Uso: python packaging/build_package.py build")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
