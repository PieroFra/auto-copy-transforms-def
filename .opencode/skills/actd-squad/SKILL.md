---
name: ACTD Squadra
description: Come è organizzata la squadra di subagenti OpenCode del progetto A.C.T.D. (ruoli, modelli, costi, comandi) e le regole/trappole di OpenCode emerse usando l'agente (permessi, steps, modello, CLI). Usare per configurare o modificare la squadra, o prima di scrivere un nuovo agente.
---

# ACTD — La squadra

Configurazione **locale** (non pubblicata): `.opencode/agents/`, `.opencode/commands/`,
`opencode.json`, `.opencode/scripts/`. `AGENTS.md`, `opencode.json`, `.opencode/agents/` e
`.opencode/commands/` sono in `.gitignore`: sono file personali.

## Il principio: il verdetto lo dà il codice

L'architetto non giudica, il modello non conta. `verify.ps1` decide (exit code) e
scrive una sola riga di verdetto; gli agenti la **riportano**:

```
VERIFY_OK   | passed=538 | failed=0 | diff=0 | index=UPDATED | task=<tag>   (exit 0)
VERIFY_FAIL | reason=... | ...                                            (exit 1)
VERIFY_FAIL | reason=DIFF_TOO_LARGE | diff=N | max=M | ...                 (exit 2)
```

Ogni decisione che prima richiedeva un LLM è ora codice deterministico:

| Prima (LLM) | Ora (codice) |
|---|---|
| il Tester contava i test e giudicava il log | `run_all_tests.ps1` conta, `verify.ps1` compara con gli attesi |
| il Coder diceva "ho toccato N righe" | `git diff --numstat` + soglia `MaxDiffLines` (exit 2) |
| l'Architetto chiedeva le righe al Scout | `ast_index.py` rigenera `actd_build\INDEX.md` a ogni verifica (0 token) |
| il Visualizzatore guardava i PNG e sperava fossero buoni | `ui_math_check.py` scarta PNG neri/corrotti e righe `TIGHT` **prima** dei token di vision |
| nessuna storia delle verifiche | `.opencode\metrics.jsonl` (una riga JSON per run) |

## I ruoli

| Ruolo | Modello | Costo | steps | Scope |
|---|---|---|---|---|
| **architetto** (primario) | `google/gemini-3.8-flash#low` | 0,75/3,75 $/M fino al 31/12/2026, poi 1,50/7,50 | 25 | orchestra: non modifica file, non esegue test |
| **architetto-riserva** (primario) | `openrouter/z-ai/glm-5.3-flash#low` | 0,15/0,50 $/M | 25 | identico, per when il credito del primario è esaurito |
| **coder** | `openrouter/deepseek/deepseek-v4.1-flash-1017` | 0,15/0,60 $/M | 12 | `actd_build\actd_mods\*.py`, monolite, `build_monolith.*`, **test `test_*.py`** |
| **tester** | `ollama/qwen3.5:9b-actd-fast` | **0 €** | 6 | esegue `gate.ps1`; Scout AST (mappa su file) |
| **visualizzatore** | `openrouter/nvidia/nemotron-3.5-super-vl#none` | 0,15/0,50 $/M | 6 | sola presentazione visiva della UI |
| **ops** | `openrouter/inclusionai/ling-3.1-flash` | ~0,10 $/M | 14 | documentazione, config, packaging, `_esperimenti\`; **mai** il monolite né i test |

Comandi: `/architetto` · `/mappa <filtro>` · `/codifica <cosa>` · `/test [suite]` · `/revisiona` · `/rilascia`.

Stack locale su `E:\AI`: `qwen3.5:9b-actd-fast` (6,6 GB, tag creato con
`PARAMETER temperature 0.0 / num_ctx 16384 / num_predict 4096`) e
`gpt-oss:20b-actd-fast` (13 GB, `num_ctx 32768 / num_predict 4096`).
Il `num_predict` era 2048 e faceva fallire lo Scout con *"Compaction summary
reached the output token limit"*: alzarlo a 4096 ha risolto.

### Spend cap di Google: cosa succede quando si esaurisce

Il 23/10/2026 il benchmark ha esaurito il credito promozionale:
`Error: Spend cap breached for project: projects/590806902997`.

**La squadra continua a funzionare**: il metodo non dipende dal modello
dell'orchestratore. Verificato con GLM 5.3 Flash al posto di Gemini:
`VERIFY_OK | passed=538 | failed=0 | ...` identico.

Per ripristinare Gemini: alzare il budget Google Cloud (o attendere il
ripristino del credito), poi rimettere `"model": "google/gemini-3.8-flash"` in
`opencode.json` e `"default_agent": "architetto"`.

**Attenzione**: in V2 la sessione conserva il modello selezionato **separatamente**
dall'agente: scegliere l'agente `architetto` non cambia il modello della
sessione, e viceversa. Nella CLI l'argomento `--agent` non cambia il modello
(eredita il root): per provare un modello serve `--model` esplicito.

### Perché i modelli sono divisi così

- **Coder = DeepSeek V4.1 Flash**: il più forte della squadra per il codice
  (77,0% su DeepSWE dichiarato da DeepSeek, 75,3% su Terminal Bench 2.0
  secondo Kilo). Scrive **anche i test headless**: un modello debole sui test
  è il rischio che ammorbidisca gli `assert` per farli passare.
- **Ops = Ling 3.1 Flash**: modello MoE da 560B (25B attivi), 238º su 445 in
  coding: adatto a README, documentazione, conf, packaging ed esperimenti ad
  alto volume, dove l'errore costa poco. **Non** scrive i test (vedi sopra).
  Il tier `:free` può essere instabile: si usa il tier a pagamento.
- **Visualizzatore = Nemotron `#none`**: vision-language 120B, orientato a
  OCR/tabelle, 26,5 su Artificial Analysis Intelligence Index. Non serve che
  sia il più intelligente: deve *vedere* e essere veloce. Le varianti
  disponibili sul tier a pagamento sono solo `none` e `thinking`: **`#low`
  non esiste** (esiste sul tier free).
