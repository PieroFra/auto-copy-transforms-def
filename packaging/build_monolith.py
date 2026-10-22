#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Split e build del monolite A.C.T.D. (architettura Moduli + Build Step).

Uso:
    python packaging/build_monolith.py          -> split (solo se actd_mods non esiste)
    python packaging/build_monolith.py build    -> assembla i moduli nel monolite

Regole di split:
- nessuna riga del monolite viene modificata;
- ogni riga finisce in un solo modulo, in ordine di file;
- ogni modulo inizia con una riga di intestazione "# MODULO ..." (italiano),
  scartata in fase di build;
- nessun import aggiunto ai moduli.

Ordine di concatenamento (moduli logici consolidati):
header, i18n, tokens, registry, logic, properties, operators, ui, main.
L'ordine e' esplicito in ORDINE_MODULI e non dipende dal nome dei file.
"""

import ast
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONOLITH = os.path.join(ROOT, "actd_build", "auto_copy_transforms_def.py")
MODS_DIR = os.path.join(ROOT, "actd_build", "actd_mods")
HEADER_MARK = "# MODULO "
HEADER_END = " (intestazione di build, non fa parte del monolite)"

# Ordine di concatenamento dei moduli logici consolidati.
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


def leggi_percorso(percorso):
    """Legge un file come testo utf-8 senza alterarne il contenuto."""
    with open(percorso, "r", encoding="utf-8", newline="") as f:
        return f.read()


def scrivi_percorso(percorso, testo):
    """Scrive un file come testo utf-8 senza alterarne il contenuto."""
    with open(percorso, "w", encoding="utf-8", newline="") as f:
        f.write(testo)


def hash_testo(testo):
    """Restituisce l'impronta SHA256 del testo codificato in utf-8."""
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


def nomi_di_assegnazione(nodo):
    """Estrae i nomi semplici da un nodo di assegnazione top-level."""
    nomi = []
    for target in getattr(nodo, "targets", []):
        if isinstance(target, ast.Name):
            nomi.append(target.id)
    return nomi


def nomi_delle_basi(classe):
    """Estrae i nomi delle classi base usate da una definizione di classe."""
    nomi = []
    for base in classe.bases:
        if isinstance(base, ast.Name):
            nomi.append(base.id)
        elif isinstance(base, ast.Attribute):
            nomi.append(base.attr)
    return nomi


def classifica(nodo, indice):
    """Classifica un nodo top-level in un gruppo di modulo.

    Restituisce (chiave_gruppo, nome_modulo, singolo, descrizione).
    """
    if isinstance(nodo, ast.Expr) and indice == 0:
        return ("docstring", "000_docstring", True, "docstring iniziale dell'addon")
    if isinstance(nodo, (ast.Import, ast.ImportFrom)):
        return ("imports", "001_imports", False, "import delle dipendenze Blender")
    if isinstance(nodo, ast.Assign):
        nomi = nomi_di_assegnazione(nodo)
        if "bl_info" in nomi:
            return ("bl_info", "002_bl_info", True, "metadati bl_info dell'addon")
        if "_classes" in nomi:
            return ("registration", "900_classes", True, "elenco delle classi da registrare")
        if all(not nome.lstrip("_").islower() for nome in nomi):
            return ("constants", "010_costanti", False, "costanti e tabelle statiche")
        return ("constants", "010_costanti", False, "costanti e tabelle statiche")
    if isinstance(nodo, ast.FunctionDef):
        nome = nodo.name
        if nome in ("register", "unregister"):
            return ("registration", "9" + ("01_" if nome == "register" else "02_") + nome, True,
                    "funzione " + nome + " dell'addon")
        return ("utilities", "020_utility", False, "funzioni di utilita e logica condivisa")
    if isinstance(nodo, ast.ClassDef):
        nome = nodo.name
        basi = nomi_delle_basi(nodo)
        if any("PropertyGroup" in base for base in basi):
            return ("settings", "100_" + nome.lower(), True, "PropertyGroup " + nome + " delle impostazioni")
        if nome.startswith("ACTD_UL_"):
            return ("uilist", "200_" + nome.lower(), True, "UIList " + nome + " di presentazione")
        if nome.startswith("ACTD_PT_"):
            return ("panels", "300_pannelli", False, "pannelli della UI")
        if nome.startswith("ACTD_OT_"):
            return ("operators", "400_" + nome.lower(), True, "operatore " + nome)
        return ("classes", "150_" + nome.lower(), True, "classe ausiliaria " + nome)
    if isinstance(nodo, ast.If):
        return ("registration", "903_main", True, "blocco di avvio del monolite")
    return ("altro", "800_altro", False, "blocchi residui del monolite")


