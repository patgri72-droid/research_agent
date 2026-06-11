import os
import sys
import time

import streamlit as st

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json

from research_agent import kjor_research
from analyse_agent import kjor_analyse
from planlegging_agent import kjor_planlegging
from run import lagre_alt, lagre_i_historikk, last_historikk
from config import AgentConfig, MODELLER


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

    if "tema_input" not in st.session_state:
        st.session_state["tema_input"] = ""

    tema = st.text_input(
        "Tema",
        placeholder="Hva vil du forske på?",
        key="tema_input",
        label_visibility="collapsed",
    )

    start_knapp = st.button("Start forskning", type="primary", disabled=not tema.strip())

    if start_knapp and tema.strip():
        start = time.time()
        ts = time.strftime("%Y-%m-%d_%H-%M")

        analyse = None
        plan = None

        with st.status("Kjører agenter...", expanded=True) as status:
            st.write("Forskningsagent kjører...")
            research = kjor_research(tema, ts, config)
            st.write(f"Forskningsagent ferdig — {len(research['notater'])} notater")

            if config.kjor_analyse:
                st.write("Analyseagent kjører...")
                analyse = kjor_analyse(research, config)
                st.write(f"Analyseagent ferdig — grunnlagsstyrke: {analyse['grunnlag_styrke']}")

            if config.kjor_plan:
                st.write("Planleggingsagent kjører...")
                plan = kjor_planlegging(research, analyse, config)
                st.write("Planleggingsagent ferdig")

            filer = lagre_alt(tema, research, analyse, plan, ts)
            lagre_i_historikk(tema, filer)

            elapsed = time.time() - start
            minutter, sekunder = divmod(int(elapsed), 60)
            status.update(label=f"Ferdig på {minutter}m {sekunder}s", state="complete")

        st.session_state["resultater"] = {
            "tema": tema,
            "research": research,
            "analyse": analyse,
            "plan": plan,
            "filer": filer,
        }
        st.rerun()

    # --- Vis resultater ---
    if "resultater" in st.session_state:
        r = st.session_state["resultater"]
        analyse = r.get("analyse")
        plan = r.get("plan")

        st.divider()
        st.subheader(r["tema"])

        if analyse:
            styrke = analyse.get("grunnlag_styrke", "ukjent")
            farge = {"sterkt": "green", "middels": "orange", "svakt": "red"}.get(styrke, "gray")
            st.markdown(f"Grunnlagsstyrke: :{farge}[**{styrke.upper()}**]")

        # Bygg bare fanene som har innhold
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
                    "Last ned PDF-rapport",
                    f,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                )


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
