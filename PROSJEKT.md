# Research Agent — Prosjektlogg

Multi-agent AI-system i Python som tar et tema og produserer en kildebelagt
forskningsrapport med kritisk analyse og konkret handlingsplan, lagret som
Markdown, JSON og PDF. Kan kjøres som CLI eller via et Streamlit nettleser-grensesnitt.

**Plassering:** `c:\Users\patgr\research_agent\`
**Modell:** `claude-opus-4-8` (alle tre agenter)

---

## Arkitektur

Tre spesialiserte agenter kjøres sekvensielt, orkestrert av `run.py` (eller `app.py`):

```
Tema → Forskningsagent → Analyseagent → Planleggingsagent → Lagring (md/json/pdf)
```

1. **Forskningsagent** — søker på nettet (`web_search`), henter artikler (`web_fetch`),
   noterer funn med kilde-URL (`ta_notater`), skriver strukturert rapport
2. **Analyseagent** — kritisk evaluering med strukturert JSON-output: mønstre,
   nøkkelfakta, usikkerhet, kunnskapshull, grunnlagsstyrke (sterkt/middels/svakt)
3. **Planleggingsagent** — konkret, faset handlingsplan forankret i research + analyse

---

## Filer

| Fil | Rolle |
|-----|-------|
| `research_agent.py` | Forskningsagent. Agentisk løkke med verktøy. Tidligere `agent.py` (omdøpt). |
| `analyse_agent.py` | Analyseagent. Strukturert JSON via `output_config` json_schema. |
| `planlegging_agent.py` | Planleggingsagent. Streamer plan-tekst. |
| `run.py` | CLI-orkestrator. Kjeder agentene, historikk, lagring, total kjøretid. |
| `app.py` | Streamlit nettleser-grensesnitt. |
| `pdf_generator.py` | Genererer formatert PDF (`RapportPDF` som utvider FPDF). |
| `kjor.bat` | Launcher for CLI. |
| `kjor_app.bat` | Launcher for nettleser-app. |
| `historikk.json` | Logg over tidligere søk med filstier. |
| `requirements.txt` | `anthropic`, `python-dotenv`, `streamlit`, `fpdf2`. |
| `.env` | `ANTHROPIC_API_KEY`. |
| `rapporter/` | Output: `{ts}_{tema}.md/.json`, `_analyse.json`, `_plan.md`, `_rapport.pdf`. |

Tidsstempel-format: `YYYY-MM-DD_HH-MM`. Tema trunkeres til 40 tegn, mellomrom → understrek.

---

## Hvordan kjøre

Fra `c:\Users\patgr\research_agent\` i PowerShell:

```powershell
.\kjor.bat        # CLI-versjon
.\kjor_app.bat    # Nettleser-app (Streamlit på localhost:8501)
```

Merk: `.\` foran er påkrevd i PowerShell. Filnavnet bruker understrek (`kjor_app`), ikke punktum.

Streamlit-appen kjører kun lokalt — ingen kostnad utover API-kall. Lukk terminalen for å stoppe.

---

## Nettleser-grensesnittet (app.py)

- Søkefelt + "Start forskning"-knapp
- Live statusoppdateringer mens agentene kjører (`st.status`)
- Tre faner: **Rapport** / **Analyse** / **Handlingsplan**
- PDF-nedlastingsknapp
- Sidepanel med tidligere søk — **klikk laster lagret rapport fra disk uten API-kall**
  (funksjon `last_lagret_resultat`). Bra for gratis testing av grensesnittet.

---

## Designvalg / konvensjoner

- **Stille terminal-output:** Agentene viser kun statuslinjer (kjører/ferdig), ikke
  søk, URL-er, notater eller full rapport. Alt innhold leses i den ferdige rapporten.
- **Norsk** i all output og alle system-prompts.
- Konsekvent agent-navngiving: `<rolle>_agent.py`.

---

## Viktig fikset bug: tidsstempel-mismatch

**Symptom:** Lagrede rapporter kunne ikke åpnes fra historikken — knappen gjorde ingenting.

**Rotårsak:** Hver agent/funksjon kalte `datetime.now()` på sitt eget tidspunkt.
Forskningsagenten lagret filene sine når den var ferdig (f.eks. 21:36), mens
`run.py` lagret analyse/plan/pdf et minutt senere (21:37) — og registrerte *alle*
stier i historikken med det siste tidsstempelet. Research-stien pekte dermed på en
fil som ikke fantes.

**Løsning:** Ett felles tidsstempel `ts` genereres én gang i `run.py`/`app.py` og
sendes videre:
- `kjor_research(tema, ts)` → `lagre_resultater(..., ts)`
- `lagre_alt(..., ts)`
- `kjor_research` returnerer nå også `md_fil` og `json_fil`; `lagre_alt` bruker disse
  faktiske stiene i `filer`-dicten i stedet for å rekonstruere dem.

**Windows-fallgruve oppdaget underveis:** `glob.glob()` returnerer stier med omvendt
skråstrek (`rapporter\fil`), mens historikken bruker vanlig skråstrek
(`rapporter/fil`). Normaliser med `.replace(os.sep, '/')` ved sammenligning.

---

## Endringslogg

### 2026-06-10
- Omdøpt `agent.py` → `research_agent.py`, oppdatert import i `run.py`
- Fjernet dobbel "AGENT-TEAM STARTER"-linje; forkortet søke-prompten
- Gjorde terminal-output stille (kun status); la til total kjøretid i `run.py`
- Bygget Streamlit-app (`app.py`) + `kjor_app.bat`; installerte `streamlit`, `fpdf2`
- Historikk-knapper laster lagrede rapporter fra disk uten API-kall
- Fikset tidsstempel-bug (felles `ts`); reparerte de tre eksisterende historikk-oppføringene

### 2026-06-11
- **Kostnadsreduksjon:** Analyse- og planleggingsagent flyttet til `claude-sonnet-4-6`
  (forskningsagenten beholder Opus — der ligger kvaliteten). `web_fetch` begrenset til
  8000 tokens/henting + maks 8 hentinger; `web_search` maks 10 søk.
- **Prompt-caching** i forsknings-loopen via `sett_cache_punkt()`: cacher statisk prefiks
  (system + verktøy) og samtalehistorikk med bevegelig breakpoint. Kutter input-kostnad
  i den agentiske loopen.
- **Git satt opp:** repo i prosjektroten, `.gitignore` utelater `.env`. Globale standarder:
  `init.defaultBranch=main` + global gitignore (`C:\Users\patgr\.gitignore_global`).
  Fjernet et tomt, feilplassert git-repo som lå i `rapporter/`.
- **Skylagring (GitHub):** privat repo på https://github.com/patgri72-droid/research_agent
  (`origin`). Installerte `gh` CLI. Push med `git push`.
