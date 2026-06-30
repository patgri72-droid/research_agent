"""
LinkedIn-agent
--------------
Leser progresjonen din i prosjektet (prosjektlogg + git-historikk + notater fra
Claude-økter) og skriver en ferdig, engasjerende LinkedIn-post i din stemme — med
forslag til bilde-prompter og hvor dine egne skjermbilder passer.

Stemmen styres av `linkedin_stil` i config.py (rediger den for å treffe deg).
Språk styres av `linkedin_sprak`: "begge" (norsk øverst, engelsk under), "norsk"
eller "engelsk".

Kjør:
    python linkedin_agent.py "vinkling for posten"
    python linkedin_agent.py            # spør om vinkling interaktivt
"""

import anthropic
import json
import os
import subprocess
import sys
from datetime import datetime

from config import AgentConfig, STANDARD_CONFIG, hent_api_nokkel

# Nøkkelen hentes sentralt: st.secrets i skyen, .env/miljø lokalt.
client = anthropic.Anthropic(api_key=hent_api_nokkel())

# --- Samle råmateriale ---

def hent_git_logg(antall: int) -> str:
    """Henter de siste commit-meldingene som en kort logg over hva som er gjort."""
    try:
        ut = subprocess.run(
            ["git", "log", f"-n{antall}", "--pretty=format:- %ad %s", "--date=short"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        return ut.stdout.strip() or "(ingen commits funnet)"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "(git-historikk utilgjengelig)"


def _les_mappe(mappe: str, nyeste_forst: bool = False):
    """Yt (filnavn, innhold) for hver ikke-tomme .md/.txt-fil i mappa.

    Felles skjelett for å lese tekstfiler — sorterer etter filnavn (sett
    `nyeste_forst=True` for nyeste øverst) og hopper stille over filer som
    ikke kan leses.
    """
    if not os.path.isdir(mappe):
        return
    for navn in sorted(os.listdir(mappe), reverse=nyeste_forst):
        if not navn.lower().endswith((".md", ".txt")):
            continue
        try:
            with open(os.path.join(mappe, navn), encoding="utf-8") as f:
                tekst = f.read().strip()
        except OSError:
            continue
        if tekst:
            yield navn, tekst


def les_tekstfiler(mappe: str) -> str:
    """Leser alle .md/.txt-filer i en mappe — dine notater fra Claude-økter."""
    return "\n\n".join(f"### Fil: {navn}\n{tekst}" for navn, tekst in _les_mappe(mappe))


def les_godkjente_poster(config: AgentConfig) -> str:
    """Leser dine egne ferdig-redigerte poster som stileksempler.

    Dette er slik agenten "lærer" stemmen din over tid: jo flere poster du
    godkjenner og legger i mappa, jo nærmere treffer den din faktiske stil.
    Tar de nyeste først (etter filnavn) og begrenser til config-antallet.
    """
    biter = []
    for navn, tekst in _les_mappe(config.linkedin_godkjent_mappe, nyeste_forst=True):
        if navn.upper().startswith("LES_MEG"):
            continue
        biter.append(f"--- Eksempelpost ---\n{tekst}")
        if len(biter) >= config.linkedin_godkjent_antall:
            break
    return "\n\n".join(biter)


def samle_kontekst(config: AgentConfig) -> str:
    """Setter sammen alt råmaterialet agenten skal bygge posten på."""
    deler = []

    if os.path.exists(config.prosjekt_logg_fil):
        with open(config.prosjekt_logg_fil, encoding="utf-8") as f:
            deler.append(f"=== PROSJEKTLOGG ({config.prosjekt_logg_fil}) ===\n{f.read().strip()}")

    deler.append(f"=== NYLIGE GIT-COMMITS ===\n{hent_git_logg(config.git_logg_antall)}")

    notater = les_tekstfiler(config.claude_logg_mappe)
    if notater:
        deler.append(f"=== NOTATER FRA CLAUDE-ØKTER ({config.claude_logg_mappe}/) ===\n{notater}")

    return "\n\n".join(deler)

# --- Output-skjema (strukturert post) ---

POST_SKJEMA = {
    "type": "object",
    "properties": {
        "arbeidstittel": {
            "type": "string",
            "description": "Kort intern tittel på posten (til filnavn, vises ikke i posten)",
        },
        "post_norsk": {
            "type": "string",
            "description": "Hele den ferdige posten på norsk, med linjeskift og emoji. Tom streng hvis kun engelsk.",
        },
        "post_engelsk": {
            "type": "string",
            "description": "Hele den ferdige posten på engelsk. Tom streng hvis kun norsk.",
        },
        "bilde_prompter": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "plassering": {"type": "string", "description": "Hvor i posten bildet hører hjemme, f.eks. 'toppbilde'"},
                    "prompt": {"type": "string", "description": "Detaljert bilde-prompt på engelsk, klar for Midjourney/DALL-E"},
                },
                "required": ["plassering", "prompt"],
                "additionalProperties": False,
            },
            "description": "1-3 bilde-prompter som passer posten",
        },
        "skjermbilde_forslag": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Konkret hva dine egne skjermbilder fra prosjektet bør vise",
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-6 relevante hashtags",
        },
    },
    "required": ["arbeidstittel", "post_norsk", "post_engelsk",
                 "bilde_prompter", "skjermbilde_forslag", "hashtags"],
    "additionalProperties": False,
}

