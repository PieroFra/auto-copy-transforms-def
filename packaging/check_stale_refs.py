"""Controllo dei riferimenti obsoleti nella documentazione e nella CI.

Esce con codice 1 se nei file scansionati (.github/workflows/*.yml,
README*.md, docs/*.md) compaiono riferimenti al vecchio flusso monolitico:
lo script ``build_monolith`` oppure il monolite ``auto_copy_transforms_def.py``.
Sono esclusi dal controllo il diario personale (docs/DIARIO.md) e i changelog
storici, che documentano il passato e non vanno riscritti.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Radice del repository (la cartella sopra packaging/).
ROOT = Path(__file__).resolve().parent.parent

# Pattern obsoleti: lo script del monolite e il monolite stesso.
STALE_PATTERNS = (
    re.compile(r"build_monolith"),
    re.compile(r"auto_copy_transforms_def\.py"),
)

# Esclusioni: changelog storici (CHANGELOG*.md ovunque) e docs/DIARIO.md.
ESCLUSI = re.compile(r"(^|[\\/])CHANGELOG.*\.md$|[\\/]docs[\\/]DIARIO\.md$")


def file_da_controllare() -> list[Path]:
    """Raccoglie i file da scansionare: workflow CI, README e docs."""
    candidati: list[Path] = []
    candidati.extend(sorted((ROOT / ".github" / "workflows").glob("*.yml")))
    candidati.extend(sorted(ROOT.glob("README*.md")))
    candidati.extend(sorted((ROOT / "docs").glob("*.md")))
    return [p for p in candidati if p.is_file() and not ESCLUSI.search(str(p))]


def main() -> int:
    """Esegue il controllo: exit 0 se pulito, exit 1 con l'elenco delle occorrenze."""
    violazioni: list[str] = []
    for path in file_da_controllare():
        # errors='replace': nessun crash su codifiche non UTF-8.
        testo = path.read_text(encoding="utf-8", errors="replace")
        for numero, riga in enumerate(testo.splitlines(), start=1):
            for pattern in STALE_PATTERNS:
                if pattern.search(riga):
                    rel = path.relative_to(ROOT)
                    violazioni.append(f"{rel}:{numero}: {riga.strip()}")
    if violazioni:
        print("RIFERIMENTI OBSOLETI TROVATI (exit 1):")
        for riga in violazioni:
            print(f"  {riga}")
        print(f"Totale: {len(violazioni)} occorrenze.")
        return 1
    print(
        "check_stale_refs: nessun riferimento obsoleto "
        "(build_monolith / auto_copy_transforms_def.py). Exit 0."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
