# ROADMAP

## Stato (2026-10-23)

- Versione: v1.1.5
- Commit `db3764d` pushato su origin/main
- CI GitHub verde (run 40024229432)
- Gate locale: 594/594

## Priorità per le prossime sessioni

1. Verificare realmente i workflow, non solo crearli: eseguire build-release.yml in workflow_dispatch su un tag di prova e controllare i log.
2. Testare in profondità il backup JSON (schema completo, contenuti per osso, casi limite: .blend non salvato, armature multiple).
3. Aggiungere il ripristino dei backup (operatore che legge actd_replace_backup_*.json e ricrea i constraint rimossi).
4. Validare automaticamente il contenuto dello ZIP (nel workflow: lista file attesi, manifest, versione, nessun file di troppo).
5. Aggiungere badge e stato CI nel README (badge tests/build-release ora che .github è su GitHub).
6. Valutare una matrice reale di versioni Blender (4.2–5.2) in CI o manuale documentata.

## Sospeso

- Ristrutturazione cartelle src/tests/dist: rimandata (path hard-coded in ~10 file; dist/ è gitignored e il monolite deve restare tracciato; nessun beneficio funzionale, header DO NOT EDIT già presente).
