# Kit promozionale multi-canale — Auto Copy Transforms DEF v1.1.5

Materiali pronti all'uso per la promozione dell'add-on **Auto Copy Transforms
DEF** v1.1.5 (GPL-3.0-or-later; Blender 4.2+ dichiarato, testato ufficialmente
su Blender 5.2 LTS). Tutto il contenuto di questo file è **locale**: non
pubblicare nulla online senza approvazione dell'autore. Adattare sempre il tono
al canale prima della pubblicazione (vedi sezione 6).

## Riferimenti (link verificati alla stesura)

- Repository: <https://github.com/PieroFra/auto-copy-transforms-def>
- Release v1.1.5: <https://github.com/PieroFra/auto-copy-transforms-def/releases/tag/v1.1.5>
- Asset estensione: `auto_copy_transforms_def-1.1.5.zip` (nella release v1.1.5)
- GIF demo: `docs/demo-ui.gif` — <https://raw.githubusercontent.com/PieroFra/auto-copy-transforms-def/main/docs/demo-ui.gif>
- Licenza: GPL-3.0-or-later (`LICENSE` nel repo, `LICENSE.txt` dentro gli asset)
- Autore: Pierfrancesco Diodato — Discord: <https://discord.com/users/1176582483165327382>

---

## 1. Blender Extensions — checklist submission

Da verificare **prima** dell'upload su extensions.blender.org:

- [ ] **Manifest valido:** `packaging/blender_manifest.toml` (schema_version
      `1.0.0`, id `auto_copy_transforms_def`, name "Auto Copy Transforms DEF",
      type `add-on`).
- [ ] **Versione 1.1.5 coerente** in ogni punto: manifest
      (`version = "1.1.5"`), `packaging/version.json` (`[1, 1, 5]`), `bl_info`
      del monolite `actd_build/auto_copy_transforms_def.py` (`(1, 1, 5)`), tag
      GitHub `v1.1.5`, nome asset `auto_copy_transforms_def-1.1.5.zip`.
- [ ] **Tag coerenti:** manifest `tags = ["Rigging"]` in linea con la categoria
      Rigging del `bl_info`; tag GitHub `v1.1.5` con asset coerenti (ZIP, RAR,
      `SHA256.txt`).
- [ ] **Licenza GPL-3.0:** manifest `SPDX:GPL-3.0-or-later`, `LICENSE` nel repo
      e `LICENSE.txt` incluso nello ZIP.
- [ ] **Nessuna dipendenza esterna:** add-on single-file Python, sola libreria
      standard, nessun requisito aggiuntivo.
- [ ] **ZIP extension già validato:** `packaging/build_extension.ps1` esegue
      `blender --command extension build` (poi `extension validate`) su
      `dist/auto_copy_transforms_def-1.1.5.zip`; ripetere il validate subito
      prima dell'upload.

Campi da compilare sul sito:

- **Nome:** Auto Copy Transforms DEF (identico al manifest).
- **Tag:** Rigging.
- **Descrizione breve** (max ~200 caratteri): la tagline del manifest
  "Automatic Copy Transforms between DEF and MCH bones"; variante più completa
  (EN, <200 caratteri): "Create Copy Transforms constraints between armatures
  in seconds: map DEF_ source bones to MCH_/ORG_ destinations, preview, apply,
  track and clean up generated constraints."
- **Descrizione lunga:** riutilizzare la `description` del manifest (EN,
  multi-riga: feature, AI disclosure, contatti) arricchendola con link al repo,
  licenza, GIF demo (`docs/demo-ui.gif`) e screenshot
  (`docs/demo-panel.png`, `docs/demo-preview.png`).

Nota: la submission richiede un **account Blender ID** collegato e ogni caricamento
è soggetto a **review manuale** del team Blender — i tempi di approvazione sono
variabili e non controllabili dall'autore. Non caricare una versione diversa
dalla 1.1.5 senza aggiornare insieme manifest, tag e asset.

---

## 2. Blender Artists — bozza thread

**Titolo:** Auto Copy Transforms DEF — open-source Blender add-on for DEF/MCH rigging

**Testo (inglese; tono community/annuncio, orientato a workflow e feedback — non
riutilizzare verbatim su altri canali):**

> Hi all — I maintain an open-source add-on, Auto Copy Transforms DEF, made for
> riggers working with DEF_/MCH_/ORG_ rigs who want the repetitive part of
> constraint setup automated.
>
> If you have ever rebuilt a production rig, you know the pain: every deform
> bone needs a matching Copy Transforms constraint on its MCH_ (or ORG_)
> counterpart, often across two different armatures, with the right spaces, mix
> mode and influence. Done by hand it is slow, repetitive and easy to get wrong.
>
> What it does in a normal rigging session:
>
> - deterministic name mapping (prefix/suffix tokens, custom templates, regex,
>   automatic L/R side detection) between a source armature (DEF_) and a
>   destination one (MCH_, ORG_, ...), or within the same armature;
> - Copy Transforms / Rotation / Location / Scale with mix, spaces, influence,
>   offset and stack position controls;
> - bone collection and deform-only filters;
> - live preview of the whole mapping before anything is applied;
> - pre-flight diagnostics (missing targets, rest orientation, drivers,
>   collections) so you know what will fail before you click;
> - every generated constraint is tracked in a JSON registry stored on the
>   armature, so cleanup never touches manual constraints;
> - maintenance tools: convert to manual, clean registry, mute/unmute
>   generated constraints, export mapping/registry to CSV or JSON;
> - "learn pattern": point it at one existing constraint and it reuses that
>   rule on the rest of the rig.
>
> Demo (full workflow in a few seconds):
> <https://raw.githubusercontent.com/PieroFra/auto-copy-transforms-def/main/docs/demo-ui.gif>
>
> Repository (GPL-3.0-or-later):
> <https://github.com/PieroFra/auto-copy-transforms-def>
>
> I would love feedback from other riggers, especially on real production rigs:
> does the mapping cover your naming conventions? Are the diagnostics useful?
> The full regression suite runs on Blender 5.2 LTS, so if you test it on
> Blender 4.2-5.1 I am very interested in your results — compatibility there is
> declared but not yet verified. Bug reports, feature requests and UI
> impressions are all welcome. Thanks!

