import anthropic
import json

from config import AgentConfig, STANDARD_CONFIG, KjoringStoppet, hent_api_nokkel

client = anthropic.Anthropic(api_key=hent_api_nokkel())


def kjor_analyse(research_data: dict, config: AgentConfig = None,
                 hendelse=None, stopp=None) -> dict:
    if config is None:
        config = STANDARD_CONFIG
    if stopp is not None and stopp.is_set():
        raise KjoringStoppet()
    tema = research_data.get("tema", "")
    rapport = research_data.get("rapport", "")
    notat_liste = research_data.get("notater", [])

    notater_tekst = "\n".join(
        f"- {n['notat']} (kilde: {n['kilde']})" for n in notat_liste if n.get("notat")
    )

    innhold = f"""Tema: {tema}

=== RAPPORT FRA FORSKNINGSAGENTEN ===
{rapport}

=== NOTATER TATT UNDERVEIS ===
{notater_tekst or 'Ingen notater'}

Gjennomfør en grundig analyse av dette materialet."""

    if hendelse is not None:
        hendelse({"t": "status", "tekst": "Analyseagent kjører…"})
    else:
        print(f"  Analyseagent kjører...")

    respons = client.messages.create(
        model=config.analyse_modell,
        max_tokens=config.analyse_max_tokens,
        thinking={"type": "adaptive"},
        system=config.analyse_prompt,
        messages=[{"role": "user", "content": innhold}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "mønstre": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Identifiserte mønstre og tendenser"
                        },
                        "nøkkelfakta": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "De viktigste faktaene for beslutninger"
                        },
                        "usikkerhet": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Motstridende info, lav troverdighet eller tvetydighet"
                        },
                        "kunnskapshull": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Hva vi ikke vet og burde undersøke videre"
                        },
                        "grunnlag_styrke": {
                            "type": "string",
                            "enum": ["sterkt", "middels", "svakt"],
                            "description": "Hvor solid er det samlede kunnskapsgrunnlaget"
                        },
                        "sammendrag": {
                            "type": "string",
                            "description": "Kortfattet analytisk oppsummering (3-5 setninger)"
                        },
                    },
                    "required": ["mønstre", "nøkkelfakta", "usikkerhet", "kunnskapshull", "grunnlag_styrke", "sammendrag"],
                    "additionalProperties": False,
                },
            }
        },
    )

    tekst = next(b.text for b in respons.content if b.type == "text")
    analyse = json.loads(tekst)

    u = getattr(respons, "usage", None)
    if hendelse is not None and u is not None:
        hendelse({"t": "forbruk", "modell": config.analyse_modell,
                  "input": getattr(u, "input_tokens", 0) or 0,
                  "output": getattr(u, "output_tokens", 0) or 0,
                  "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
                  "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0})
        hendelse({"t": "status",
                  "tekst": f"Analyseagent ferdig — grunnlag: {analyse['grunnlag_styrke']}"})
    else:
        print(f"  Ferdig — grunnlagsstyrke: {analyse['grunnlag_styrke']}")

    return analyse


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Bruk: python analyse_agent.py <research_json_fil>")
    else:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
        resultat = kjor_analyse(data)
        print("\nAnalyse:")
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
