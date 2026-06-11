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


if __name__ == "__main__":
    historikk = last_historikk()
    siste = vis_historikk(historikk)

    tema = velg_tema(siste)
    if not tema:
        print("Ingen tema angitt.")
    else:
        start = time.time()
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")

        research = kjor_research(tema, ts)
        analyse = kjor_analyse(research)
        plan = kjor_planlegging(research, analyse)
        filer = lagre_alt(tema, research, analyse, plan, ts)

        lagre_i_historikk(tema, filer)

        elapsed = time.time() - start
        minutter, sekunder = divmod(int(elapsed), 60)
        print(f"\nFerdig på {minutter}m {sekunder}s")
