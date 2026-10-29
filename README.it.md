# Auto Copy Transforms DEF

[![XERJ Corpus Hub contributor](https://hub.xerj.org/contributors/PieroFra/badge.svg)](https://hub.xerj.org/contributors/PieroFra)
[![CI](https://github.com/PieroFra/auto-copy-transforms-def/actions/workflows/tests.yml/badge.svg)](https://github.com/PieroFra/auto-copy-transforms-def/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/PieroFra/auto-copy-transforms-def)](https://github.com/PieroFra/auto-copy-transforms-def/releases/latest)
[![Licenza](https://img.shields.io/badge/Licenza-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Blender](https://img.shields.io/badge/Blender-4.2%2B-blue)](https://www.blender.org/)
[![Versione](https://img.shields.io/badge/versione-1.3.0-green.svg)](https://github.com/PieroFra/auto-copy-transforms-def/releases/tag/v1.3.0)
[![Blender Extensions](https://img.shields.io/badge/Blender_Extensions-auto--copy--transforms--def-orange?logo=blender)](https://extensions.blender.org/add-ons/auto-copy-transforms-def/)

**Constraint Copy Transforms automatici per rig Blender.**  
Automatizza la creazione di constraint Copy Transforms tra armature in pochi
click e ti fa risparmiare ore di lavoro di rigging ripetitivo.

Mappa le ossa sorgente (`MCH_`) sulle ossa di destinazione (`DEF_`, `ORG_`, ...)
e costruisce lo stack di constraint in pochi click.

[Download v1.3.0](https://github.com/PieroFra/auto-copy-transforms-def/releases/tag/v1.3.0) · [Issues](https://github.com/PieroFra/auto-copy-transforms-def/issues)

![Popup Informazioni](docs/info-popup.png)

---

## Perché questo add-on

Nel rigging capita spesso di ripetere la stessa operazione decine di volte:
creare un Copy Transforms su ogni osso di destinazione, puntarlo all'osso
sorgente corrispondente, poi sistemare spazi, influenza e ordine nello stack.

**Auto Copy Transforms DEF** automatizza la parte ripetitiva, lasciando il
risultato ispezionabile e reversibile.

- mappatura dei nomi deterministica
- anteprima prima di applicare
- constraint generati tracciati in un registro JSON
- pulizia che non tocca mai i constraint manuali

---

## Quale file scaricare?

Tutto è pubblicato nella [pagina delle release](https://github.com/PieroFra/auto-copy-transforms-def/releases/latest):

| File | Cos'è | Quando usarlo |
|---|---|---|
| `auto_copy_transforms_def-1.3.0.zip` | Pacchetto Blender Extension | **Consigliato**: installalo come estensione (**Edit → Preferences → Get Extensions → Install from Disk...**) |
| `Auto_Copy_Transforms_DEF_1.3.0.rar` | Pacchetto completo | Vuoi tutto in un solo archivio: lo ZIP dell'estensione, il pacchetto dell'add-on classico (`legacy/auto_copy_transforms_def/`), la documentazione (`README.txt`, `README.it.txt`, `LEGGIMI.txt`) e la licenza (`LICENSE.txt`) |
| `SHA256.txt` | Controllo integrità | Verifica il download prima di installare: confronta la SHA256 di ZIP/RAR con gli hash elencati nel file |
| `legacy/auto_copy_transforms_def/` (dentro il RAR) | Pacchetto add-on classico | Solo uso manuale, solo per chi non usa lo ZIP: copia la cartella nella directory `scripts/addons` di Blender e riavvia Blender |

- **Versione Blender consigliata: 5.2 LTS** — l'unica testata ufficialmente (vedi la matrice di compatibilità sotto).
- **Aggiornamento da una versione precedente:** disinstalla la versione precedente prima di installare la nuova. Il registro dei constraint è salvato su ogni armatura, quindi i dati si mantengono dopo l'aggiornamento.
- **Posizione del registro:** il registro JSON dei constraint generati è salvato come custom property (ID-property `actd_generated`) sull'oggetto armatura, dentro il file `.blend` — non è un file esterno. Viaggia con il `.blend` e non richiede gestione separata (vedi la documentazione dell'add-on nel popup **Info**).

---

## Funzioni

| Area | Cosa offre |
|---|---|
| Mappatura | Token prefisso/suffisso, template personalizzati, regex, riconoscimento lati (`L`/`R`) |
| Armatura sorgente | Stessa armatura oppure armatura sorgente separata |
| Tipi di constraint | `COPY_TRANSFORMS`, `COPY_ROTATION`, `COPY_LOCATION`, `COPY_SCALE` |
| Controllo fine | Mix, spazi target/owner, influenza, offset, posizione nello stack, rimozione shear |
| Filtri | Bone collection e solo ossa deform |
| Diagnostica | Controlli pre-flight per target mancanti, orientamento di rest, driver, collection |
| Auto-prefisso | Stima prefissi come `DEF_` / `MCH_` / `ORG_` dai nomi osso, senza cambiare i default |
| Impara pattern | Legge un constraint di copia esistente e riusa la regola sul resto del rig |
| Manutenzione | Converti in manuali, pulisci registro, mute/unmute dei generati |
| Export | Export di mappatura/registro in CSV o JSON |

L'add-on installabile è un pacchetto Python generato da sorgenti modulari e non ha dipendenze esterne.

---

## Installazione

### Blender 4.2+ / 5.x — Estensione (consigliata)

1. Scarica `auto_copy_transforms_def-1.3.0.zip`.
2. Apri **Edit → Preferences → Get Extensions**.
3. Clicca la freccia in alto a destra e scegli **Install from Disk...**
4. Seleziona lo ZIP e attiva **Auto Copy Transforms DEF**.

### Blender 4.2+ / 5.x — Add-on classico

1. Estrai dal RAR abbinato la cartella `legacy/auto_copy_transforms_def/`.
2. Copiala nella directory `scripts/addons` di Blender.
3. Riavvia Blender e attiva **Rigging: Auto Copy Transforms DEF** in
   **Edit → Preferences → Add-ons**.

Il pacchetto dell'add-on classico è nel RAR abbinato, nella cartella
`legacy/`; non è incluso nello ZIP dell'estensione.

### Dove si trova

Apri la 3D View, premi `N` e seleziona la scheda **Auto Copy Transforms**.

### Aggiornamento da una versione precedente

1. Scarica il nuovo ZIP dall'ultima release.
2. Installalo come estensione (**Edit → Preferences → Get Extensions → Install from Disk...**): Blender sostituisce la versione precedente e conserva le impostazioni.
3. Chi usa l'add-on classico: sostituisce la vecchia cartella `legacy/auto_copy_transforms_def` con quella estratta dal nuovo RAR e riavvia Blender se richiesto.
4. Nulla da rifare sui rig esistenti: il registro resta sull'oggetto armatura (ID-property `actd_generated`) dentro ogni `.blend`, quindi i constraint generati restano tracciati dopo l'aggiornamento.

### Disinstallazione

1. Prima disattiva l'add-on (estensione: menu della voce in **Get Extensions** → disattiva; add-on classico: voce in **Add-ons** → togli la spunta).
2. Rimuovilo dallo stesso pannello (estensione: menu della voce → **Uninstall**; add-on classico: menu della voce → **Remove**).
3. I rig non vengono toccati: i constraint restano sulle ossa e il registro resta come ID-property `actd_generated` sull'oggetto armatura dentro il `.blend` (residuo innocuo; rimuovibile con **Manutenzione → Pulisci registro** in caso di reinstallazione). I backup di Sostituisci (`actd_replace_backup_*.json`) restano nella cartella del `.blend`.

---

## Uso rapido

1. Seleziona l'armatura di destinazione ed entra in **Pose Mode**.
2. Apri la sidebar: `N → Auto Copy Transforms`.
3. Imposta il token sorgente (`MCH_`) e quello di destinazione (`DEF_`).
4. Clicca **Anteprima** per controllare la mappatura.
5. Clicca **Applica constraint**.
6. Usa **Rimuovi constraint creati** per annullare.

> Default: `COPY_TRANSFORMS`, token `MCH_` / `DEF_`.

---

## Come funziona

### 1. Scegli i token

![Pannello principale](docs/demo-panel.png)

Il pannello principale è organizzato in tre passaggi: token, opzioni del
constraint e azioni. Il box di avvio rapido mostra sempre il flusso:
**scegli i token → anteprima → applica**.

![Demo](docs/demo-ui.it.gif)

### 2. Controlla la mappatura

![Anteprima mappatura](docs/demo-preview.png)

L'anteprima elenca ogni coppia `MCH_` → `DEF_` con il suo stato. Nulla viene
applicato finché non clicchi **Applica constraint**.

### 3. Applica e verifica

Il report dell'anteprima conferma il numero di coppie valide e i constraint
generati vengono tracciati nel registro JSON. La suite di regressione verifica
lo stesso comportamento su Blender 5.2 (vedi sotto).

---

## Tipi di constraint

| Tipo | Copia | Note |
|---|---|---|
| `COPY_TRANSFORMS` | Posizione, rotazione, scala | Default; supporta mix e remove shear |
| `COPY_ROTATION` | Solo rotazione | Caso tipico per ossa deform; supporta mix/offset |
| `COPY_LOCATION` | Solo posizione | Supporta `use_offset` |
| `COPY_SCALE` | Solo scala | Supporta `use_offset` |

`use_offset` viene mostrato solo dove è indipendente dal mix
(Copy Location e Copy Scale). Copy Rotation usa il suo mix nativo `OFFSET`;
Copy Transforms ignora l'opzione con un avviso chiaro.

---

## Pannello Manutenzione

Il sotto-pannello **Manutenzione** tiene sotto controllo i constraint generati:

- **Converti in manuali** — esce dal registro senza toccare i constraint.
- **Pulisci registro** — rimuove voci orfane, tipo non coerente e subtarget mancanti.
- **Mute/Unmute generati** — toggle globale, i constraint manuali non vengono toccati.
- **Export CSV / JSON** — una riga per voce del registro, salvata accanto al `.blend`
  (o nella cartella di lavoro corrente se il file non è ancora salvato).

I constraint generati sono tracciati tramite un registro JSON salvato
sull'armatura, perché i constraint Blender non supportano le ID properties.

---

## Compatibilità

| Versione Blender | Stato |
|---|---|
| 4.2 LTS | Dichiarata, non verificata |
| 4.3 | Dichiarata, non verificata |
| 4.4 | Dichiarata, non verificata |
| 5.0 | Dichiarata, non verificata |
| 5.1 | Dichiarata, non verificata |
| 5.2 LTS | **Testata ufficialmente** |

- **Testato ufficialmente: solo Blender 5.2 LTS.**
- **Compatibilità dichiarata: Blender 4.2+** per entrambi i percorsi di
  installazione (add-on classico e manifest dell'estensione). Blender 4.2–5.1
  sono dichiarate compatibili ma non sono state verificate con la suite
  completa.
- **Lingua UI:** italiano e inglese, in base alla lingua dell'interfaccia Blender.
- **Documentazione:** inglese e italiano.

La suite copre operatori, mappatura, tipi di constraint, diagnostica,
auto-prefisso, apprendimento del pattern, manutenzione ed export. La UI viene
verificata a mano perché i test headless non possono cliccare l'interfaccia.

---

## Limitazioni note

- **Blender 4.2–5.1 sono dichiarate compatibili ma non sono state testate
  ufficialmente.** L'ambiente di regressione ufficiale è Blender 5.2 LTS.
- **I test headless non sostituiscono una verifica GUI interattiva completa:**
  le suite di regressione verificano comportamento e logica, ma l'interfaccia
  è stata verificata a mano solo su Blender 5.2.
- **I constraint generati usano un registro JSON interno:** i constraint
  Blender non supportano le ID properties, quindi i constraint generati sono
  tracciati tramite un registro salvato sull'armatura. Rimuoverli o rinominarli
  a mano fuori dal pannello Manutenzione può lasciare voci orfane (rimuovibili
  via **Pulisci registro**).

---

## Sviluppo

L'add-on installabile è un pacchetto Python generato da sorgenti modulari.
La fonte di verità sono i moduli in `actd_build/actd_mods/`; lo step di build
assembla il pacchetto installabile. L'architettura di sviluppo completa (file
modificati, file generati, rigenerazione, test, versionamento) è documentata
in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) (in inglese).

Le suite di regressione stanno in `actd_build/`:

```text
test_mod1.py            armatura sorgente
test_mod2.py            mix mode e posizione nello stack
test_mod3.py            filtro bone collection
test_mod4.py            diagnostica
test_actd.py            suite end-to-end storica
test_mod_types.py       tipi di constraint e use_offset
test_mod_autoprefix.py  riconoscimento automatico dei token
test_mod_learn.py       impara il pattern da un constraint
test_mod6.py            manutenzione ed export
test_i18n.py            traduzioni UI italiano/inglese
test_func1.py           verifica funzionale della copia
test_mod7.py            backup di sostituzione e classificazione del registro
```

Esegui l'audit canonico (tutte le 12 suite, con verifica di ogni
`test_out.txt` e controllo dei conteggi attesi per suite):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File actd_build\run_all_tests.ps1
```

Lo stesso audit è eseguibile su Linux, macOS e Windows con il runner portatile
(solo libreria standard Python, senza PowerShell):

```bash
python actd_build/run_all_tests.py
```

Accetta `-Blender <percorso>` (default: variabile d'ambiente `BLENDER_EXE`,
altrimenti `blender` nel `PATH`) e `-Suites <elenco separato da virgole>`
(default: tutte le suite); scrive lo stesso `test_out.txt`, applica gli stessi
conteggi attesi per suite e restituisce exit code 0/1 come il wrapper Windows.
Il wrapper PowerShell per default usa
`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`;
passa `-Blender <percorso>` per usare un altro eseguibile. Per una sola suite,
avvia Blender direttamente, ad esempio:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --background --factory-startup --python actd_build\test_actd.py
```

Esito dell'audit: **644/644 controlli superati, 0 falliti** su Blender 5.2. Il runner
si aspetta: `test_mod1.py` 40, `test_mod2.py` 18, `test_mod3.py` 24,
`test_mod4.py` 43, `test_func1.py` 5, `test_actd.py` 106,
`test_mod_types.py` 49, `test_mod_autoprefix.py` 35,
`test_mod_learn.py` 40, `test_mod6.py` 169, `test_i18n.py` 65 e
`test_mod7.py` 50 controlli. Le suite riportano `SUPERATO`; la storica
`test_actd.py` stampa `TUTTI I TEST SUPERATI`. Le prime quattro suite
totalizzano 125/125.

![Risultati test](docs/test-results.png)

Tabella completa: [docs/TEST_RESULTS.md](docs/TEST_RESULTS.md). L'immagine
sopra è un riepilogo grafico, non output grezzo dei test.  
Checklist di release: [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).

### Costruire l'estensione

La cartella `packaging` contiene manifest, README del pacchetto e il builder ZIP:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File packaging\build_extension.ps1
```

Crea `dist/auto_copy_transforms_def-1.3.0.zip` ed esegue il validatore delle
estensioni Blender. Usa `-Blender <percorso>` per indicare un altro eseguibile.
Per assemblare localmente ZIP, RAR e file SHA256:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File packaging\build_release.ps1
```

Lo script invoca il builder ZIP e richiede un tool RAR da riga di comando
(`rar.exe` o `WinRAR.exe`; usa `-Rar <percorso>` se si trova altrove). Crea solo
file locali in `dist/`: non pubblica, non crea tag e non usa Git.

---

## Nota sull'uso dell'AI

Questo add-on e la sua documentazione sono stati sviluppati con
**l'assistenza di AI** (agente OpenCode), sotto la direzione e la revisione di
**Pierfrancesco Diodato**. L'autore resta responsabile del codice, dei test e
della licenza.

---

## Licenza

Questo progetto è software libero, distribuito con
**GNU General Public License v3.0 o successiva**.

Vedi [LICENSE](LICENSE) per il testo completo.

Copyright (C) 2026 **Pierfrancesco Diodato**.

---

## Autore

**Pierfrancesco Diodato**

- Discord: [1176582483165327382](https://discord.com/users/1176582483165327382)

Se usi l'add-on in un rig di produzione, feedback e segnalazioni sono
benvenuti.
