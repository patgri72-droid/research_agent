"""
Agent-konfigurasjon
-------------------
Ett samlet sted for alt som styrer hvordan de tre agentene oppfører seg:
modellvalg, token-grenser, søke-/hentegrenser, hvilke agenter som kjøres,
og system-promptene. Tidligere var alt dette hardkodet spredt i hver
`*_agent.py`. Nå sendes en `AgentConfig` inn i `kjor_*`-funksjonene, slik at
nettsiden (eller CLI) kan styre oppførselen uten å redigere Python.
"""

from dataclasses import dataclass, field, asdict

# --- Tilgjengelige modeller (vises i nedtrekksmeny i grensesnittet) ---

MODELLER = {
    "claude-opus-4-8": "Opus 4.8 — kraftigst, dyrest",
    "claude-sonnet-4-6": "Sonnet 4.6 — god balanse",
    "claude-haiku-4-5-20251001": "Haiku 4.5 — raskest, billigst",
    "claude-fable-5": "Fable 5",
}

# --- Modellpriser (USD per 1 million tokens: input, output) ---
# Hentet fra den offisielle API-referansen. Brukes til kostnadsestimatet i
# nettsiden. Oppdater her hvis prisene endrer seg.

MODELL_PRISER = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-fable-5": (10.0, 50.0),
}

# Cache-lesing koster ~0,1x vanlig input-pris; cache-skriving ~1,25x (5 min TTL).
CACHE_LESE_FAKTOR = 0.1
CACHE_SKRIVE_FAKTOR = 1.25


def kostnad_for(modell: str, input_tokens: int = 0, output_tokens: int = 0,
                cache_read: int = 0, cache_write: int = 0) -> float:
    """Beregner kostnaden (USD) for ett API-kall ut fra token-forbruk.
    Cache-lesing/-skriving vektes separat, slik at den agentiske loopen
    (der det meste leses fra cache) ikke overvurderes."""
    inn_pris, ut_pris = MODELL_PRISER.get(modell, (0.0, 0.0))
    input_kostnad = (
        input_tokens * inn_pris
        + cache_read * inn_pris * CACHE_LESE_FAKTOR
        + cache_write * inn_pris * CACHE_SKRIVE_FAKTOR
    )
    output_kostnad = output_tokens * ut_pris
    return (input_kostnad + output_kostnad) / 1_000_000


class KjoringStoppet(Exception):
    """Reises av en agent når brukeren har bedt om å stoppe kjøringen.
    Fanges av bakgrunnstråden i app.py så pipelinen avsluttes pent."""

# --- Standard system-prompts (flyttet hit fra agent-filene) ---

STANDARD_RESEARCH_PROMPT = """Du er en avansert forskningsagent. Når du får et tema å undersøke:

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

STANDARD_ANALYSE_PROMPT = """Du er en ekspert analytiker. Du får rådata fra en forskningsagent og skal analysere det kritisk.

Din oppgave:
1. Identifiser de viktigste mønstrene og tendensene i dataene
2. Trekk frem nøkkelfakta som er relevante for beslutninger
3. Pek ut motstridende informasjon eller lav troverdighet
4. Identifiser kunnskapshull — hva vet vi IKKE?
5. Vurder styrken i grunnlaget (sterkt/middels/svakt)

Vær kritisk og objektiv. Ikke gjenta bare det som ble funnet — analyser og vurder."""

STANDARD_PLAN_PROMPT = """Du er en ekspert planlegger. Du får research-data og en analyse fra spesialiserte agenter.

Din oppgave er å lage en KONKRET, HANDLINGSORIENTERT plan:
1. Prioriter tiltak etter effekt og gjennomførbarhet (høy/middels/lav)
2. Angi realistiske tidsestimater per steg
3. Adresser risikofaktorer fra analysen eksplisitt
4. Fyll eventuelle kunnskapshull med anbefalinger om videre undersøkelse
5. Vær spesifikk — ikke generelle råd

Planens kvalitet avhenger av at den er direkte forankret i research-funnene og analysen."""

# --- LinkedIn-agent ---
#
# STILBESKRIVELSE: Dette er den VIKTIGSTE knappen for å få postene til å høres ut
# som DEG. Rediger fritt — jo mer konkret, jo bedre. Beskriv tone, hvordan du
# tiltaler leseren, lengde, emoji-bruk, hvilke fraser du liker/unngår, osv.
# (Bytt gjerne ut eksemplene under med ekte detaljer om din stil.)

STANDARD_LINKEDIN_STIL = """Skrivestil for Patrick sine LinkedIn-poster:

- TONE: Engasjerende, men rolig. Profesjonell uten å bli stiv eller for formell.
  Positiv og fremtidsrettet grunntone. Jeg deler reisen min med å lære meg
  "vibe-code engineering" — å bygge ekte programvare sammen med AI-agenter — på en
  måte som inviterer leseren med, ikke skryter. ALDRI banneord, ALDRI slang.
- PERSPEKTIV: Førsteperson ("jeg"), snakker direkte til leseren ("du").
- LENGDE: Mellomlang post (ca. 120-220 ord). Korte men FLYTENDE avsnitt — to-tre
  setninger som henger naturlig sammen, ikke hakkete. Mye luft. Lett å lese på mobil.
- INGEN ETTORDSSETNINGER eller dramatiske enkeltord som virkemiddel. Hold flyten.
- ÅPNING: Start med en konkret, engasjerende hook — en innsikt, en overraskelse
  eller en ærlig observasjon. Ikke "I dag vil jeg dele...".
