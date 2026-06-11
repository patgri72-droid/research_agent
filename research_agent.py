import anthropic
import json
import os
import sys
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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

VERKTOY = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 10},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 8, "max_content_tokens": 8000},
    {
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
    },
]

SYSTEM_PROMPT = """Du er en avansert forskningsagent. Når du får et tema å undersøke:

1. Del temaet opp i 3-5 konkrete delspørsmål
2. Søk etter svar på hvert delspørsmål — gjør minst 4-6 søk totalt
3. Les relevante artikler i sin helhet med web_fetch når du trenger mer dybde
4. Bruk ta_notater underveis — oppgi ALLTID full URL som kilde
5. Skriv en strukturert rapport med følgende format:

---
## Sammendrag
[3-5 setninger som oppsummerer de viktigste funnene]

## [Delspørsmål 1]
[Funn med in-text sitering, f.eks. ifølge [kilde1]]

## [Delspørsmål 2]
...

## Konklusjon
[Helhetlig vurdering]

## Kilder
- [1] <full URL>
- [2] <full URL>
...
---

VIKTIG: Siter kilden direkte i teksten der du bruker informasjonen. Alle URL-er MÅ være med i kildelisten.
Skriv rapporten på norsk."""

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

def kjor_research(tema: str, tidsstempel: str = None) -> dict:
    global notater
    notater = []

    print(f"  Forskningsagent kjører...")

    meldinger = [{"role": "user", "content": f"Undersøk grundig: {tema}"}]
    endelig_rapport = ""
    container_id = None  # Brukes av web_search sin interne kode-eksekvering

    # Statisk prefiks (system + verktøy) caches på tvers av alle runder
    system_blokker = [{"type": "text", "text": SYSTEM_PROMPT,
                       "cache_control": {"type": "ephemeral"}}]

    while True:
        sett_cache_punkt(meldinger)
        kall_kwargs = dict(
            model="claude-opus-4-8",
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=system_blokker,
            tools=VERKTOY,
            messages=meldinger,
        )
        if container_id:
            kall_kwargs["container"] = container_id

        with Spinner("Søker og analyserer"):
            respons = client.messages.create(**kall_kwargs)

        if hasattr(respons, "container") and respons.container:
            container_id = respons.container.id

        for blokk in respons.content:
            if blokk.type == "text" and blokk.text:
                endelig_rapport = blokk.text

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
                    resultater.append({
                        "type": "tool_result",
                        "tool_use_id": blokk.id,
                        "content": json.dumps(resultat, ensure_ascii=False),
                    })
            meldinger.append({"role": "user", "content": resultater})

    md_fil, json_fil = lagre_resultater(tema, endelig_rapport, notater, tidsstempel)
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