# --- Agenten ---

def kjor_linkedin(vinkling: str, config: AgentConfig = None,
                  ekstra_kontekst: str = "") -> dict:
    if config is None:
        config = STANDARD_CONFIG

    kontekst = samle_kontekst(config)
    if ekstra_kontekst:
        kontekst += f"\n\n=== EKSTRA KONTEKST FRA DEG ===\n{ekstra_kontekst}"

    eksempler = les_godkjente_poster(config)
    eksempel_blokk = ""
    if eksempler:
        eksempel_blokk = f"""
PATRICKS EGNE GODKJENTE POSTER (dette er hvordan han FAKTISK skriver — match
denne stemmen i rytme, ordvalg og tone. Ikke kopier innholdet, men la stilen smitte):
{eksempler}
"""

    innhold = f"""SKRIVESTIL (følg denne nøye — dette er Patricks stemme):
{config.linkedin_stil}
{eksempel_blokk}
SPRÅKMODUS: {config.linkedin_sprak}

VINKLING FOR DENNE POSTEN:
{vinkling or "Velg selv det mest interessante fra råmaterialet under."}

RÅMATERIALE:
{kontekst}

Skriv LinkedIn-posten nå."""

    print("  LinkedIn-agent kjører...")

    respons = client.messages.create(
        model=config.linkedin_modell,
        max_tokens=config.linkedin_max_tokens,
        thinking={"type": "adaptive"},
        system=config.linkedin_prompt,
        messages=[{"role": "user", "content": innhold}],
        output_config={"format": {"type": "json_schema", "schema": POST_SKJEMA}},
    )

    # Gi tydelige feil i stedet for en kryptisk StopIteration / JSON-feil når
    # svaret ikke er en komplett post.
    if respons.stop_reason == "max_tokens":
        raise RuntimeError(
            "Svaret ble avkuttet før posten var ferdig (traff max_tokens). "
            "Øk linkedin_max_tokens i config.py.")
    if respons.stop_reason == "refusal":
        raise RuntimeError("Modellen avslo forespørselen. Prøv en annen vinkling.")

    tekst = next((b.text for b in respons.content if b.type == "text"), None)
    if tekst is None:
        raise RuntimeError("Fikk ingen tekst tilbake fra modellen.")
    resultat = json.loads(tekst)
    print(f"  Ferdig — \"{resultat['arbeidstittel']}\"")
    return resultat

# --- Sette sammen den synlige posten ---

SKILLE = "\n\n— — — — — — — — — —\n🇬🇧 English version below\n— — — — — — — — — —\n\n"


def render_post(resultat: dict, sprak: str) -> str:
    no = resultat.get("post_norsk", "").strip()
    en = resultat.get("post_engelsk", "").strip()
    tags = " ".join(resultat.get("hashtags", []))

    if sprak == "norsk":
        kropp = no
    elif sprak == "engelsk":
        kropp = en
    else:  # begge
        kropp = no + SKILLE + en if (no and en) else (no or en)

    return f"{kropp}\n\n{tags}".strip()

# --- Lagring ---

def lagre_post(vinkling: str, resultat: dict, config: AgentConfig = None,
               ts: str = None) -> str:
    if config is None:
        config = STANDARD_CONFIG
    os.makedirs("linkedin", exist_ok=True)
    now = datetime.now()
    if ts is None:
        ts = now.strftime("%Y-%m-%d_%H-%M")
    tittel = resultat.get("arbeidstittel", "post")[:40].replace(" ", "_")
    base = f"linkedin/{ts}_{tittel}"

    post_tekst = render_post(resultat, config.linkedin_sprak)

    with open(f"{base}.md", "w", encoding="utf-8") as f:
        f.write("## Ferdig post (kopier teksten under)\n\n")
        f.write(post_tekst + "\n\n")
        f.write("---\n\n## 🎨 Bilde-prompter (lim inn i Midjourney/DALL-E/Gemini)\n\n")
        for b in resultat.get("bilde_prompter", []):
            f.write(f"**{b['plassering']}:**\n> {b['prompt']}\n\n")
        f.write("## 📸 Skjermbilder fra prosjektet ditt\n\n")
        for s in resultat.get("skjermbilde_forslag", []):
            f.write(f"- {s}\n")
        f.write(f"\n*Vinkling: {vinkling or '(agenten valgte selv)'}*\n")
        f.write(f"*Generert: {now.strftime('%d.%m.%Y %H:%M')}*\n")

    with open(f"{base}.json", "w", encoding="utf-8") as f:
        json.dump({"vinkling": vinkling, "timestamp": now.isoformat(),
                   **resultat}, f, ensure_ascii=False, indent=2)

    print("\nLagret:")
    print(f"  Post:  {base}.md")
    print(f"  Data:  {base}.json")
    return f"{base}.md"

# --- Kjør direkte ---

if __name__ == "__main__":
    # Windows-konsollen er cp1252 og kveles av emoji. Tving UTF-8 ut.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    vinkling = " ".join(sys.argv[1:]).strip()
    if not vinkling:
        vinkling = input("Hva skal posten handle om? (Enter = la agenten velge) ").strip()

    resultat = kjor_linkedin(vinkling)
    lagre_post(vinkling, resultat)

    print("\n" + "=" * 50)
    print(render_post(resultat, STANDARD_CONFIG.linkedin_sprak))
    print("=" * 50)