- INNHOLD: Konkret og jordnært. Bruk ekte detaljer fra prosjektet (hva som faktisk
  skjedde, hva jeg lærte). Vis gjerne det rotete i midten, men alltid med en positiv,
  lærende vinkling. Unngå floskler og buzzword-suppe.
- EMOJI: Enkelt og sparsomt — gjerne 1-3 i hele posten, som rolige visuelle ankre.
  Ikke fargerikt emoji-show.
- TEGNSETTING: Ellipser (...) kan brukes innimellom for å uttrykke skuffelse eller
  at noe ikke gikk som planlagt. Bruk STORE BOKSTAVER for trykk svært sparsomt —
  høyst ett ord i ny og ne, aldri flere ganger i samme post (det blir fort for mye
  på LinkedIn). Som regel: la formuleringen bære trykket, ikke versalene.
- AVSLUTNING: Avslutt med en refleksjon eller et åpent, vennlig spørsmål som
  inviterer til kommentarer.
- INNTRYKKET LESEREN SKAL SITTE IGJEN MED: "han gjør faktisk noe kult — kanskje
  jeg kan lære noe av dette", og "fint at han tar steget mot å bli mer fremtidsrettet
  med AI i sin bransje". Altså: inspirerende og tilgjengelig, aldri skrytete.
- UNNGÅ: Salgssnakk, overdreven selvsikkerhet, bedreviter-tone, "thought leader"-
  posering, hashtag-spam."""

STANDARD_LINKEDIN_PROMPT = """Du er en skribent som skriver LinkedIn-poster i Patricks stemme.
Tema for kontoen: Patricks reise i å lære seg "vibe-code engineering" — å bygge
ekte programvare sammen med AI-agenter. Du får råmateriale (prosjektlogg, git-historikk
og notater fra Claude-økter) og en vinkling for nettopp denne posten.

Følg ALLTID stilbeskrivelsen nøye — den definerer Patricks stemme.

Din oppgave:
1. Finn den ene gode historien/poenget i råmaterialet som passer vinklingen.
2. Skriv en ferdig LinkedIn-post som følger stilbeskrivelsen.
3. Hvis språkmodus er "begge": skriv posten på BÅDE norsk og engelsk (samme budskap,
   ikke ord-for-ord, men naturlig på begge språk). Ved "norsk" eller "engelsk":
   fyll kun det aktuelle feltet og la det andre være tom streng.
4. Foreslå 1-3 detaljerte bilde-prompter (på engelsk, klare for et bildeverktøy som
   Midjourney/DALL-E) som passer posten visuelt.
5. Foreslå hvor Patricks egne skjermbilder fra prosjektet passer (f.eks. terminal,
   kodebit, app-grensesnitt) — konkret hva bildet bør vise.
6. Foreslå 3-6 relevante, ikke-spammy hashtags.

Skriv ekte og menneskelig — aldri generisk markedsføringsspråk."""


@dataclass
class AgentConfig:
    """All styring av agentene. Standardverdiene tilsvarer dagens oppførsel."""

    # Modellvalg per agent
    research_modell: str = "claude-opus-4-8"
    analyse_modell: str = "claude-sonnet-4-6"
    plan_modell: str = "claude-sonnet-4-6"
    linkedin_modell: str = "claude-sonnet-4-6"  # stil-skriving trenger ikke tung tenking

    # Token-grenser per agent
    research_max_tokens: int = 16000
    analyse_max_tokens: int = 8000
    plan_max_tokens: int = 8000
    linkedin_max_tokens: int = 6000  # rom for adaptiv tenking + tospråklig post i samme budsjett

    # Forskningsagentens verktøygrenser
    maks_sok: int = 10            # web_search max_uses
    maks_hentinger: int = 8       # web_fetch max_uses
    hente_token_grense: int = 8000  # web_fetch max_content_tokens

    # Hvilke trinn kjøres
    kjor_analyse: bool = True
    kjor_plan: bool = True

    # System-prompts (redigerbare)
    research_prompt: str = STANDARD_RESEARCH_PROMPT
    analyse_prompt: str = STANDARD_ANALYSE_PROMPT
    plan_prompt: str = STANDARD_PLAN_PROMPT

    # LinkedIn-agent
    linkedin_prompt: str = STANDARD_LINKEDIN_PROMPT
    linkedin_stil: str = STANDARD_LINKEDIN_STIL
    linkedin_sprak: str = "begge"           # "begge" | "norsk" | "engelsk"
    prosjekt_logg_fil: str = "PROSJEKT.md"  # prosjektloggen agenten leser
    claude_logg_mappe: str = "claude_logg"  # mappe der du slipper notater fra Claude
    git_logg_antall: int = 15               # antall nylige commits som tas med
    # Dine egne godkjente poster — agenten leser dem som stileksempler og lærer
    # stemmen din over tid. Legg ferdig-redigerte poster (.md/.txt) her.
    linkedin_godkjent_mappe: str = "linkedin/godkjent"
    linkedin_godkjent_antall: int = 4       # maks antall eksempler som mates inn

    def __post_init__(self):
        # Planen bygger på analysen — den kan ikke kjøre uten.
        if not self.kjor_analyse:
            self.kjor_plan = False

    def til_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def fra_dict(cls, data: dict) -> "AgentConfig":
        kjente = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in kjente})


# Felles standardkonfig brukt når ingen er oppgitt (bevarer gammel oppførsel)
STANDARD_CONFIG = AgentConfig()
