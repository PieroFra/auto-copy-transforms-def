---
name: ACTD Squadra
description: Come è organizzata la squadra di subagenti OpenCode del progetto A.C.T.D. (ruoli, modelli, costi, comandi) e le regole/trappole di OpenCode emerse usando l'agente (permessi, steps, modello, CLI). Usare per configurare o modificare la squadra, o prima di scrivere un nuovo agente.
---

# ACTD — La squadra

Configurazione **locale** (non pubblicata): `.opencode/agents/`, `.opencode/commands/`,
`opencode.json`, `.opencode/scripts/`. `AGENTS.md`, `opencode.json`, `.opencode/agents/` e
`.opencode/commands/` sono in `.gitignore`: sono file personali.

## I ruoli

| Ruolo | Modello | Costo | steps | Scope |
|---|---|---|---|---|
| **architetto** (primario) | `openrouter/z-ai/glm-5.3-flash#low` | ~0,0003 €/turno | 24 | orchestra: non modifica file, non esegue test |
| **coder** | `openrouter/deepseek/deepseek-v4.1-flash-1017` | 0,15/0,60 $/M | 12 | **solo** `actd_build\auto_copy_transforms_def.py` |
| **tester / scout** | `ollama/qwen3.5:9b-actd-fast` | **0 €** | 6 | esegue i test; Scout AST |
| **visualizzatore** | `openrouter/qwen/qwen3.8-omni-flash#none` | ~0,001 €/run | 6 | sola presentazione visiva della UI |
| **repo-ops** | `openrouter/deepseek/deepseek-v4.1-flash-1017` | 0,15/0,60 $/M | 14 | test, `README*`, `AGENTS.md`, `packaging\*`; **mai** il monolite |

Comandi: `/architetto` · `/mappa <filtro>` · `/codifica <cosa>` · `/test [suite]` · `/revisiona` · `/rilascia`.

Stack locale su `E:\AI`: `qwen3.5:9b-actd-fast` (6,6 GB, tag creato con
`PARAMETER temperature 0.0 / num_ctx 16384 / num_predict 2048`).

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
6. **`model` radice e `#variante`**: il root conserva la variante solo se scritta esplicitamente.
7. I **subagenti ereditano il modello del primario** se non ne dichiarano uno.

## I modelli che sono stati scartati (e perché)

| Modello | Problema |
|---|---|
| `minimax-m3.1-flash:free` | non disponibile su OpenRouter al momento |
| `inclusionai/ling-3.0-flash-vl` | `Provider returned error` su OpenRouter |
| `nvidia/nemotron-3.5-super-vl:free` | funziona, ma **137 s** (il tier `:free` non ha nemmeno la variante `#low`) |
| `qwen2.5-coder:14b` (locale) | **non emette le tool call native**: la JSON arriva come testo e Ollama non la converte → non può eseguire il runner né leggere il log |
| `qwen3:14b` (locale) | soppiantato da `qwen3.5:9b` (più piccolo, multimodale, tool call native) |

## Gotcha d'ambiente

- `python` nel PATH è la **stub del Microsoft Store**: usare il path completo del Python di Blender.
- `Set-Content -Encoding UTF8` scrive il **BOM** → i file Python eseguiti dal bridge muoiono con
  `SyntaxError: invalid non-printable character U+FEFF`.
- **Blender non è nel PATH**: sempre il percorso completo dell'eseguibile.
- I path con spazi vanno quotati in `Start-Process`.
