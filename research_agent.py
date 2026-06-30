import anthropic
import json
import os
import sys
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

from config import AgentConfig, STANDARD_CONFIG, KjoringStoppet

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# --- Hendelser (live-oppdateringer til nettsiden) ---
#
# Agentene kjenner ikke til Streamlit. De kaller en valgfri `hendelse`-callback
# med en enkel dict; app.py legger den på en kø og tegner den. Når `hendelse`
# er None (CLI), skjer ingenting — uendret oppførsel.

def _meld(hendelse, **felt):
    if hendelse is not None:
        hendelse(felt)


def _forbruk(hendelse, modell, respons):
    """Sender token-forbruket fra ett svar videre til kostnadsestimatet."""
    u = getattr(respons, "usage", None)
    if hendelse is None or u is None:
        return
    _meld(hendelse, t="forbruk", modell=modell,
          input=getattr(u, "input_tokens", 0) or 0,
          output=getattr(u, "output_tokens", 0) or 0,
          cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
          cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0)

# --- Spinner (viser at agenten jobber) ---

class Spinner:
    def __init__(self, melding="Jobber"):
        self._melding = melding
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()
        sys.stdout.write(f"\r{' ' * (len(self._melding) + 6)}\r")
        sys.stdout.flush()

    def _loop(self):
        tegn = ["-", "\\", "|", "/"]
        i = 0
        while not self._stop.is_set():
            sys.stdout.write(f"\r  {tegn[i % 4]} {self._melding}...")
            sys.stdout.flush()
            time.sleep(0.15)
            i += 1

# --- Notater (arbeidsminne under research) ---

notater = []

def ta_notater(notat: str, kilde: str = "") -> dict:
    notater.append({"notat": notat, "kilde": kilde})
    return {"status": "Lagret", "totalt_antall": len(notater)}

def kjor_verktoy(navn: str, input_data: dict):
    if navn == "ta_notater":
        return ta_notater(input_data["notat"], input_data.get("kilde", ""))
    return {"feil": f"Ukjent verktøy: {navn}"}

# --- Verktøy tilgjengelig for agenten ---

# Notat-verktøyet er statisk; web_search/web_fetch bygges fra config.
NOTAT_VERKTOY = {
    "name": "ta_notater",
    "description": "Lagre et viktig funn, faktum eller konklusjon. Oppgi alltid kildens URL i 'kilde'-feltet.",
    "input_schema": {
        "type": "object",
        "properties": {
            "notat": {"type": "string", "description": "Funnet eller faktumet du vil huske"},
            "kilde": {"type": "string", "description": "Full URL til siden du hentet informasjonen fra"},
        },
        "required": ["notat", "kilde"],
    },
}


def bygg_verktoy(config: AgentConfig) -> list:
    """Setter sammen verktøylista med grensene fra config."""
    return [
        {"type": "web_search_20260209", "name": "web_search",
         "max_uses": config.maks_sok},
        {"type": "web_fetch_20260209", "name": "web_fetch",
         "max_uses": config.maks_hentinger,
         "max_content_tokens": config.hente_token_grense},
        NOTAT_VERKTOY,
    ]

# --- Lagre rapport og data ---

