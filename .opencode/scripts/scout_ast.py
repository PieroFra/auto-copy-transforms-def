#!/usr/bin/env python3
"""SCOUT AST — mappa simboli -> righe del monolite A.C.T.D.

Scopo: l'Architetto deve sapere a che righe sta una classe o una funzione
senza MAI caricare il codice dell'addon nella propria memoria (i token del
monolite sono la voce di costo piu' alta della sessione).

Output: solo la mappa, una riga per simbolo:

    SCOUT_FILE <file> righe=<n> simboli=<n>
    SIMBOLO <Classe|Funzione> <nome> <inizio>-<fine>

Uso:
    scout_ast.py [file] [--filter <testo>] [--line <n>] [--max <n>]

--filter  tiene solo i simboli il cui nome contiene il testo (case-insensitive)
--line    indica il simbolo che contiene la riga indicata
"""

import argparse
import ast
import os
import sys

DEFAULT_FILE = os.path.join("actd_build", "auto_copy_transforms_def.py")


def _symbols(tree):
    """Elenca (nome, tipo, riga_inizio, riga_fine, profondita') di ogni simbolo.

    Non scende dentro le funzioni per le classi interne: bastano i nomi dei
    metodi di primo livello per orientarsi.
    """
    out = []

    def visit(node, depth):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                out.append((child.name, "Classe", child.lineno,
                            getattr(child, "end_lineno", child.lineno), depth))
                visit(child, depth + 1)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append((child.name, "Funzione", child.lineno,
                            getattr(child, "end_lineno", child.lineno), depth))
                if depth < 1:
                    visit(child, depth + 1)
            else:
                visit(child, depth)

    visit(tree, 0)
    return out


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("file", nargs="?", default=DEFAULT_FILE)
    parser.add_argument("--filter", dest="flt", default="")
    parser.add_argument("--line", dest="line", type=int, default=0)
    parser.add_argument("--max", dest="max", type=int, default=60)
    args = parser.parse_args()

    path = args.file
    if not os.path.isfile(path):
        print("SCOUT_ERROR file non trovato: {0}".format(path))
        return 2

    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except Exception as exc:
        print("SCOUT_ERROR lettura fallita: {0}: {1}".format(type(exc).__name__, exc))
        return 2

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        print("SCOUT_ERROR SyntaxError riga {0}: {1}".format(exc.lineno, exc.msg))
        return 2

    total_lines = source.count("\n") + 1
    symbols = _symbols(tree)
    print("SCOUT_FILE {0} righe={1} simboli={2}".format(path, total_lines, len(symbols)))

    if args.line > 0:
        best = None
        for name, kind, start, end, depth in symbols:
            if start <= args.line <= end:
                if best is None or depth < best[4]:
                    best = (name, kind, start, end, depth)
        if best is None:
            print("SCOUT_LINE {0} -> nessun simbolo".format(args.line))
        else:
            print("SCOUT_LINE {0} -> {1} {2} ({3}-{4})".format(
                args.line, best[1], best[0], best[2], best[3]))
        return 0

    if args.flt:
        needle = args.flt.lower()
        symbols = [s for s in symbols if needle in s[0].lower()]

    shown = symbols[:max(args.max, 1)]
    for name, kind, start, end, _depth in shown:
        print("SIMBOLO {0:<8} {1:<38} {2}-{3}".format(kind, name, start, end))
    if len(symbols) > len(shown):
        print("... ({0} di {1} mostrati: alza --max)".format(len(shown), len(symbols)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
