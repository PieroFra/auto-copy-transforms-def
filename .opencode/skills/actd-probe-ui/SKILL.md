---
name: ACTD Probe UI
description: Come funziona la verifica deterministica della UI A.C.T.D. (probe in Blender, formato del report, regole di misura del troncamento, troubleshooting di tab/splash/crop). Usare per verificare la presentazione della UI, leggere ui_report.txt o capire perché una cattura è sbagliata.
---

# ACTD — Probe UI

Skill di procedura per il **Visualizzatore**. Il probe misura la UI **dentro Blender**: il modello
non deve fare OCR, perché i pixel sono già stati misurati.

## Il probe in una riga

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\checc\Desktop\BLENDER ADDONS\ACTD\.opencode\scripts\run_ui_probe.ps1"
```

Un solo comando: avvia Blender in GUI con il ponte TCP, carica l'addon, prepara la scena neutra,
apre la sidebar sul tab "Auto Copy Transforms", misura ogni etichetta e salva i file sotto
`TEMP\opencode\actd_gui\`. Durata misurata: **~7,7 s**.

**Non** avviare Blender a mano, **non** usare il ponte TCP direttamente, **non** ripetere il comando.

## I 3 file da leggere (assoluti)

```
C:\Users\checc\AppData\Local\Temp\opencode\actd_gui\ui_report.txt
C:\Users\checc\AppData\Local\Temp\opencode\actd_gui\actd-ui-it.png
C:\Users\checc\AppData\Local\Temp\opencode\actd_gui\actd-ui-en.png
```

Non leggere altri PNG (`actd-panel-*.png` è la finestra intera: non serve).

## Il formato del report, riga per riga

| Riga | Significato |
|---|---|
| `UI_REGION width=561 available=537 scale=1` | larghezza reale della regione sidebar e spazio utile |
| `UI_TEXT OK kind=label w=334 avail=537 "testo"` | etichetta misurata: `OK` / `TIGHT` / `TRUNC?` |
| `UI_SUMMARY labels=67 flagged=0 region_width=561 min_safe_width=468` | totale etichette, quante problematiche, larghezza minima sicura |
| `UI_NOTE ...` | le etichette sono le stesse in IT ed EN (nessun catalogo `.po`): le misure valgono per entrambe |
| `UI_TAB active=Auto Copy Transforms` | verifica che il tab sia attivo **prima** della cattura |
| `SHOT it full=... crop=actd-ui-it.png 553x1396` | screenshot ritagliato |
| `REPORT_FILE <path>` | dove è stato scritto il report |

## La regola decisionale (non si indovina)

- `flagged=0` e nessuna riga `TRUNC?` → **il troncamento è escluso per definizione matematica**:
  la voce `wrapping/troncamento` è `OK`. Non dedurlo dagli pixel della immagine.
- Ogni riga `TIGHT` → **automaticamente `FAIL`**.
- La misura minima (`min_safe_width`) confrontata con `available` dice quanto margine c'è.
- Il PNG serve per l'**estetica** (allineamenti, gerarchia, spaziatura, sovrapposizioni, stati),
  non per ridimostrare i pixel.

## Troubleshooting (cose già rotte una volta)

| Sintomo | Causa | Rimedio |
|---|---|---|
| la cattura mostra il pannello "Trasforma" | il tab è stato attivato **prima** che i pannelli esistessero, e la regione lo ha resettato | attivare il tab **dopo** il primo redraw e riverificarlo (`_activate_tab` in `actd_ui_probe.py`) |
| lo splash copre la sidebar | splash di avvio attivo | `bpy.context.preferences.view.show_splash = False` nello script del bridge |
| il ritaglio è sbagliato | origine calcolata senza `region.x` | sommare `area.x + region.x` |
| `SyntaxError: invalid non-printable character U+FEFF` | BOM scritto da `Set-Content -Encoding UTF8` | usare `[IO.File]::WriteAllText(..., UTF8Encoding($false))` |
| il file Python non viene trovato dal bridge | `sys.path.insert` perso | ripristinare il path del modulo caricato |

## Limiti noti

- Le stringhe vengono dal sorgente in italiano: **per l'EN la misura è un'approssimazione**
  (il pannello non ha un catalogo di traduzione proprio).
- L'altezza della finestra mostra solo la parte superiore del pannello: sotto, la UIList va piegata
  o serve scroll.
- La cattura IT ed EN differiscono solo per la cornice di Blender, non per le etichette.

## Quando il probe non parte

Se il comando non produce i file: **non ripeterlo**. Rispondere `FAIL: probe UI non disponibile`.
