# Research Agent — Prosjektlogg

Multi-agent AI-system i Python som tar et tema og produserer en kildebelagt
forskningsrapport med kritisk analyse og konkret handlingsplan, lagret som
Markdown, JSON og PDF. Kan kjøres som CLI eller via et Streamlit nettleser-grensesnitt.

**Plassering:** `c:\Users\patgr\research_agent\`
**Modell:** Konfigurerbar per agent i nettsiden (standard: Opus 4.8 for research, Sonnet 4.6 for analyse/plan)

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
| `config.py` | `AgentConfig` (dataclass) + `MODELLER` + standard-prompts. Ett sted for all agent-styring. |
| `research_agent.py` | Forskningsagent. Agentisk løkke med verktøy. Tidligere `agent.py` (omdøpt). |
| `analyse_agent.py` | Analyseagent. Strukturert JSON via `output_config` json_schema. |
| `planlegging_agent.py` | Planleggingsagent. Streamer plan-tekst. |
| `linkedin_agent.py` | LinkedIn-agent. Leser prosjektlogg + git + `claude_logg/`, skriver tospråklig post m/ bilde-prompter via json_schema. Frittstående (ikke i `run.py`-kjeden). |
| `kjor_linkedin.bat` | Launcher for LinkedIn-agenten. |
| `claude_logg/` | Slipp `.md`/`.txt`-notater fra Claude-økter her — råmateriale for poster. |
| `linkedin/` | Output: `{ts}_{tittel}.md` (ferdig post + bilde-prompter) og `.json`. |
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
- **Innstillingspanel** i sidepanelet (`bygg_config_panel`): modellvalg per agent, søke-/hentegrenser,
  token-grenser, av/på for analyse- og planleggingstrinn, og redigerbare system-prompts.
  Bygger en `AgentConfig` som sendes inn i agentene. Avskrudde trinn hopper over fane + fil + PDF-seksjon.

---

## Agent-hub (hjemmeside)

`app.py` åpner nå på en **hub** — en hjemmeside med klikkbare agent-bobler (kort),
én per agent, bygget fra `AGENTER`-registeret. Enkel ruter i `session_state`
(`aktiv_agent` + `gaa_til`). Research-agenten er koblet inn (`vis_research_agent`);
LinkedIn-agenten vises som "Kommer snart" (`render: None` — finnes som CLI, mangler webview).
Ny agent legges til på én linje i `AGENTER` + en `vis_<navn>()`-funksjon.

---

## Fase 2 — ikke-blokkerende kjøring med live-aktivitet, Stopp og kostnad (BYGGET)

Agentene kjøres nå i en **bakgrunnstråd** og rapporterer live til nettsiden, med en
alltid-klikkbar **Stopp**-knapp og et **kostnadsestimat** basert på faktisk tokenforbruk.

**Slik henger det sammen:**

1. **Hendelses-callback** — `kjor_research/analyse/planlegging(..., hendelse=None, stopp=None)`.
   Agentene kaller `hendelse({...})` med enkle dict-er (`status`, `verktoy`, `notat`,
   `forbruk`) — aldri `st.*`. Standard `None` = uendret CLI-oppførsel. Forbruk leses fra
   `respons.usage` (input/output + `cache_read`/`cache_write` hver for seg). Søk/henting
   leses fra `server_tool_use`-blokker i svaret.
2. **`kjor_pipeline()` i `run.py`** — kjeder research→analyse→plan→lagring og tar
   `hendelse`/`stopp`. Brukt av både CLI og web. Avskrudde trinn hoppes over som før.
3. **Bakgrunnstråd + kø (`app.py`)** — `start_kjoring()` starter en `threading.Thread`
   som kjører `kjor_pipeline` og dytter hendelser på en `queue.Queue`. Tråden rører kun
   køen + stopp-signalet, aldri `session_state`/`st.*`. Sluttresultatet sendes som en
   `ferdig`/`stoppet`/`feil`-hendelse på køen (tråden skriver ikke session_state selv).
4. **Stopp** — `threading.Event` sjekkes øverst i forskningsloopen og før hver agent;
   agentene reiser `KjoringStoppet` (definert i `config.py`), tråden fanger den.
   Granularitet: mellom API-kall (et pågående kall fullføres — sekunder).
5. **Live-visning** — `st.fragment(run_every=1.0)` tømmer køen og tegner status, tid,
   notat-antall, tokens og `$`-estimat hvert sekund. Stopp-knappen ligger **utenfor**
   fragmentet (full app-rerun) så den alltid er klikkbar. Når tråden er ferdig bytter
   fragmentet til resultatvisning via `st.rerun(scope="app")`.

**Kostnad:** `MODELL_PRISER` + `kostnad_for()` i `config.py` (priser per 1M tokens fra
API-referansen). Cache-lesing vektes 0,1x, cache-skriving 1,25x — så den agentiske loopen
ikke overvurderes. Estimatet vises live og lagres på resultatet (`_kostnad`/`_tokens`).

**Demo-modus:** `kjor_demo()` i `run.py` har samme `hendelse`/`stopp`-grensesnitt som
`kjor_pipeline`, men sender oppdiktede hendelser med korte pauser — **ingen API-kall, ingen
søk, ingen kostnad, ingen filer**. Knappen «▶ Demo (uten søk)» i `app.py` kjører den i samme
bakgrunnstråd, så du ser hele live-grensesnittet (søk, henting, notater, tokens, $-estimat,
Stopp) gratis. Live-visningen merkes med et DEMO-banner.

Testet headless (`AppTest`): hub + research-vy rendrer, begge knappene (Start + Demo) finnes,
alle moduler importerer rent, `kostnad_for` gir riktig sum, `kjor_demo` emitterer riktige
hendelser og respekterer stopp. Ekte live-kjøring krever API-kall — demoen gjør ikke det.

---

## Fase 3 — «Tilgjengelig overalt» (PLANLAGT, IKKE BYGGET)

Mål: få appen ut på nett så den kan åpnes fra hvor som helst (mobil/annen PC) via en URL,
trygt og kostnadskontrollert. Ikke en ny agent-funksjon — et **deploy- og tilgangssteg**.

**Steg (i rekkefølge, lav→høyere risiko):**

1. **API-nøkkel fra ett sted** — lag `hent_api_nokkel()` i `config.py` som prøver
   `st.secrets["ANTHROPIC_API_KEY"]` først (sky) og faller tilbake til `os.getenv` / `.env`
   (lokalt). Alle agentene (`research/analyse/planlegging/linkedin`) bytter
   `os.getenv("ANTHROPIC_API_KEY")` → denne helperen. Da virker samme kode lokalt og i skyen.
   *Lav risiko, ingen UI-endring.*

2. **Passord-port** — en enkel gate øverst i `app.py`: `st.text_input(type="password")`
   sammenlignet mot `st.secrets["APP_PASSORD"]`, husket i `session_state`. Appen vises kun
   etter riktig passord. Hindrer at fremmede brenner API-tokens. *Lav risiko.*

3. **Flyktig disk i skyen** — på Streamlit Community Cloud forsvinner filer ved restart/dvale,
   så `historikk.json`, `rapporter/` og `linkedin/` overlever ikke slik de gjør lokalt.
   Tre alternativer (velg én):
   - **(a) Akseptér flyktighet** *(anbefalt MVP)* — historikk nullstilles ved restart;
     rapporter lastes ned med PDF-knappen mens økten lever. Kostnadsestimat + nedlasting
     gjør dette brukbart. Minst arbeid.
   - **(b) Commit til GitHub** — appen pusher historikk/rapporter til repoet (krever
     GitHub-token som secret). Mer robust, mer kompleksitet.
   - **(c) Ekstern lagring** — gratis DB (Supabase/Google Sheets). Mest robust, mest arbeid.

4. **Deploy** — repoet ligger allerede på privat GitHub (`origin`). På share.streamlit.io:
   «New app» → velg repo + branch + `app.py` → legg `ANTHROPIC_API_KEY` og `APP_PASSORD`
   inn under app-ets **Secrets**. Verifiser at `requirements.txt` er komplett
   (`anthropic`, `python-dotenv`, `streamlit`, `fpdf2`).

5. **Robusthet + kostnadskontroll i skyen** — test lange kjøringer mot skyens
   inaktivitets-timeout (bakgrunnstråd + `st.fragment` fungerer, men en kjøring kan kollidere
   med dvale). Vurder en hard øvre grense på `maks_sok`/`maks_hentinger` i skyversjonen.
   Demo-modus + synlig `$`-estimat (fase 2) er gode sikkerhetsnett mot overraskelser her.

**Avhengighet:** bør gjøres ETTER at fase 2 er committet (trygt sjekkpunkt før deploy).

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

### 2026-06-30 (grensesnitt-forbedringer)
- **Skrivefeltene vokser nedover i stedet for å renne ut av skjermen:** `st.text_input`
  byttet til `st.text_area` for både tema (research) og vinkling (LinkedIn), med CSS
  `field-sizing: content` (min-høyde ~1 linje, maks 30vh). Bryter linja og vokser ved
  behov. Krever nyere Chromium (Chrome/Edge 123+).
- **Liten rød→grønn søkeknapp i Research-agenten:** den brede «Start forskning»-baren
  (`use_container_width=True`) erstattet med en kompakt «🔍 Søk»-knapp. Fargen styres ved
  at knappen bytter `key` (`sok_tom`/`sok_klar`) etter om boksen har tekst — CSS-klassene
  `.st-key-sok_tom`/`.st-key-sok_klar` gir rød (tom) / grønn (klar). Demo-knappen krympet
  tilsvarende. Merk: i et flerlinjet felt sender vanlig Enter en ny linje; fargen slår om
  når teksten bekreftes (Ctrl+Enter / klikk ut) — en Streamlit-begrensning (vokse vs.
  Enter-send er gjensidig utelukkende).
- **Innstillinger flyttet fra sidepanelet til hovedområdet** for begge agentene: en
  høyrekolonne (`st.columns([3, 2])`) holder innstillingene mens søkeboksen ligger til
  venstre. Sidepanelet er nå lett — Research beholder «Tidligere søk», LinkedIn bare
  navigasjon. `config` bygges i høyrekolonnen før venstrekolonnens knapp bruker den.
  Stiler en spesifikk widget via `.st-key-<key>`-klassen (Streamlit 1.58).
- Commit `f4051c7` på `main` (kun `app.py`). Ikke pushet.

### 2026-06-10
- Omdøpt `agent.py` → `research_agent.py`, oppdatert import i `run.py`
- Fjernet dobbel "AGENT-TEAM STARTER"-linje; forkortet søke-prompten
- Gjorde terminal-output stille (kun status); la til total kjøretid i `run.py`
- Bygget Streamlit-app (`app.py`) + `kjor_app.bat`; installerte `streamlit`, `fpdf2`
- Historikk-knapper laster lagrede rapporter fra disk uten API-kall
- Fikset tidsstempel-bug (felles `ts`); reparerte de tre eksisterende historikk-oppføringene

### 2026-06-11 (senere — styringsgrensesnitt fase 1)
- **`config.py` lagt til:** `AgentConfig`-dataclass samler all agent-styring (modeller, token-grenser,
  søke-/hentegrenser, av/på-trinn, system-prompts). Standardverdier = uendret oppførsel.
- **Agentene tar nå `config`:** `kjor_research/analyse/planlegging(... , config)`. Verktøylista bygges
  fra config (`bygg_verktoy`). Hardkodede modeller/prompts/grenser fjernet fra agent-filene.
- **Innstillingspanel i `app.py`** (`bygg_config_panel`) — styr alt fra nettsiden uten å redigere kode.
- **Valgfrie trinn:** analyse/plan kan skrus av. `lagre_alt` + `generer_pdf` hopper over manglende
  deler; visningen bygger bare fanene som har innhold. Plan tvinges av hvis analyse er av (`__post_init__`).
- Fikset tomt-label-varsel på søkefeltet (`"Tema"` + `label_visibility="collapsed"`).
- Testet med Streamlit `AppTest` (headless) — ingen runtime-feil, alle widgets rendrer.

### 2026-06-11 (hub + fase 2-design)
- **Agent-hub:** `app.py` refaktorert til hub-struktur — hjemmeside med agent-bobler,
  `session_state`-ruter, research-grensesnitt pakket i `vis_research_agent`, `AGENTER`-register.
  Testet headless med `AppTest` (to bobler, "Åpne"/"Tilbake"-navigasjon virker). Commit `b5951f5`.
- **Fase 2 designet, ikke bygget:** ikke-blokkerende kjøring (bakgrunnstråd + hendelses-kø +
  `threading.Event`-stopp + `st.fragment(run_every)`) med kostnadsestimat. Se egen seksjon over.
  Stoppet rett før implementasjon — neste steg var å hente modellpriser fra API-referansen.

### 2026-06-11 (fase 2 bygget)
- **`config.py`:** `MODELL_PRISER` (USD/1M, fra API-referansen) + `kostnad_for()` (vekter
  cache-lesing 0,1x / -skriving 1,25x) + `KjoringStoppet`-unntak.
- **Agentene tar `hendelse=None, stopp=None`:** sender live-hendelser (`status`/`verktoy`/
  `notat`/`forbruk`) via callback og sjekker stopp. Forbruk fra `respons.usage`; søk/henting
  fra `server_tool_use`-blokker. `None` = uendret CLI-oppførsel (Spinner/print beholdt).
- **`run.py`:** ny `kjor_pipeline()` som kjeder agentene + lagrer; brukt av CLI og web.
- **`app.py`:** bakgrunnstråd + `queue.Queue` + `st.fragment(run_every=1.0)` live-visning
  (tid/notater/tokens/$-estimat), Stopp-knapp utenfor fragmentet. Resultat/feil/stopp sendes
  som hendelse på køen; tråden rører aldri `st.*`. Resultatvisning faktorert til `vis_resultater`.
- **Demo-modus:** `kjor_demo()` i `run.py` + «▶ Demo (uten søk)»-knapp i `app.py` — viser hele
  live-grensesnittet med oppdiktede hendelser, uten API-kall/søk/kostnad/filer. Banner i live-vyen.
- Testet headless (`AppTest` + kompilering + `kostnad_for` + `kjor_demo`-hendelser/stopp).
- **Fase 3 planlagt** (ikke bygget): deploy til Streamlit Community Cloud — secrets-basert
  API-nøkkel, passord-port, håndtering av flyktig disk, deploy-oppskrift. Se "Fase 3"-seksjonen.
- Merknad: Streamlit re-importerer ikke moduler ved nettleser-reload — restart serveren
  (Ctrl+C + `.\kjor_app.bat`) etter endringer i importerte filer (`run.py`/`config.py`/agenter).

### 2026-06-30 (robusthet i forskningsloopen — teknisk gjeld utbedret)
- **Loop kunne henge / brenne tokens ved uventet `stop_reason`:** `while True`-loopen i
  `research_agent.py` håndterte bare `end_turn`/`pause_turn`/`tool_use`. Ved `max_tokens`
  (for lang rapport) eller `refusal` traff ingen gren `break` → samtalen ble re-sendt i det
  uendelige. **Fikset:** uventet `stop_reason` bryter nå loopen og beholder den (eventuelt
  delvise) rapporten; tom rapport får en tydelig plassholdertekst.
- **Ingen øvre grense på antall runder:** la til `maks_runder = maks_sok + maks_hentinger + 20`
  som hard sikkerhetsvakt (skalerer med verktøybudsjettet). Hindrer evig loop også ved
  vedvarende `pause_turn`.
- **Verifisert med enhetstest (mocket Anthropic-klient):** `max_tokens` bryter etter 1 runde
  og beholder delrapport; evig `pause_turn` stoppes av maks-runde-vakta. Første ekte test av
  selve loop-logikken uten API-kall (jf. svakhet «kjernelogikken er utestet»).
- Gjenstående kjente svakheter (ikke fikset): kostnadsestimatet teller ikke server-verktøyenes
  egen pris (websøk faktureres separat); `notater` er en modul-global (ikke trådsikker ved
  samtidige kjøringer); analyse/plan sjekker `stopp` kun ved start; `historikk.json` skrives
  ikke-atomisk. Se egen gjennomgang i samtalehistorikken.

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
- **LinkedIn-agent (`linkedin_agent.py`):** ny, frittstående agent som lager LinkedIn-poster
  om vibe-coding-reisen. Leser råmateriale fra prosjektloggen, nylige git-commits og
  `.md`/`.txt`-notater i `claude_logg/`. Tar en *vinkling* + en *stilbeskrivelse*
  (`linkedin_stil` i config — den viktigste knappen for stemmen). Strukturert output via
  json_schema (post_norsk, post_engelsk, bilde_prompter, skjermbilde_forslag, hashtags).
  Tospråklig som standard (norsk øverst, skille, engelsk under); `linkedin_sprak` kan settes
  til `"norsk"` eller `"engelsk"`. Lagrer ferdig post + bilde-prompter i `linkedin/`.
  Kjør: `.\kjor_linkedin.bat "vinkling"`. Windows-merknad: `sys.stdout.reconfigure("utf-8")`
  i `__main__` så emoji ikke kveler cp1252-konsollen (filer skrives uansett UTF-8).
