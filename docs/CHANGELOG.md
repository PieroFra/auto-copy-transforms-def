# Changelog

Tutte le modifiche rilevanti di A.C.T.D. (Auto Copy Transforms DEF) sono
documentate in questo file. Le date si riferiscono all'anno 2026.

## [1.3.1] - 2026-11-04

### Cambiato

- Allineamento di versione a 1.3.1: `bl_info`, manifest dell'estensione e
  testi del pacchetto.

## [1.3.0] - 2026-10-27

### Cambiato

- Direzione standard del rigging: i constraint Copy Transforms vengono ora
  creati sui bone `DEF_` (owner), con `MCH_` come sorgente, coerentemente
  con la convenzione dei rig di produzione.
- Rimossi i riferimenti testuali alla direzione inversa (constraint su `MCH_`
  con sorgente `DEF_`) da documentazione e testi della UI.

### Verifica

- 12 suite di test headless: 644/644 controlli verdi, 0 fallimenti.

## [1.2.0] - 2026-10-26

### Aggiunto

- Architettura "Moduli + Build Step": la fonte di verità sono i moduli in
  `actd_build\actd_mods\`, da cui `packaging\build_package.py` genera il
  pacchetto installabile `actd_build\auto_copy_transforms_def\`.

### Consolidato

- UI e diagnostica: pannelli, operatori e report di verifica riallineati
  alle nuove sorgenti modulari, senza cambiare il comportamento di default.
