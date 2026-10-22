# Release checklist

Seguire il ciclo iterativo durante lo sviluppo; eseguire la regressione completa
alla fine, prima di aggiornare i risultati documentati o creare i pacchetti.

## 1. Coerenza token

- [ ] I default dell'addon sono `DEF_` / `MCH_`.
- [ ] UI, descrizioni, manifest, README e pacchetto usano coerentemente i token
      effettivi (default `DEF_` / `MCH_`; prefissi configurabili).
- [ ] Le immagini in `docs/` mostrano i token aggiornati.

## 2. Test automatici — sviluppo iterativo

```powershell
python -m py_compile actd_build\auto_copy_transforms_def.py
powershell -NoProfile -ExecutionPolicy Bypass -File actd_build\run_all_tests.ps1 -Suites test_mod1.py,test_mod_types.py
```

Sostituire `-Suites` con le suite mirate alla modifica. Se il Tester stateless
esegue subito le verifiche, il Coder non ripete i test.

## 3. Regressione completa finale

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File actd_build\run_all_tests.ps1
```

- [ ] Verificati `test_out.txt` e tutti gli esiti: 11 suite, **538/538 controlli,
      0 fallimenti**.
- [ ] Solo dopo il pass completo aggiornare la documentazione dei risultati e
      procedere con la creazione dei pacchetti.
- [ ] `test_mod1.py` 40/40 — SUPERATO
- [ ] `test_mod2.py` 18/18 — SUPERATO
- [ ] `test_mod3.py` 24/24 — SUPERATO
- [ ] `test_mod4.py` 43/43 — SUPERATO
- [ ] `test_func1.py` 5/5 — SUPERATO
- [ ] `test_actd.py` 106/106 — TUTTI I TEST SUPERATI
- [ ] `test_mod_types.py` 49/49 — SUPERATO
- [ ] `test_mod_autoprefix.py` 35/35 — SUPERATO
- [ ] `test_mod_learn.py` 40/40 — SUPERATO
- [ ] `test_mod6.py` 113/113 — SUPERATO
- [ ] `test_i18n.py` 65/65 — SUPERATO
- [ ] Totale: **538/538 controlli, 0 falliti**

Esiti verificati: le suite riportano `SUPERATO`, mentre la suite storica
`test_actd.py` riporta `TUTTI I TEST SUPERATI`. Le suite `test_mod1.py`–
`test_mod4.py` totalizzano 125/125. Vedi
`docs/TEST_RESULTS.md` per la tabella completa.

## 4. Pacchetti e verifica Blender

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build_release.ps1
```

- [ ] ZIP dell'estensione creato e validato; RAR creato con ZIP, sorgente legacy,
      README EN/IT, LICENSE e LEGGIMI; `dist/SHA256.txt` contiene gli hash ZIP/RAR.
- [ ] Lo script opera localmente: non esegue upload, crea tag o usa Git.
- [ ] Installazione in un profilo isolato e attivazione riuscite.
- [ ] Popup IT e EN aperti nella GUI reale.
- [ ] Screenshot IT/EN aggiornati.

## 5. Contenuto e trasparenza

- [ ] README EN/IT e README del pacchetto EN/IT aggiornati.
- [ ] Nota **AI assistance** presente in README, manifest e popup.
- [ ] Licenza GPL-3.0-or-later presente.
- [ ] Crediti: Pierfrancesco Diodato + Discord.
- [ ] `LEGGIMI.txt` incluso nel RAR; nessun file locale/personale (`AGENTS.md`,
      `SPEC.md`, copia ACTD legacy in root, backup) incluso nei pacchetti.

## 6. Git e release

- [ ] `git status` pulito.
- [ ] Commit con messaggio chiaro.
- [ ] Push su `origin/main`.
- [ ] Preparare una release con versione/tag nuovi e asset coerenti.

### Incongruenza GitHub verificata — non correggere riscrivendo la release

Il tag `v1.1.0` è antecedente al branch `main` e agli asset pubblicati con
underscore nei nomi. Non alterare né riscrivere la release/tag esistente. Al
prossimo rilascio incrementare la versione e usare un nuovo tag, quindi
pubblicare asset coerenti con quel rilascio.
