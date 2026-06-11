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

st.set_page_config(
    page_title="Research Agent",
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
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("## Research Agent")
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
    "",
    placeholder="Hva vil du forske på?",
    key="tema_input",
    label_visibility="collapsed",
)

start_knapp = st.button("Start forskning", type="primary", disabled=not tema.strip())

if start_knapp and tema.strip():
    start = time.time()
    ts = time.strftime("%Y-%m-%d_%H-%M")

    with st.status("Kjører agenter...", expanded=True) as status:
        st.write("Forskningsagent kjører...")
        research = kjor_research(tema, ts)
        st.write(f"Forskningsagent ferdig — {len(research['notater'])} notater")

        st.write("Analyseagent kjører...")
        analyse = kjor_analyse(research)
        st.write(f"Analyseagent ferdig — grunnlagsstyrke: {analyse['grunnlag_styrke']}")

        st.write("Planleggingsagent kjører...")
        plan = kjor_planlegging(research, analyse)
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
    analyse = r["analyse"]

    st.divider()
    st.subheader(r["tema"])

    styrke = analyse.get("grunnlag_styrke", "ukjent")
    farge = {"sterkt": "green", "middels": "orange", "svakt": "red"}.get(styrke, "gray")
    st.markdown(f"Grunnlagsstyrke: :{farge}[**{styrke.upper()}**]")

    tab1, tab2, tab3 = st.tabs(["Rapport", "Analyse", "Handlingsplan"])

    with tab1:
        st.markdown(r["research"]["rapport"])

    with tab2:
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

    with tab3:
        st.markdown(r["plan"])

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
