#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AST_INDEX — genera l'indice dei simboli del monolite in Markdown.

E' il "mappa" deterministico del progetto: nessun token speso, nessuna
interpretazione. Il file generato elenca classi e metodi con le righe di
inizio/fine, cosi' l'Architetto e il Coder non devono MAI leggere il sorgente
dell'addon per sapere dove intervenire.

Uso:
    ast_index.py [file] [--out <INDEX.md>]

Riutilizza lo stesso motore di scout_ast.py: una sola logica AST nel progetto.
"""

import argparse
import ast
import os
import sys

# Lo stesso motore del Scout quando e' disponibile: una sola logica AST nel
# progetto. Se manca (progetto senza scout_ast.py), si usa il visitor
# equivalente qui sotto: il file resta autosufficiente.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import scout_ast  # noqa: E402
    _symbols = scout_ast._symbols
except Exception:  # pragma: no cover - fallback per progetti senza Scout
    scout_ast = None

    def _symbols(tree):
        """(nome, tipo, riga_inizio, riga_fine, profondita') di ogni simbolo."""
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

DEFAULT_FILE = os.path.join("actd_build", "auto_copy_transforms_def.py")
DEFAULT_OUT = os.path.join("actd_build", "INDEX.md")


def _outline(source, path):
    """(righe_totali, classi) dove ogni classe porta i suoi metodi.

    Una classe: (nome, inizio, fine, [(metodo, inizio, fine), ...]).
    """
    tree = ast.parse(source, filename=path)
    symbols = _symbols(tree)
    total_lines = source.count("\n") + 1

    classes = []
    current = None
    for name, kind, start, end, depth in symbols:
        if kind == "Classe" and depth == 0:
            current = (name, start, end, [])
            classes.append(current)
        elif current is not None and depth >= 1 and kind == "Funzione":
            current[3].append((name, start, end))
        elif depth == 0:
            # Funzione di primo livello: si tiene da parte come "modulo".
            current = None
    return total_lines, classes, symbols


def _render(source, path):
    total_lines, classes, symbols = _outline(source, path)
    out = []
    out.append("# INDEX AST — {0}".format(os.path.basename(path)))
    out.append("")
    out.append("Generato da `ast_index.py`: file derivato, non modificare a mano.")
    out.append("")
    out.append("- righe totali: {0}".format(total_lines))
    out.append("- simboli: {0}".format(len(symbols)))
    out.append("- classi: {0}".format(len(classes)))
    out.append("")
    out.append("## Classi")
    out.append("")
    out.append("| Classe | Righe | Metodi |")
    out.append("|---|---|---|")
    for name, start, end, methods in classes:
        out.append("| `{0}` | {1}-{2} | {3} |".format(name, start, end, len(methods)))
    out.append("")
    out.append("## Metodi")
    out.append("")
    for name, start, end, methods in classes:
        if not methods:
            continue
        out.append("### `{0}` ({1}-{2})".format(name, start, end))
        out.append("")
        for m_name, m_start, m_end in methods:
            out.append("- `{0}`: {1}-{2}".format(m_name, m_start, m_end))
        out.append("")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("file", nargs="?", default=DEFAULT_FILE)
    parser.add_argument("--out", dest="out", default=DEFAULT_OUT)
    args = parser.parse_args()

    path = args.file
    if not os.path.isfile(path):
        print("INDEX_ERROR file non trovato: {0}".format(path))
        return 2
    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except Exception as exc:
        print("INDEX_ERROR lettura fallita: {0}: {1}".format(type(exc).__name__, exc))
        return 2
    try:
        text = _render(source, path)
    except SyntaxError as exc:
        print("INDEX_ERROR SyntaxError riga {0}: {1}".format(exc.lineno, exc.msg))
        return 2

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    # Scrittura senza BOM: il file viene letto da Python e dall'Architetto.
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    n_classes = text.count("| `")
    print("INDEX_UPDATED {0} classi={1} bytes={2}".format(args.out, n_classes, len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