def lagre_resultater(tema: str, rapport: str, notat_liste: list, tidsstempel: str = None) -> tuple[str, str]:
    os.makedirs("rapporter", exist_ok=True)
    if tidsstempel is None:
        tidsstempel = datetime.now().strftime("%Y-%m-%d_%H-%M")
    base = f"rapporter/{tidsstempel}_{tema[:40].replace(' ', '_')}"

    with open(f"{base}.md", "w", encoding="utf-8") as f:
        f.write(f"# {tema}\n\n")
        f.write(f"*Generert: {datetime.now().strftime('%d.%m.%Y %H:%M')}*\n\n")
        f.write(rapport)

    data = {
        "tema": tema,
        "timestamp": datetime.now().isoformat(),
        "rapport": rapport,
        "notater": notat_liste,
    }
    with open(f"{base}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return f"{base}.md", f"{base}.json"

# --- Prompt-caching ---

def sett_cache_punkt(meldinger: list):
    """Flytter cache-breakpoint til siste melding så samtalehistorikken
    gjenbrukes billig i hver loop-runde. Fjerner gamle breakpoints først
    (API-et tillater maks 4)."""
    for m in meldinger:
        innhold = m["content"]
        if isinstance(innhold, list):
            for blokk in innhold:
                if isinstance(blokk, dict):
                    blokk.pop("cache_control", None)

    siste = meldinger[-1]
    innhold = siste["content"]
    if isinstance(innhold, str):
        siste["content"] = [{"type": "text", "text": innhold,
                             "cache_control": {"type": "ephemeral"}}]
    elif isinstance(innhold, list) and innhold and isinstance(innhold[-1], dict):
        innhold[-1]["cache_control"] = {"type": "ephemeral"}

# --- Agenløkken ---

def kjor_research(tema: str, tidsstempel: str = None,
                  config: AgentConfig = None, hendelse=None, stopp=None) -> dict:
    global notater
    notater = []
    if config is None:
        config = STANDARD_CONFIG

    _meld(hendelse, t="status", tekst="Forskningsagent kjører…")
    if hendelse is None:
        print(f"  Forskningsagent kjører...")

    meldinger = [{"role": "user", "content": f"Undersøk grundig: {tema}"}]
    endelig_rapport = ""
    container_id = None  # Brukes av web_search sin interne kode-eksekvering

    verktoy = bygg_verktoy(config)

    # Statisk prefiks (system + verktøy) caches på tvers av alle runder
    system_blokker = [{"type": "text", "text": config.research_prompt,
                       "cache_control": {"type": "ephemeral"}}]

    while True:
        if stopp is not None and stopp.is_set():
            raise KjoringStoppet()

        sett_cache_punkt(meldinger)
        kall_kwargs = dict(
            model=config.research_modell,
            max_tokens=config.research_max_tokens,
            thinking={"type": "adaptive"},
            system=system_blokker,
            tools=verktoy,
            messages=meldinger,
        )
        if container_id:
            kall_kwargs["container"] = container_id

        if hendelse is None:
            with Spinner("Søker og analyserer"):
                respons = client.messages.create(**kall_kwargs)
        else:
            respons = client.messages.create(**kall_kwargs)

        _forbruk(hendelse, config.research_modell, respons)

        if hasattr(respons, "container") and respons.container:
            container_id = respons.container.id

        for blokk in respons.content:
            if blokk.type == "text" and blokk.text:
                endelig_rapport = blokk.text
            elif blokk.type == "server_tool_use":
                detalj = blokk.input or {}
                if blokk.name == "web_search":
                    _meld(hendelse, t="verktoy", navn="web_search",
                          detalj=detalj.get("query", ""))
                elif blokk.name == "web_fetch":
                    _meld(hendelse, t="verktoy", navn="web_fetch",
                          detalj=detalj.get("url", ""))

        if respons.stop_reason == "end_turn":
            break

        meldinger.append({"role": "assistant", "content": respons.content})

        if respons.stop_reason == "pause_turn":
            meldinger.append({"role": "user", "content": "Fortsett forskningen."})
            continue

        if respons.stop_reason == "tool_use":
            resultater = []
            for blokk in respons.content:
                if blokk.type == "tool_use":
                    resultat = kjor_verktoy(blokk.name, blokk.input)
                    if blokk.name == "ta_notater":
                        _meld(hendelse, t="notat",
                              antall=resultat.get("totalt_antall", len(notater)))
                    resultater.append({
                        "type": "tool_result",
                        "tool_use_id": blokk.id,
                        "content": json.dumps(resultat, ensure_ascii=False),
                    })
            meldinger.append({"role": "user", "content": resultater})

    md_fil, json_fil = lagre_resultater(tema, endelig_rapport, notater, tidsstempel)
    _meld(hendelse, t="status", tekst=f"Forskningsagent ferdig — {len(notater)} notater")
    if hendelse is None:
        print(f"  Ferdig — {len(notater)} notater")

    return {
        "tema": tema,
        "timestamp": datetime.now().isoformat(),
        "rapport": endelig_rapport,
        "notater": notater,
        "md_fil": md_fil,
        "json_fil": json_fil,
    }

# --- Kjør direkte ---

if __name__ == "__main__":
    print("Forskningsagent klar! Skriv 'avslutt' for å stoppe.\n")
    while True:
        tema = input("Hva vil du forske på? ").strip()
        if not tema:
            continue
        if tema.lower() == "avslutt":
            break
        kjor_research(tema)
