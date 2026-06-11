import anthropic
import json
import os
from dotenv import load_dotenv

from config import AgentConfig, STANDARD_CONFIG

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def kjor_planlegging(research_data: dict, analyse_data: dict,
                     config: AgentConfig = None) -> str:
    if config is None:
        config = STANDARD_CONFIG
    tema = research_data.get("tema", "")

    innhold = f"""Tema: {tema}

=== NØKKELFAKTA (fra research) ===
{chr(10).join(f'- {f}' for f in analyse_data.get('nøkkelfakta', []))}

=== MØNSTRE OG TENDENSER ===
{chr(10).join(f'- {m}' for m in analyse_data.get('mønstre', []))}

=== USIKKERHET OG RISIKOER ===
{chr(10).join(f'- {u}' for u in analyse_data.get('usikkerhet', []))}

=== KUNNSKAPSHULL (krever videre arbeid) ===
{chr(10).join(f'- {k}' for k in analyse_data.get('kunnskapshull', []))}

=== ANALYTISK VURDERING ===
{analyse_data.get('sammendrag', '')}
Grunnlagsstyrke: {analyse_data.get('grunnlag_styrke', 'ukjent')}

Lag en konkret handlingsplan basert på dette grunnlaget."""

    print(f"  Planleggingsagent kjører...")

    plan = ""
    with client.messages.stream(
        model=config.plan_modell,
        max_tokens=config.plan_max_tokens,
        thinking={"type": "adaptive"},
        system=config.plan_prompt,
        messages=[{"role": "user", "content": innhold}],
    ) as stream:
        for tekst in stream.text_stream:
            plan += tekst

    print(f"  Ferdig")
    return plan


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Bruk: python planlegging_agent.py <research_json> <analyse_json>")
    else:
        with open(sys.argv[1], encoding="utf-8") as f:
            research = json.load(f)
        with open(sys.argv[2], encoding="utf-8") as f:
            analyse = json.load(f)
        kjor_planlegging(research, analyse)