- **Architetto = Gemini 3.8 Flash `#low`**: supporta `low`/`medium`/`high`
  (non `minimal`). Il prezzo introduttivo finisce il 31/12/2026.
  Attenzione: **non** impostare `body.reasoning.enabled: false` su OpenRouter
  per GLM o altri modelli che lo richiedono: l'endpoint risponde
  `Reasoning is mandatory for this endpoint and cannot be disabled`.
- **Tester = Qwen 3.5 9B locale**: 0 €, e il suo compito è solo eseguire e
  copiare una riga. `gpt-oss:20b` **non emette la tool call** nell'app
  (risposta vuota): non è usato.

Dopo una ventina di task, `report.ps1` dice quale agente sbaglia davvero.

## Gli script deterministici

| Script | Funzione | Exit |
|---|---|---|
| `.opencode\scripts\gate.ps1` | **porta d'ingresso unica**: lock, esecuzione, auto-audit, verdetto | 0 / 1 |
| `.opencode\scripts\verify.ps1` | build step + py_compile + gate diff + `INDEX.md` + test (8 in parallelo) | 0 / 1 / 2 |
| `.opencode\scripts\test_core.ps1` | **batteria del nucleo**: 30 controlli, per lo piu' negativi | 0 / 1 |
| `.opencode\scripts\audit_verdict.py` | rifiuta un verdetto non supportato da una run reale (nonce + tag + freschezza) | 0 / 1 |
| `.opencode\scripts\ast_index.py` | genera l'indice AST dei simboli (0 token) | 0 / 2 |
| `.opencode\scripts\ui_math_check.py` | valida `ui_report.txt` e i 2 PNG (decoder PNG puro, **senza PIL**) | 0 / 1 |
| `.opencode\scripts\report.ps1` | riepilogo della telemetria: per agente, ok/fail e durata | 0 |
| `.opencode\scripts\run_ui_probe.ps1` | probe UI + check geometrico in coda | 0 / 1 |
| `.opencode\scripts\run_scout.ps1` | Scout AST su richiesta (mappa in `-Out`) | 0 / 2 |

### Il build step NON e' opzionale

I test importano il **monolite**, che e' un artefatto di build; i **moduli**
sono la fonte di verita'. Se il Coder modifica un modulo e il monolite non
viene ricostruito, i test girano su codice **vecchio** e il gate da' un verde
falso. Per questo `verify.ps1` esegue `packaging\build_monolith.py build`
**prima** dei test.

Semantica del build step: `exit 0` = il monolite era gia' allineato
(`IN_SYNC`), `exit 1` = era disallineato ed e' stato rigenerato (`REBUILT`,
caso normale dopo una modifica), altro = guasto (`FAILED`).

