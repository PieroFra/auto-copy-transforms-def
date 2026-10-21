# Release checklist

Eseguire questi controlli **prima** di ogni commit, push o release.

## 1. Coerenza token

- [ ] I default dell'addon sono `DEF_` / `MCH_`.
- [ ] UI, descrizioni, manifest, README e pacchetto usano coerentemente i token
      effettivi (default `DEF_` / `MCH_`; prefissi configurabili).
- [ ] Le immagini in `docs/` mostrano i token aggiornati.

## 2. Test automatici

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
Get-ChildItem actd_build\test_*.py | ForEach-Object {
    & $blender --background --factory-startup --python $_.FullName `
        > test_out.txt 2>&1
    "### $($_.Name) exit=$LASTEXITCODE"
    Select-String test_out.txt -Pattern 'Passati:|Falliti:|Superati:|RISULTATO:|TUTTI I TEST'
}
```

- [ ] `test_mod1.py` 40/40
- [ ] `test_mod2.py` 18/18
- [ ] `test_mod3.py` 16/16
- [ ] `test_mod4.py` 18/18
- [ ] `test_func1.py` 5/5
- [ ] `test_actd.py` 106/106
- [ ] `test_mod_types.py` 49/49
- [ ] `test_mod_autoprefix.py` 35/35
- [ ] `test_mod_learn.py` 40/40
- [ ] `test_mod6.py` 48/48
- [ ] `test_i18n.py` 14/14
- [ ] Totale: **389 controlli, 0 falliti**

## 3. Estensione

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build_extension.ps1
```

- [ ] Build completata.
- [ ] Validazione `--command extension validate` superata.
- [ ] Installazione in un profilo isolato e attivazione riuscite.
- [ ] Popup IT e EN aperti nella GUI reale.
- [ ] Screenshot IT/EN aggiornati.

## 4. Contenuto e trasparenza

- [ ] README EN/IT e README del pacchetto EN/IT aggiornati.
- [ ] Nota **AI assistance** presente in README, manifest e popup.
- [ ] Licenza GPL-3.0-or-later presente.
- [ ] Crediti: Pierfrancesco Diodato + Discord.
- [ ] Nessun file locale/personale (`AGENTS.md`, `SPEC.md`, `read.me`,
      copia ACTD legacy in root, backup) incluso nel pacchetto.

## 5. Git e release

- [ ] `git status` pulito.
- [ ] Commit con messaggio chiaro.
- [ ] Push su `origin/main`.
- [ ] Preparare una release con versione/tag nuovi e asset coerenti.

### Incongruenza GitHub verificata — non correggere riscrivendo la release

Il tag `v1.1.0` è antecedente al branch `main` e agli asset pubblicati con
underscore nei nomi. Non alterare né riscrivere la release/tag esistente. Al
prossimo rilascio incrementare la versione e usare un nuovo tag, quindi
pubblicare asset coerenti con quel rilascio.