---

## 3. Reddit — bozza post tecnico

**Destinazione:** r/blender o r/blenderhelp. **Struttura:** prima persona; il
problema tecnico apre il post, la GIF demo sta al centro, il link al repo chiude.
Testo diverso dalla bozza Blender Artists.

**Testo (inglese):**

> I lost way too many hours last week on something that should take two clicks:
> a rig with a few hundred bones, split between a DEF_ armature and an MCH_
> armature, needs a Copy Transforms constraint on every destination bone
> pointing at its source counterpart. Doing that manually — one constraint at a
> time, then fixing target space, mix mode and influence on each — is where
> rigging hours quietly disappear, and where typos in subtargets breed.
>
> So the tool I use matches bones deterministically by name tokens (DEF_ →
> MCH_, with templates, regex and side detection also available), shows the
> entire mapping as a preview with pre-flight checks (missing targets, rest
> orientation, drivers, collections) before anything touches the rig, and then
> applies it in one shot. Generated constraints live in a JSON registry on the
> armature object, which makes "remove what I generated" safe and never deletes
> manual constraints. Mapping and registry can be exported to CSV or JSON for
> documentation.
>
> [GIF demo — armature source/destination, pannello, preview, apply, cleanup]:
> <https://raw.githubusercontent.com/PieroFra/auto-copy-transforms-def/main/docs/demo-ui.gif>
>
> Repository (open source, GPL-3.0-or-later):
> <https://github.com/PieroFra/auto-copy-transforms-def>
>
> How do you others handle bulk constraint generation between armatures —
> scripts, drivers, other add-ons? Feedback and issues welcome, especially from
> anyone running it on Blender 4.2-5.1 (my full test suite only runs on 5.2 LTS).

---

## 4. Bazaar / directory

Scheda prodotto ordinata, pronta per directory/listing:

- **Nome:** Auto Copy Transforms DEF
- **Descrizione breve:** Automatic Copy Transforms constraints between DEF_
  source bones and MCH_/ORG_ destination bones — mapping, preview, diagnostics,
  registry tracking and cleanup.
- **Licenza:** GPL-3.0-or-later
- **Compatibilità:** Blender 4.2+ (extension e add-on classico); testato
  ufficialmente su Blender 5.2 LTS
- **Link download:** <https://github.com/PieroFra/auto-copy-transforms-def/releases/tag/v1.1.5>
  (asset: `auto_copy_transforms_def-1.1.5.zip`)
- **Link repo:** <https://github.com/PieroFra/auto-copy-transforms-def>

Nota onesta: **verificare al momento della sottomissione** se i siti citati
(BlenderNation Bazaar e directory simili) accettano ancora submission — policy,
moduli e persino l'esistenza di questi listing cambiano nel tempo. Non dare per
scontato nessun canale: controllare la pagina "submit" del singolo sito prima
di preparare l'asset.

---

## 5. Video demo 30-60s — storyboard

Registrare in **1080p da Blender 5.2 LTS** (ambiente ufficialmente testato).
Shot list — 8 shot:

1. **0-5s — Setup.** Scena con armatura sorgente (ossa `DEF_`) e armatura
   destinazione (ossa `MCH_`); selezione della destinazione e ingresso in
   Pose Mode.
2. **5-10s — Pannello.** Sidebar `N` → tab Auto Copy Transforms; token di
   default `DEF_` / `MCH_` visibili.
3. **10-18s — Preview.** Click **Preview**: tabella di mapping `DEF_` → `MCH_`
   con stato di ogni coppia e report delle coppie valide.
4. **18-25s — Diagnostics.** Panoramica sui controlli pre-volo (target
   mancanti, orientamento rest, driver, collection) senza applicare nulla.
5. **25-32s — Apply.** Click **Apply constraints**: i vincoli compaiono nello
   stack delle ossa `MCH_` (Outliner / pannello osso).
6. **32-42s — Risultato.** Prova di animazione: le ossa `MCH_` seguono le `DEF_`
   in tempo reale.
7. **42-52s — Manutenzione/export.** Registry dei constraint generati, export
   CSV/JSON, convert-to-manual.
8. **52-60s — Cleanup + end card.** **Remove generated constraints**: il rig
   torna esattamente come prima; card finale con link al repo, release v1.1.5
   e licenza GPL-3.0.

---

## 6. Note adattamento per canale

| Canale | Angolo |
|---|---|
| Blender Extensions | Installazione/compatibilità (manifest valido, 4.2+, review manuale) |
| Blender Artists | Workflow e feedback (riggers, rig di produzione) |
| Reddit (r/blender, r/blenderhelp) | Problema tecnico e dimostrazione |
| YouTube | Risultato visivo (storyboard 30-60s) |
| Directory / Bazaar | Scheda secca (nome, licenza, compatibilità, link) |
