"""
Agent-team orkestrator
----------------------
Kjeder tre spesialiserte agenter:
  1. Forskningsagent  — samler informasjon fra nettet
  2. Analyseagent     — identifiserer mønstre og kunnskapshull
  3. Planleggingsagent — lager konkret handlingsplan

Kjør: python run.py
"""

import json
import os
import time
from datetime import datetime

from research_agent import kjor_research
from analyse_agent import kjor_analyse
from planlegging_agent import kjor_planlegging
from pdf_generator import generer_pdf
from config import AgentConfig, STANDARD_CONFIG, KjoringStoppet

HISTORIKK_FIL = "historikk.json"


def last_historikk() -> list:
    if not os.path.exists(HISTORIKK_FIL):
        return []
    with open(HISTORIKK_FIL, encoding="utf-8") as f:
        return json.load(f)


def lagre_i_historikk(tema: str, filer: dict):
    historikk = last_historikk()
    historikk.append({
        "dato": datetime.now().isoformat(),
        "tema": tema,
        "filer": filer,
    })
    with open(HISTORIKK_FIL, "w", encoding="utf-8") as f:
        json.dump(historikk, f, ensure_ascii=False, indent=2)


def vis_historikk(historikk: list) -> list:
    siste = historikk[-8:]  # Vis maks 8 siste
    if not siste:
        return siste
    print("\nTidligere undersøkelser:")
    for i, h in enumerate(siste, 1):
        dato = h["dato"][:10]
        print(f"  [{i}] {h['tema']}  ({dato})")
    print()
    return siste


def velg_tema(siste: list) -> str:
    raw = input("Hva skal jeg undersøke for deg? ").strip()
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(siste):
            tema = siste[idx]["tema"]
            print(f"Gjentar: {tema}")
            return tema
    return raw


def lagre_alt(tema: str, research: dict, analyse: dict = None,
              plan: str = None, ts: str = None) -> dict:
    os.makedirs("rapporter", exist_ok=True)
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    base = f"rapporter/{ts}_{tema[:40].replace(' ', '_')}"

    filer = {
        "research_md": research.get("md_fil", f"{base}.md"),
        "research_json": research.get("json_fil", f"{base}.json"),
    }

    if analyse:
        with open(f"{base}_analyse.json", "w", encoding="utf-8") as f:
            json.dump(analyse, f, ensure_ascii=False, indent=2)
        filer["analyse_json"] = f"{base}_analyse.json"

    if plan:
        with open(f"{base}_plan.md", "w", encoding="utf-8") as f:
            f.write(f"# Handlingsplan: {tema}\n\n")
            f.write(f"*Generert: {datetime.now().strftime('%d.%m.%Y %H:%M')}*\n\n")
            f.write("---\n\n")
            f.write(f"**Grunnlagsstyrke:** {analyse.get('grunnlag_styrke', 'ukjent')}\n\n")
            f.write(f"**Analytisk vurdering:** {analyse.get('sammendrag', '')}\n\n")
            f.write("---\n\n")
            f.write(plan)
        filer["plan_md"] = f"{base}_plan.md"

    pdf_path = f"{base}_rapport.pdf"
    generer_pdf(tema, research, analyse, plan, pdf_path)
    filer["pdf"] = pdf_path

    print(f"\nLagret:")
    print(f"  PDF:       {pdf_path}")
    print(f"  Research:  {base}.md / .json")
    if analyse:
        print(f"  Analyse:   {base}_analyse.json")
    if plan:
        print(f"  Plan:      {base}_plan.md")

    return filer


def kjor_pipeline(tema: str, config: AgentConfig = None, ts: str = None,
                  hendelse=None, stopp=None) -> dict:
    """Kjeder hele agent-pipelinen (research → analyse → plan → lagring) og
    returnerer alt som trengs for visning. Brukes både av CLI og av
    bakgrunnstråden i app.py.

    `hendelse`: valgfri callback for live-oppdateringer (None = stille).
    `stopp`: valgfri threading.Event; sjekkes mellom agentene. Reiser
    `KjoringStoppet` (fra agentene) hvis satt — fanges av kalleren.
    Avskrudde trinn (`config.kjor_analyse`/`kjor_plan`) hoppes over.
    """
    if config is None:
        config = STANDARD_CONFIG
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")

    research = kjor_research(tema, ts, config, hendelse=hendelse, stopp=stopp)

    analyse = None
    if config.kjor_analyse:
        analyse = kjor_analyse(research, config, hendelse=hendelse, stopp=stopp)

    plan = None
    if config.kjor_plan:
        plan = kjor_planlegging(research, analyse, config, hendelse=hendelse, stopp=stopp)

    if hendelse is not None:
        hendelse({"t": "status", "tekst": "Lagrer rapport og PDF…"})
    filer = lagre_alt(tema, research, analyse, plan, ts)
    lagre_i_historikk(tema, filer)

    return {
        "tema": tema,
        "research": research,
        "analyse": analyse,
        "plan": plan,
        "filer": filer,
    }


