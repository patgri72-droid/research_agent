import os
import queue
import sys
import threading
import time

import streamlit as st

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json

from run import kjor_pipeline, kjor_demo, last_historikk
from config import AgentConfig, MODELLER, KjoringStoppet, kostnad_for


def last_lagret_resultat(entry: dict) -> dict | None:
    """Leser en tidligere lagret rapport fra disk — ingen API-kall."""
    filer = entry.get("filer", {})
    try:
        with open(filer["research_json"], encoding="utf-8") as f:
            research = json.load(f)
        with open(filer["analyse_json"], encoding="utf-8") as f:
            analyse = json.load(f)
        with open(filer["plan_md"], encoding="utf-8") as f:
            plan_md = f.read()
        # Plan-filen har en header-wrapper; rå plan ligger etter andre "---"
        plan = plan_md.split("---\n\n", 2)[-1]
    except (KeyError, FileNotFoundError):
        return None

    return {
        "tema": entry.get("tema", research.get("tema", "")),
        "research": research,
        "analyse": analyse,
        "plan": plan,
        "filer": filer,
    }


def velg_modell(label: str, standard: str, key: str) -> str:
    """Nedtrekksmeny over tilgjengelige modeller."""
    nokler = list(MODELLER.keys())
    return st.selectbox(
        label,
        nokler,
        index=nokler.index(standard) if standard in nokler else 0,
        format_func=lambda k: MODELLER[k],
        key=key,
    )


def bygg_config_panel() -> AgentConfig:
    """Tegner innstillingspanelet og bygger en AgentConfig fra valgene."""
    std = AgentConfig()  # standardverdier som utgangspunkt

    st.markdown("**Hvilke trinn kjøres**")
    kjor_analyse_på = st.checkbox("Analyseagent", value=std.kjor_analyse)
    kjor_plan_på = st.checkbox(
        "Planleggingsagent", value=std.kjor_plan,
        disabled=not kjor_analyse_på,
        help="Krever at analyseagenten er på — planen bygger på analysen.",
    )

    with st.expander("Modeller"):
        research_modell = velg_modell("Forskningsagent", std.research_modell, "m_research")
        analyse_modell = velg_modell("Analyseagent", std.analyse_modell, "m_analyse")
        plan_modell = velg_modell("Planleggingsagent", std.plan_modell, "m_plan")

    with st.expander("Søk og henting"):
        maks_sok = st.slider("Maks nettsøk", 1, 20, std.maks_sok)
        maks_hentinger = st.slider("Maks artikkelhentinger", 1, 20, std.maks_hentinger)
        hente_token_grense = st.slider(
            "Tokens per henting", 2000, 20000, std.hente_token_grense, step=1000)

    with st.expander("Token-grenser (svar)"):
        research_max_tokens = st.slider(
            "Forskningsagent", 4000, 32000, std.research_max_tokens, step=1000)
        analyse_max_tokens = st.slider(
            "Analyseagent", 2000, 16000, std.analyse_max_tokens, step=1000)
        plan_max_tokens = st.slider(
            "Planleggingsagent", 2000, 16000, std.plan_max_tokens, step=1000)

    with st.expander("System-prompts"):
        st.caption("Endrer hvordan hver agent tenker. Tøm feltet for å bruke standard.")
        research_prompt = st.text_area(
            "Forskningsagent", value=std.research_prompt, height=160)
        analyse_prompt = st.text_area(
            "Analyseagent", value=std.analyse_prompt, height=120)
        plan_prompt = st.text_area(
            "Planleggingsagent", value=std.plan_prompt, height=120)

    return AgentConfig(
        research_modell=research_modell,
        analyse_modell=analyse_modell,
        plan_modell=plan_modell,
        research_max_tokens=research_max_tokens,
        analyse_max_tokens=analyse_max_tokens,
        plan_max_tokens=plan_max_tokens,
        maks_sok=maks_sok,
        maks_hentinger=maks_hentinger,
        hente_token_grense=hente_token_grense,
        kjor_analyse=kjor_analyse_på,
        kjor_plan=kjor_plan_på,
        research_prompt=research_prompt.strip() or std.research_prompt,
        analyse_prompt=analyse_prompt.strip() or std.analyse_prompt,
        plan_prompt=plan_prompt.strip() or std.plan_prompt,
    )