Il test di mutazione in `test_core.ps1` (rompe il codice sorgente e verifica
che il gate se ne accorga) esiste per impedire che questo buco torni.

### Lock sulle verifiche

`verdict.txt` e `metrics.jsonl` sono stato condiviso: `gate.ps1` prende un
lock esclusivo (`.opencode\gate.lock`). Due verifiche contemporanee si
rifiuterebbero a vicenda con `reason=LOCKED`, invece di falsificarsi il
verdetto a vicenda.

### Il nucleo è riusabile: config per progetto

`verify.ps1` e `gate.ps1` sono uguali in ogni progetto addon; cambia solo
`.opencode\verify.config.psd1`:

| Chiave | Significato |
|---|---|
| `Monolith` | sorgente principale (relativo) |
| `Sources` | altri sorgenti da compilare (file o cartelle) |
| `Runner` | script PowerShell che lancia i test |
| `RunnerArgs` | argomenti aggiuntivi del runner (es. `-MaxParallel 8`) |
| `ExpectedTotal` | attesi del run completo (0 = dedotti dal riepilogo) |
| `DiffPaths` | path sui quali misurare il diff |
| `IndexOutput` | dove scrivere l'indice AST ("" = disabilitato) |

Il nucleo è installato e verificato in **ACTD**, **intelligent_uv** e
**CTRL_DEF**. I due formati di riepilogo sono supportati:
`test_x.py  attesi  passati  falliti  esito` (ACTD) e
`RISULTATO passati=N falliti=M` (intelligent_uv, CTRL_DEF).

Un progetto **non ancora versionato con git** non e' un errore: il controllo
del diff viene saltato (`Test-GitRepo`).

### La catena anti-allucinazione

In prova reale (23/10/2026) un subagente ha riportato `VERIFY_OK | passed=538`
**senza aver eseguito nulla**, copiando il numero da `docs/TEST_RESULTS.md` e
inventando campi inesistenti (`suites`, `exec=3.2s`). Il difetto non era
l'allucinazione in sé: era che il verdetto passava dalla **prosa** del modello.

La catena che lo impedisce:

1. `gate.ps1 -TaskTag <TAG>` esegue `verify.ps1` e controlla che la telemetria
   sia cambiata: senza una run nuova esce `VERIFY_FAIL | reason=NO_RUN_RECORDED`.
2. `verify.ps1` genera un **nonce** (`run=<timestamp>-<guid>`) e lo scrive sia
   in `verdict.txt` sia nella riga JSON di `metrics.jsonl`.
3. `audit_verdict.py --expect-tag <TAG>` confronta verdetto e telemetria:
   `RUN_MISMATCH`, `COUNT_MISMATCH`, `TAG_MISMATCH`, `NO_RUN_ID`, `STALE`.

Il modello non può comporre il verdetto: può solo **copiare** una riga che il
codice ha prodotto. Se la copia non combacia con la telemetria, l'audit fallisce.

### I modelli locali nell'app: due errori da non ripetere

1. **Tutti i tool inutili vanno negati.** Con `execute` (Code Mode) disponibile
   e 10 tool esposti, `qwen3.5:9b` rispondeva con testo invece di chiamare
   `shell`. Negando tutto tranne `shell` e `read`, e togliendo dal system
   prompt ogni comando d'esempio, il modello chiama il tool al primo turno.