def kjor_demo(tema: str, config: AgentConfig = None, ts: str = None,
              hendelse=None, stopp=None) -> dict:
    """Demo-kjøring: viser HELE live-grensesnittet (status, søk, henting, notater,
    tokenforbruk, kostnadsestimat og Stopp) UTEN å gjøre ekte API-kall eller søk.
    Trygt og gratis — hendelsene er oppdiktet og pauser simulerer arbeid.

    Samme grensesnitt som `kjor_pipeline` (hendelse/stopp), så app.py kan kjøre
    den i akkurat samme bakgrunnstråd. Lagrer ingen filer.
    """
    if config is None:
        config = STANDARD_CONFIG
    tema = tema or "Demoemne"

    def vent(sekunder: float):
        """Avbrytbar pause — sjekker stopp-signalet ~10 ganger i sekundet."""
        for _ in range(max(1, int(sekunder / 0.1))):
            if stopp is not None and stopp.is_set():
                raise KjoringStoppet()
            time.sleep(0.1)

    def meld(ev: dict):
        if hendelse is not None:
            hendelse(ev)

    # --- Forskningsagent (simulert) ---
    meld({"t": "status", "tekst": "Forskningsagent kjører… (DEMO)"})
    vent(0.6)

    søk = [f"{tema} oversikt", f"{tema} statistikk 2026",
           f"{tema} fordeler og ulemper", f"{tema} hva ekspertene mener",
           f"{tema} utvikling fremover"]
    antall_notater = 0
    for i, spørring in enumerate(søk, 1):
        meld({"t": "verktoy", "navn": "web_search", "detalj": spørring})
        meld({"t": "forbruk", "modell": config.research_modell,
              "input": 0, "output": 240, "cache_read": 9000, "cache_write": 1200})
        vent(0.7)
        meld({"t": "verktoy", "navn": "web_fetch",
              "detalj": f"https://eksempel.no/artikkel-{i}"})
        vent(0.5)
        antall_notater += 1
        meld({"t": "notat", "antall": antall_notater})

    meld({"t": "status", "tekst": f"Forskningsagent ferdig — {antall_notater} notater (DEMO)"})
    vent(0.4)

    rapport = f"""## Sammendrag
Dette er en **DEMO-rapport** om «{tema}». Ingen ekte søk ble gjort — teksten er
generert lokalt for å vise hvordan grensesnittet ser ut under en kjøring.

## Hovedfunn
- Demopunkt 1 om {tema}
- Demopunkt 2 om {tema}
- Demopunkt 3 om {tema}

## Konklusjon
Demo fullført. I en ekte kjøring ville denne rapporten vært bygget fra nettsøk og kilder.

## Kilder
- [1] https://eksempel.no/artikkel-1
- [2] https://eksempel.no/artikkel-2"""

    research = {
        "tema": tema,
        "rapport": rapport,
        "notater": [{"notat": f"Demonotat {i}", "kilde": f"https://eksempel.no/artikkel-{i}"}
                    for i in range(1, antall_notater + 1)],
        "md_fil": "",
        "json_fil": "",
    }

    # --- Analyseagent (simulert) ---
    analyse = None
    if config.kjor_analyse:
        meld({"t": "status", "tekst": "Analyseagent kjører… (DEMO)"})
        vent(0.9)
        meld({"t": "forbruk", "modell": config.analyse_modell,
              "input": 3200, "output": 700, "cache_read": 0, "cache_write": 0})
        analyse = {
            "mønstre": ["Demomønster A", "Demomønster B"],
            "nøkkelfakta": ["Demofaktum 1", "Demofaktum 2", "Demofaktum 3"],
            "usikkerhet": ["Demo: én kilde var utdatert"],
            "kunnskapshull": ["Demo: mangler oppdaterte tall for 2026"],
            "grunnlag_styrke": "middels",
            "sammendrag": "Dette er en simulert analyse for demo-formål.",
        }
        meld({"t": "status", "tekst": "Analyseagent ferdig — grunnlag: middels (DEMO)"})
        vent(0.3)

    # --- Planleggingsagent (simulert) ---
    plan = None
    if config.kjor_plan:
        meld({"t": "status", "tekst": "Planleggingsagent kjører… (DEMO)"})
        vent(0.9)
        meld({"t": "forbruk", "modell": config.plan_modell,
              "input": 2600, "output": 900, "cache_read": 0, "cache_write": 0})
        plan = """## Handlingsplan (DEMO)

1. **Steg 1 (høy prioritet)** — eksempeltiltak forankret i funnene. *Tidsestimat: 1 uke.*
2. **Steg 2 (middels)** — eksempeltiltak som adresserer en risiko. *Tidsestimat: 2 uker.*
3. **Steg 3 (lav)** — videre undersøkelse for å fylle kunnskapshullet. *Tidsestimat: 1 måned.*"""
        meld({"t": "status", "tekst": "Planleggingsagent ferdig (DEMO)"})
        vent(0.3)

    meld({"t": "status", "tekst": "Demo ferdig — ingen filer ble lagret"})
    return {
        "tema": tema,
        "research": research,
        "analyse": analyse,
        "plan": plan,
        "filer": {},  # ingen PDF/filer i demo
    }


if __name__ == "__main__":
    historikk = last_historikk()
    siste = vis_historikk(historikk)

    tema = velg_tema(siste)
    if not tema:
        print("Ingen tema angitt.")
    else:
        start = time.time()
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")

        kjor_pipeline(tema, ts=ts)

        elapsed = time.time() - start
        minutter, sekunder = divmod(int(elapsed), 60)
        print(f"\nFerdig på {minutter}m {sekunder}s")
