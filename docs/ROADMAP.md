# ROADMAP — definitiva di chiusura del progetto

## Obiettivo

Chiudere il progetto con la release finale **v1.2.0**: il ripristino dei backup
è una feature nuova (nessun comportamento esistente viene rimosso), quindi il
bump è **minor** (1.1.5 -> 1.2.0). Dopo v1.2.0 solo **patch release** (1.2.x)
per bug; nessuna nuova feature.

## Milestone

### M1 — Hardening CI
- [ ] Eseguire realmente i workflow, non solo crearli: tests.yml su una PR di prova, build-release.yml in workflow_dispatch su un tag di prova, controllando i log.
- [ ] Validazione automatica del contenuto ZIP dentro build-release.yml: lista file attesi, manifest, versione coerente, nessun file di troppo.

### M2 — REPLACE e backup
- [ ] Test profondi del backup JSON: schema completo, contenuti per osso, caso .blend non salvato, più armature in scena.
- [ ] Operatore di ripristino da file `actd_replace_backup_*.json` (ricrea i constraint rimossi) con test headless scritti dal Coder.

### M3 — Documentazione e visibilità
- [ ] Badge build/test/release/compatibilità e stato CI nel README EN/IT.
- [ ] Matrice Blender 4.2–5.2 con esiti reali: almeno 5.2 LTS verificato, dichiarazione esplicita per le altre versioni.
- [ ] Note di troubleshooting ricavate dai bug raccolti.

### M4 — Release di chiusura v1.2.0
- [ ] Bump in `packaging/version.json` + rebuild monolite/manifest.
- [ ] Gate completo superato.
- [ ] CHANGELOG con sezioni Breaking / Compatibility / Known issues.
- [ ] Tag `v1.2.0`, release via workflow con ZIP+SHA256, verifica degli asset pubblicati.

## Dopo la chiusura: triage bug

Ogni issue: applicare il template -> riproduzione su Blender 5.2 LTS -> test di
regressione -> fix con gate -> patch release 1.2.x con **tag nuovo** (mai
riscrivere un tag esistente). Label consigliate: `bug`, `enhancement`,
`compatibility`, `docs`.

## Bug segnalati al 2026-10-24

Nessuna issue aperta (`gh issue list --state open`: 0 risultati).

## Sospeso

Ristrutturazione cartelle src/tests/dist: rimandata con i vincoli già noti
(path hard-coded in ~10 file; `dist/` è gitignored e il monolite deve restare
tracciato; nessun beneficio funzionale; header DO NOT EDIT già presente).

## Stato (2026-10-24)

- Versione: v1.1.5 (tags fino a v1.1.5)
- Commit attuale: `df9ae8d` (docs: roadmap priorità prossime sessioni)
- CI GitHub verde: run 40025171952 (push su main, success)
- Gate locale: 594/594
