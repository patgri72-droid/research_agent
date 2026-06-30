# Godkjente poster — agentens stilskole

Legg dine **ferdig-redigerte, godkjente** LinkedIn-poster her som `.md`- eller
`.txt`-filer. `linkedin_agent.py` leser dem og bruker dem som stileksempler når
den skriver nye poster — slik lærer den stemmen din over tid.

## Slik bruker du det

1. Når du har finpusset et utkast til en post du er fornøyd med, lim inn den
   **endelige teksten** i en ny fil her (f.eks. `2026-06-tidsstempel-bug.md`).
2. Ta med kun selve posten — ikke bilde-prompter eller skjermbildeforslag.
   Jo renere eksempel, jo bedre lærer agenten.
3. Neste gang du kjører agenten, matcher den stemmen i disse postene.

## Detaljer

- Agenten tar de **nyeste** filene først (sortert på filnavn) og bruker maks
  antallet satt i `linkedin_godkjent_antall` i `config.py` (standard: 4).
- Tips: navngi filene med dato foran (`2026-06-...`) så de nyeste alltid
  havner øverst og veier tyngst.
- Du kan trygt slette denne LES_MEG-filen når du har lagt inn ekte poster
  (den blir også lest, men gjør lite skade).