def costruisci_moduli(testo):
    """Partiziona il testo del monolite in moduli contigui (lista di tuple)."""
    albero = ast.parse(testo)
    righe = testo.splitlines(True)
    moduli = []
    inizio = 1
    gruppo_corrente = None
    for indice, nodo in enumerate(albero.body):
        chiave, nome, singolo, descrizione = classifica(nodo, indice)
        fine = nodo.end_lineno
        if singolo or chiave != gruppo_corrente or not moduli:
            blocco = "".join(righe[inizio - 1:fine])
            moduli.append([chiave, nome, descrizione, blocco])
            gruppo_corrente = chiave
        else:
            moduli[-1][3] += "".join(righe[inizio - 1:fine])
        inizio = fine + 1
        gruppo_corrente = chiave
    if inizio <= len(righe):
        coda = "".join(righe[inizio - 1:])
        if moduli:
            moduli[-1][3] += coda
        else:
            moduli.append(["altro", "800_altro", "blocchi residui del monolite", coda])
    return moduli


def nomi_univoci(moduli):
    """Assegna a ogni modulo un nome file univoco e progressivo."""
    visti = {}
    risultato = []
    for indice, (chiave, nome, descrizione, blocco) in enumerate(moduli):
        corpo = re.sub(r"[^a-z0-9_]", "_", re.sub(r"^\d+_", "", nome.lower()))
        base = "%03d_%s" % (indice * 10, corpo)
        if base in visti:
            visti[base] += 1
            base = "%s_%d" % (base, visti[base])
        else:
            visti[base] = 0
        risultato.append((base, chiave, descrizione, blocco))
    return risultato


def split():
    """Esegue lo split del monolite nei moduli sorgente."""
    if os.path.isdir(MODS_DIR) and os.listdir(MODS_DIR):
        print("ERRORE: %s esiste gia, split non eseguito." % MODS_DIR)
        return 1
    testo = leggi_percorso(MONOLITH)
    impronta_originale = hash_testo(testo)
    moduli = nomi_univoci(costruisci_moduli(testo))
    os.makedirs(MODS_DIR, exist_ok=True)
    for nome, chiave, descrizione, blocco in moduli:
        intestazione = HEADER_MARK + nome + ".py — " + descrizione + HEADER_END + "\n"
        scrivi_percorso(os.path.join(MODS_DIR, nome + ".py"), intestazione + blocco)
    print("Moduli generati in %s:" % MODS_DIR)
    totale = 0
    for nome, chiave, descrizione, blocco in moduli:
        conteggio = blocco.count("\n") + (0 if blocco.endswith("\n") or not blocco else 1)
        totale += conteggio
        print("  %-34s %5d righe  (%s)" % (nome + ".py", conteggio, descrizione))
    print("Totale righe nei moduli: %d" % totale)
    ricostruito = assembla()
    if hash_testo(ricostruito) != impronta_originale:
        print("ERRORE: round-trip non identico all'originale.")
        return 1
    print("Hash originale:   %s" % impronta_originale)
    print("Hash ricostruito: %s" % hash_testo(ricostruito))
    print("Round-trip: OK (byte-identico)")
    return 0


def elenca_moduli():
    """Elenca i file dei moduli nell'ordine esplicito di concatenamento."""
    percorsi = []
    for nome in ORDINE_MODULI:
        percorso = os.path.join(MODS_DIR, nome)
        if os.path.isfile(percorso):
            percorsi.append(percorso)
    return percorsi


def assembla():
    """Assembla i moduli nell'ordine di split, scartando le intestazioni."""
    parti = []
    for percorso in elenca_moduli():
        testo = leggi_percorso(percorso)
        if testo.startswith(HEADER_MARK):
            taglio = testo.find("\n")
            testo = testo[taglio + 1:] if taglio >= 0 else ""
        parti.append(testo)
    return "".join(parti)


def build():
    """Assembla i moduli e riscrive il monolite verificando l'hash."""
    percorsi = elenca_moduli()
    if not percorsi:
        print("ERRORE: nessun modulo in %s." % MODS_DIR)
        return 1
    impronta_originale = hash_testo(leggi_percorso(MONOLITH))
    testo = assembla()
    impronta_nuova = hash_testo(testo)
    scrivi_percorso(MONOLITH, testo)
    print("Moduli assemblati: %d" % len(percorsi))
    for percorso in percorsi:
        contenuto = leggi_percorso(percorso)
        print("  %-34s %5d righe" % (os.path.basename(percorso), contenuto.count("\n")))
    print("Hash monolite precedente: %s" % impronta_originale)
    print("Hash monolite rigenerato: %s" % impronta_nuova)
    if impronta_nuova != impronta_originale:
        print("ERRORE: il monolite rigenerato non e byte-identico al precedente.")
        return 1
    print("Build: OK (byte-identico)")
    return 0


def main(argomenti):
    """Punto di ingresso: split senza argomenti, build con argomento 'build'."""
    if len(argomenti) == 0:
        return split()
    if argomenti[0] == "build":
        return build()
    print("Uso: python packaging/build_monolith.py [build]")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