2. **Un comando scritto nel system prompt viene ricopiato, non eseguito.**
   "Esegui `python .opencode\scripts\gate.py`" faceva rispondere il modello
   con un blocco di codice. Ora l'incarico è: `Chiama il tool shell con
   command="..." e riporta solo la riga finale.`
3. `gpt-oss:20b` (non `-actd-fast`) **non emette la tool call**: esce con
   risposta vuota. `qwen3.5:9b-actd-fast` è il default del tester.

### Prestazioni

Le 11 suite girano in **parallelo, 8 istanze di Blender** (`-MaxParallel 8`):
regressione completa da **35,6 s a 4,0 s**. Ogni suite usa file temporanei
propri (GUID), poi `test_out.txt` viene assemblato in ordine canonico con in
coda i log delle suite fallite.

Note di implementazione (bug già incontrati, non ripetere):

- `python` nel PATH è la **stub del Microsoft Store**: usare sempre
  `C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe`.
- **Get-Content senza `-Encoding UTF8` legge come ANSI** (PowerShell 5.1):
  un file UTF-8 con accenti viene riletto come mojibake e, riscritto, resta
  corrotto. Per file di progetto usare `-Encoding UTF8` o le API .NET
  (`[IO.File]::ReadAllBytes` / `WriteAllBytes`).
- **git scrive warning su stderr** (autocrlf, LF/CRLF): con
  `ErrorActionPreference=Stop` diventano errori fatali. Tutte le chiamate
  git passano da `Invoke-Git`, che isola lo scope e restituisce codice di
  uscita + stdout.
- In PowerShell 5.1 `2>&1` su un processo figlio **solleva** `RemoteException`
  se il figlio scrive su stderr: `$ErrorActionPreference = "Continue"` attorno
  alla chiamata, e `WaitForExit()` prima di `ReadAllText` sui file di redirect.
- **PIL non è installato** nel Python di Blender (numpy sì): `ui_math_check.py`
  decodifica il PNG con `zlib` + unfilter, in stdlib pura.
- `run_all_tests.ps1` **sovrascrive** `test_out.txt` a ogni suite: i conteggi
  si rileggono dalla **tabella finale** del runner, non dal file di log.
- `Set-Content -Encoding UTF8` scrive il **BOM** → i file Python eseguiti dal
  bridge muoiono con `SyntaxError: invalid non-printable character U+FEFF`.
- il rollback di `verify.ps1` usa `git stash push`, non `git checkout --`: il
  lavoro del Coder resta recuperabile con `git stash pop`.
- `Add-Content -Encoding UTF8` in PowerShell 5.1 scrive il BOM: per
  `metrics.jsonl` si usa `[IO.File]::AppendAllText` con `UTF8Encoding($false)`.
- **le righe di fallimento devono avere `task=`**: senza, l'audit riporta un
  fuorviante `TAG_MISMATCH` invece della causa reale.
- `git stash drop` vuole il selettore (`stash@{0}`), non l'hash.
- il build step restituisce **1 quando il monolite era disallineato** (e
  l'ha rigenerato): non e' un errore, e' il caso normale dopo una modifica.

## Skill correlate

- `actd-regressione` — runner, conteggi attesi, lettura del log, diagnostica.
- `actd-probe-ui` — probe deterministico, formato del report, troubleshooting.
- `actd-monolite` — mappa semantica dell'addon e Scout AST.
- `blender-bridge` — il ponte TCP (skill preesistente, tracciata in git).

## Le regole di OpenCode (empiriche, non documentate)

1. **L'ultima regola che combacia vince.** Nelle `permissions` in ordine: prima il wildcard, poi le
   regole specifiche. Con `edit: deny` su `*` e poi `allow` sul path del monolite, il Coder scrive
   **solo** lì: il `deny` finale coprirebbe tutto, quindi l'ordine va invertito rispetto al buon
   senso.
2. **`task` è un'azione come le altre.** Si può negare un subagente:
   `task: { "*": allow, "general": deny }`. Un agente negato **scompare dalla descrizione** del Task
   tool, quindi il modello non lo vede nemmeno.
3. **`steps` è un tetto di step**, non un consiglio: al raggiungimento del tetto il modello riceve
   "rispondi in testo" e la risposta può uscire **vuota**. Dimensionarlo sul flusso reale
   (visualizzatore: 4 azioni + risposta → 6 step con margine).
4. **Nella CLI il `model:` dell'agente viene ignorato**: `opencode run --agent X` eredita il modello
   radice. Nell'app funziona. Nei test da riga di comando passare `--model` **esplicito**.
5. **`temperature` e `permission:` (forma oggetto)** sono validi nel frontmatter YAML dell'agente;
   la chiave della shell è `shell` (non `bash`), e `write` non esiste come chiave (`edit` copre
   `write`, `apply_patch`).
6. **`model` radice e `#variante`**: il root **non conserva** la variante (docs V2). Per il default si
   mette il modello nel root e si forza il reasoning nel `body` del modello; la variante `#thinking`
   vale per sessione/run/agente (`--model ...#thinking`).
7. I **subagenti ereditano il modello del primario** se non ne dichiarano uno.

## Come si sceglie un modello (banco di misura)

Non si sceglie a impressione: ogni ruolo ha un **oracolo**. I test sono stati fatti il 22/10/2026,
stesso prompt per tutti i concorrenti.

