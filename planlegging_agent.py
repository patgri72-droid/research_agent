import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Du er en ekspert planlegger. Du får research-data og en analyse fra spesialiserte agenter.

Din oppgave er å lage en KONKRET, HANDLINGSORIENTERT plan:
1. Prioriter tiltak etter effekt og gjennomførbarhet (høy/middels/lav)
2. Angi realistiske tidsestimater per steg
3. Adresser risikofaktorer fra analysen eksplisitt
4. Fyll eventuelle kunnskapshull med anbefalinger om videre undersøkelse
5. Vær spesifikk — ikke generelle råd

Planens kvalitet avhenger av at den er direkte forankret i research-funnene og analysen."""

def kjor_planlegging(research_data: dict, analyse_data: dict) -> str:
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
        model="claude-sonnet-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
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