st.set_page_config(
    page_title="Agent-hub",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f0f1a; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    [data-testid="stSidebar"] .stButton button {
        background-color: #1a1a2e;
        color: #e0e0e0 !important;
        border: 1px solid #2a2a4a;
        text-align: left;
        font-size: 0.8rem;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #2a2a4a;
        border-color: #4a4a8a;
    }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; }
    .stDownloadButton button {
        background-color: #14145a;
        color: white;
    }
    /* Agent-bobler på hjemmesiden */
    .agent-boble {
        text-align: center;
        padding: 0.5rem 0.5rem 0.2rem;
    }
    .agent-boble .ikon { font-size: 3rem; line-height: 1; }
    .agent-boble .navn { font-size: 1.25rem; font-weight: 700; margin-top: 0.4rem; }
    .agent-boble .beskr { color: #9aa0b4; font-size: 0.85rem; min-height: 2.4rem; }
</style>
""", unsafe_allow_html=True)


# =====================================================================
#  Navigasjon mellom hjemmeside og enkeltagenter
# =====================================================================

def gaa_til(agent_id):
    """Bytt aktiv side og tegn på nytt."""
    st.session_state["aktiv_agent"] = agent_id
    st.rerun()


# =====================================================================
#  Fase 2: ikke-blokkerende kjøring med live-aktivitet og Stopp
# =====================================================================
#
# Agentene kjøres i en bakgrunnstråd. De sender hendelser på en kø
# (de rører aldri `st.*` direkte). Et `st.fragment(run_every=1s)` tømmer
# køen og tegner fremdrift hvert sekund, mens «Stopp» ligger utenfor
# fragmentet og alltid er klikkbar.

def start_kjoring(tema: str, config: AgentConfig, kjorefunksjon=kjor_pipeline,
                  demo: bool = False):
    """Spinner opp pipelinen i en bakgrunnstråd og lagrer kø/tråd/stopp
    i session_state. Tråden rører kun køen og stopp-signalet — aldri st.*.

    `kjorefunksjon` er som standard `kjor_pipeline` (ekte kjøring), men kan være
    `kjor_demo` for å vise grensesnittet uten API-kall."""
    ko = queue.Queue()
    stopp = threading.Event()
    ts = time.strftime("%Y-%m-%d_%H-%M")

    def hendelse(ev):
        ko.put(ev)

    def arbeid():
        try:
            res = kjorefunksjon(tema, config, ts, hendelse=hendelse, stopp=stopp)
            ko.put({"t": "ferdig", "resultat": res})
        except KjoringStoppet:
            ko.put({"t": "stoppet"})
        except Exception as e:  # noqa: BLE001 — tråden må aldri dø stille
            ko.put({"t": "feil", "melding": str(e)})

    traad = threading.Thread(target=arbeid, daemon=True)
    traad.start()

    st.session_state["kjoring"] = {
        "kø": ko, "traad": traad, "stopp": stopp, "tema": tema, "demo": demo,
        "start": time.time(), "status": "Starter…",
        "notater": 0, "logg": [], "forbruk": [],
        "ferdig": False, "stoppet": False, "feil": None, "resultat": None,
    }


def _tøm_kø(kj: dict):
    """Flytter alle ventende hendelser fra køen inn i akkumulatorene."""
    ko = kj["kø"]
    while True:
        try:
            ev = ko.get_nowait()
        except queue.Empty:
            break
        t = ev.get("t")
        if t == "status":
            kj["status"] = ev["tekst"]
            kj["logg"].append(f"• {ev['tekst']}")
        elif t == "verktoy":
            ikon = "🔎 Søk:  " if ev["navn"] == "web_search" else "📄 Henter:"
            kj["logg"].append(f"{ikon} {ev.get('detalj', '')[:90]}")
        elif t == "notat":
            kj["notater"] = ev["antall"]
        elif t == "forbruk":
            kj["forbruk"].append(ev)
        elif t == "ferdig":
            kj["resultat"] = ev["resultat"]
            kj["ferdig"] = True
        elif t == "stoppet":
            kj["stoppet"] = True
        elif t == "feil":
            kj["feil"] = ev["melding"]


def _forbruk_sum(forbruk: list) -> tuple[float, int]:
    """Returnerer (total kostnad i USD, totalt antall tokens) for kjøringen."""
    kostnad = sum(
        kostnad_for(f["modell"], f["input"], f["output"], f["cache_read"], f["cache_write"])
        for f in forbruk
    )
    tokens = sum(f["input"] + f["cache_read"] + f["cache_write"] + f["output"]
                 for f in forbruk)
    return kostnad, tokens


def vis_live_kjoring(kj: dict):
    """Tegner live-fremdrift mens en kjøring pågår."""
    st.subheader(f"🔬 {kj['tema']}")

    if kj.get("demo"):
        st.info("▶ DEMO-modus — ingen ekte søk eller API-kall. Tallene er oppdiktet.")

    # Stopp UTENFOR fragmentet — full app-rerun, alltid klikkbar
    if st.button("⏹ Stopp kjøringen", type="secondary"):
        kj["stopp"].set()
        kj["status"] = "Stopper… (fullfører pågående steg)"

    @st.fragment(run_every=1.0)
    def live():
        kj = st.session_state.get("kjoring")
        if kj is None:
            return
        _tøm_kø(kj)
        kostnad, tokens = _forbruk_sum(kj["forbruk"])

        # Avslutt og bytt vy når tråden er ferdig / stoppet / feilet
        if kj["ferdig"]:
            res = dict(kj["resultat"])
            res["_kostnad"] = kostnad
            res["_tokens"] = tokens
            st.session_state["resultater"] = res
            st.session_state["kjoring"] = None
            st.rerun(scope="app")
        if kj["stoppet"]:
            st.session_state["kjoring"] = None
            st.session_state["kjor_melding"] = (
                "warning", "Kjøringen ble stoppet. Ingen rapport ble lagret.")
            st.rerun(scope="app")
        if kj["feil"]:
            st.session_state["kjoring"] = None
            st.session_state["kjor_melding"] = ("error", f"Feil under kjøring: {kj['feil']}")
            st.rerun(scope="app")

        forløpt = int(time.time() - kj["start"])
        m, s = divmod(forløpt, 60)

        st.markdown(f"**{kj['status']}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tid", f"{m}m {s:02d}s")
        c2.metric("Notater", kj["notater"])
        c3.metric("Tokens", f"{tokens:,}".replace(",", " "))
        c4.metric("Est. kostnad", f"${kostnad:.3f}")

        if kj["logg"]:
            st.caption("Aktivitet")
            st.code("\n".join(kj["logg"][-12:]), language=None)

    live()


def vis_resultater(r: dict):
    """Viser rapport/analyse/plan/PDF for en ferdig (eller lagret) kjøring."""
    analyse = r.get("analyse")
    plan = r.get("plan")

    st.divider()
    st.subheader(r["tema"])

    if "_kostnad" in r:
        st.caption(
            f"Estimert kostnad: ${r['_kostnad']:.3f}  ·  "
            f"{r.get('_tokens', 0):,}".replace(",", " ") + " tokens")

    if analyse:
        styrke = analyse.get("grunnlag_styrke", "ukjent")
        farge = {"sterkt": "green", "middels": "orange", "svakt": "red"}.get(styrke, "gray")
        st.markdown(f"Grunnlagsstyrke: :{farge}[**{styrke.upper()}**]")

    fane_navn = ["Rapport"]
    if analyse:
        fane_navn.append("Analyse")
    if plan:
        fane_navn.append("Handlingsplan")
    faner = st.tabs(fane_navn)
    fane = dict(zip(fane_navn, faner))

    with fane["Rapport"]:
        st.markdown(r["research"]["rapport"])

    if analyse:
        with fane["Analyse"]:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Mønstre og tendenser**")
                for m in analyse.get("mønstre", []):
                    st.markdown(f"- {m}")
                st.markdown("**Nøkkelfakta**")
                for f in analyse.get("nøkkelfakta", []):
                    st.markdown(f"- {f}")
            with col2:
                st.markdown("**Usikkerhet og risiko**")
                for u in analyse.get("usikkerhet", []):
                    st.markdown(f"- {u}")
                st.markdown("**Kunnskapshull**")
                for k in analyse.get("kunnskapshull", []):
                    st.markdown(f"- {k}")
            st.divider()
            st.markdown(f"_{analyse.get('sammendrag', '')}_")

    if plan:
        with fane["Handlingsplan"]:
            st.markdown(plan)

    pdf_path = r["filer"].get("pdf")
    if pdf_path and os.path.exists(pdf_path):
        st.divider()
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Last ned PDF-rapport", f,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
            )


# =====================================================================
#  Research-agentens grensesnitt (det vi bygde i fase 1)
# =====================================================================

def vis_research_agent():
    # --- Sidepanel ---
    with st.sidebar:
        if st.button("← Tilbake til hub", use_container_width=True):
            gaa_til(None)
        st.markdown("## Research Agent")
        st.markdown("---")

        st.markdown("### Innstillinger")
        config = bygg_config_panel()
        st.markdown("---")

        historikk = last_historikk()
        siste = historikk[-8:] if historikk else []

        if siste:
            st.markdown("**Tidligere søk**")
            st.caption("Klikk for å åpne uten å kjøre på nytt")
            for h in reversed(siste):
                dato = h["dato"][:10]
                label = h["tema"][:38] + ("..." if len(h["tema"]) > 38 else "")
                if st.button(f"{label}\n_{dato}_", key=h["dato"], use_container_width=True):
                    lagret = last_lagret_resultat(h)
                    if lagret:
                        st.session_state["resultater"] = lagret
                    else:
                        st.warning("Fant ikke de lagrede filene for dette søket.")
                    st.rerun()

    # --- Hovedinnhold ---
    st.title("Research Agent")
    st.caption("Skriv inn et tema for en dybdeundersøkelse med analyse og handlingsplan")

    # Pågår en kjøring? Vis live-fremdrift og stopp her — ikke input/resultat.
    kjoring = st.session_state.get("kjoring")
    if kjoring is not None:
        vis_live_kjoring(kjoring)
        return

    # Melding fra forrige kjøring (stoppet / feil)
    melding = st.session_state.pop("kjor_melding", None)
    if melding:
        nivaa, tekst = melding
        getattr(st, nivaa)(tekst)

    if "tema_input" not in st.session_state:
        st.session_state["tema_input"] = ""

    tema = st.text_input(
        "Tema",
        placeholder="Hva vil du forske på?",
        key="tema_input",
        label_visibility="collapsed",
    )

    c_start, c_demo = st.columns([2, 1])
    with c_start:
        if st.button("Start forskning", type="primary", disabled=not tema.strip(),
                     use_container_width=True) and tema.strip():
            start_kjoring(tema.strip(), config)
            st.rerun()
    with c_demo:
        if st.button("▶ Demo (uten søk)", use_container_width=True,
                     help="Viser hele live-grensesnittet uten ekte søk, API-kall eller kostnad."):
            start_kjoring(tema.strip() or "Demoemne: fornybar energi i Norge",
                          config, kjorefunksjon=kjor_demo, demo=True)
            st.rerun()

    # --- Vis resultater (ferdig kjøring eller lagret søk) ---
    if "resultater" in st.session_state:
        vis_resultater(st.session_state["resultater"])


# =====================================================================
#  Agent-register — legg til nye agenter her
# =====================================================================
#
# Hvert kort på hjemmesiden bygges fra denne lista. For å legge til en ny
# agent: skriv en vis_<navn>()-funksjon og legg til en rad her.
# "render": None betyr "ikke koblet til web ennå" (vises som kommer snart).

AGENTER = [
    {
        "id": "research",
        "navn": "Research-Agent",
        "ikon": "🔬",
        "beskrivelse": "Dybdeundersøkelse av et tema med kildebelagt rapport, kritisk analyse og handlingsplan.",
        "render": vis_research_agent,
    },
    {
        "id": "linkedin",
        "navn": "LinkedIn-Agent",
        "ikon": "✍️",
        "beskrivelse": "Skriver LinkedIn-poster i din stemme fra prosjektlogg, git og notater.",
        "render": None,  # finnes som CLI (linkedin_agent.py) — web-grensesnitt kommer
    },
]


def finn_agent(agent_id):
    return next((a for a in AGENTER if a["id"] == agent_id), None)


# =====================================================================
#  Hjemmeside — agent-bobler
# =====================================================================

def vis_hjem():
    with st.sidebar:
        st.markdown("## Agent-hub")
        st.caption("Velg en agent for å komme i gang.")

    st.title("Styringsgrensesnitt for AI-agenter")
    st.caption("Velg en agent å jobbe med. Flere kommer etter hvert.")
    st.write("")

    kolonner = st.columns(3)
    for i, agent in enumerate(AGENTER):
        with kolonner[i % 3]:
            with st.container(border=True):
                st.markdown(
                    f"<div class='agent-boble'>"
                    f"<div class='ikon'>{agent['ikon']}</div>"
                    f"<div class='navn'>{agent['navn']}</div>"
                    f"<div class='beskr'>{agent['beskrivelse']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                tilgjengelig = agent["render"] is not None
                if st.button(
                    "Åpne" if tilgjengelig else "Kommer snart",
                    key=f"aapne_{agent['id']}",
                    use_container_width=True,
                    type="primary" if tilgjengelig else "secondary",
                    disabled=not tilgjengelig,
                ):
                    gaa_til(agent["id"])


# =====================================================================
#  Ruter
# =====================================================================

if "aktiv_agent" not in st.session_state:
    st.session_state["aktiv_agent"] = None

aktiv = finn_agent(st.session_state["aktiv_agent"])
if aktiv and aktiv["render"]:
    aktiv["render"]()
else:
    vis_hjem()