| Ruolo | Prova | Oracolo |
|---|---|---|
| architetto | "proponi i primi 3 moduli dello split, righe dallo Scout, max 10 righe" | coerenza del piano, righe verificate, rispetto del contratto di 3 righe |
| coder | 4 difetti reali in un modulo di prova | script di check con 13 assert (esito `BENCH n/13`) + righe cambiate |
| visualizzatore | probe reale + 2 screenshot | `UI_SUMMARY ... flagged=0`: chi annuncia troncamenti si sta inventando un problema |
| tester/scout | mappa di 156 simboli | `SCOUT_OUT ... simboli=156` senza errori di compaction |

Risultati (tempo / esito):

- **architetto**: `gpt-6-luna#low` 29,9 s, 16 righe, piano corretto → **scelto**. `haiku-5.5` 106,5 s ma il più
  onesto (rifiuta di passare numeri non verificati) → riserva. `glm-5.3-flash#low` 59,3 s, inventa un nome classe.
  `qwen3.7-flash` 332 righe di output. `mercury-2.5` 19,3 s ma propone 3 moduli da 1.800 righe.
- **Default attuale (23/10/2026)**: architetto `Gemini 3.8 Flash` con `thinkingLevel: low` forzato via `body.generationConfig.thinkingConfig` nei due `opencode.json`; visualizzatore `Nemotron 3.5 Super VL` (pagato, ~11 s per i due test). Prova reale: 1 delega, 3 righe, 14/14, 17,7 s in IUV. `MiMo-V2.6-Flash` e `Gemma 4 31b-it` restano il fallback documentato.
- **coder**: `deepseek-v4.1-flash` 20,3 s 13/13 (resta); `glm-5.3-flash` 13,5 s 13/13 ma 7 s e 0,0016 $ in meno non
  valgono il cambio su codice `bpy` reale; `haiku-5.5` e `gpt-6-luna` **12/13**, sbagliano entrambi
  `_strip_token` sul suffisso.
- **visualizzatore**: `glm-5.3-flash#low` 16,5 s, 8/8 voci, cita i numeri del report → **scelto**.
  `haiku-5.5` 23,9 s, 8/8 ma 17 righe (IT ed EN separate). `qwen3.8-omni-flash#none` 42,8 s, 7/8 voci (uscita).

Il banco del coder e del visualizzatore è riutilizzabile: i file di prova sono in `%TEMP%\actd_bench\`.

## I modelli che sono stati scartati (e perché)

| Modello | Problema |
|---|---|
| `minimax-m3.1-flash:free` | non disponibile su OpenRouter al momento |
| `inclusionai/ling-3.0-flash-vl` | `Provider returned error` su OpenRouter |
| `inclusionai/ling-3.0-flash` | assegna gli stessi simboli a due moduli (dipendenza circolare) e va in `Compaction summary reached the output token limit` |
| `poolside/laguna-s-2.1` | piano tecnicamente ottimo ma **181 s** a `#low`; ignora i limiti di lunghezza; non è nel catalogo OpenCode (va dichiarato a mano) |
| `inception/mercury-2.5` | 19 s, ma propone moduli da 1.180 e 1.790 righe: granularità inutilizzabile |
| `nvidia/nemotron-3.5-super-vl:free` | funziona, ma **137 s** (il tier `:free` non ha nemmeno la variante `#low`) |
| `qwen/qwen3.8-omni-flash#none` | non scartato: resta il visualizzatore precedente, battuto da glm su tempo (42,8 s vs 16,5 s) e completezza (7/8 voci) |
| `deepseek/deepseek-v4-flash-0731` | 13/13 ma 32,2 s: più lento di entrambi, nessun vantaggio |
| `qwen2.5-coder:14b` (locale) | **non emette le tool call native**: la JSON arriva come testo e Ollama non la converte → non può eseguire il runner né leggere il log |
| `qwen3:14b` (locale) | soppiantato da `qwen3.5:9b` (più piccolo, multimodale, tool call native) |

## Gotcha d'ambiente

- `python` nel PATH è la **stub del Microsoft Store**: usare il path completo del Python di Blender.
- `Set-Content -Encoding UTF8` scrive il **BOM** → i file Python eseguiti dal bridge muoiono con
  `SyntaxError: invalid non-printable character U+FEFF`.
- **Blender non è nel PATH**: sempre il percorso completo dell'eseguibile.
- I path con spazi vanno quotati in `Start-Process`.
