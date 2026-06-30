# Handlingsplan: Hvilke verktøy er det beste for å genere videoer med bruk av AI. Jeg vil lage anonnse videoer for leiligheter, jeg trenger at videoene er realistiske og har mulighet til å gjøre en sammensetning av bilder om til en smooth og realistisk gjennomgang av leiligheten

*Generert: 30.06.2026 14:06*

---

**Grunnlagsstyrke:** middels

**Analytisk vurdering:** Kunnskapsgrunnlaget gir et godt strukturert overblikk over tre distinkte teknologiske tilnærminger, og kjernekonklusjonen – at Kling og Google Veo er de sterkeste image-to-video-alternativene for realistiske gjennomganger – støttes av to uavhengige tester. Det kritiske svakhetspunktet er at ingen av kildene tester verktøyene spesifikt på leilighetsannonser, og rapporten mangler konkrete priser, norsk plattformkompatibilitet og opphavsrettslige vurderinger. Påstanden om 403% flere henvendelser bør ignoreres som beslutningsgrunnlag da den kommer fra en leverandør med egeninteresse. For en bruker som vil gå fra stillbilder til smooth walkthrough uten filming, er den reelle praktiske begrensningen at dedikerte eiendomsverktøy gir pan/zoom (ikke ekte 3D-bevegelse), mens Kling/Veo gir høyere realisme men krever mer teknisk kompetanse og har ukjente kostnader ved volumproduksjon.

---

# Handlingsplan: AI-genererte annonsevideo for leiligheter

## Overordnet vurdering før du starter

**Kritisk innsikt du må ta innover deg:** Det finnes *ingen* enkeltstående verktøy som tar stillbilder og produserer en ekte 3D-walkthrough automatisk. Du må velge mellom to realistiske veier:

| Vei | Resultat | Krav |
|-----|----------|------|
| **Vei A** – Kling/Veo (image-to-video) | Høy realisme, ekte bevegelse | Teknisk kompetanse, ukjent kostnad ved volum |
| **Vei B** – Dedikerte eiendomsverktøy | Rask/enkel, men kun pan/zoom på flat bilder | Lav kompetanseterskel, forutsigbar pris |

**Anbefaling:** Start med Vei A (Kling), test Vei B som backup, kombiner ved behov.

---

## FASE 1: Kartlegging og verifisering
### Prioritet: Høy | Tidsramme: 3–5 dager

### Steg 1.1 – Verifiser tilgjengelighet og pris for Kling og Google Veo (Dag 1–2)

**Konkrete handlinger:**
- Gå til **klingai.com** – opprett gratis konto og bekreft at norsk IP-adresse fungerer uten VPN
- Noter eksakt pris for «Professional»-modus (dette er moduset med høyest kvalitet – prisen er ikke bekreftet i research)
- Gå til **labs.google/veo** eller **VideoFX** – sjekk om Veo er tilgjengelig utenfor USA (dette er et kjent usikkerhetsmoment)
- Dokumenter: antall videosekunder per kreditt, maks oppløsning, og om du eier rettighetene til generert innhold

**Risikofaktor:** Veo er historisk sett geografisk begrenset. Hvis ikke tilgjengelig i Norge → dropp Veo, fokuser 100% på Kling.

**Suksesskriterium:** Du har aktiv konto i minst ett av verktøyene og kjenner faktisk kostnad per video.

---

### Steg 1.2 – Avklar opphavsrett og kommersielle rettigheter (Dag 2–3)

Dette steget hoppes over av de fleste – ikke gjør den feilen.

**Konkrete handlinger:**
- Les Klings bruksvilkår, avsnitt om «Commercial use» og «ownership of output»
- Sjekk om generert innhold kan brukes i kommersielle annonser (Finn.no, eiendomsmegling) uten ekstra lisens
- Kontakt **Forbrukerrådet** eller en medierettsjurist dersom vilkårene er uklare – en 15-minutters konsultasjon er billigere enn å publisere ulovlig innhold

**Risikofaktor:** Noen AI-verktøy forbeholder seg retten til å bruke output i treningsdata. For klientannonser er dette kritisk.

---

### Steg 1.3 – Test Finn.no-kravene til videoformat (Dag 3–4)

**Konkrete handlinger:**
- Logg inn på Finn.no Torget/Eiendom og sjekk tekniske krav: filformat (MP4/MOV), maks filstørrelse, lengdebegrensning, lydkrav
- Ring Finn.no support og spør eksplisitt: «Godtas AI-genererte annonsevideo?»
- Sjekk om norske eiendomsmeglere du samarbeider med har interne retningslinjer

**Kunnskapshull dette fyller:** Research nevner ikke Finn.no-kompatibilitet. Dette er blokkerende informasjon du *må* ha.

---

## FASE 2: Teknisk pilottest
### Prioritet: Høy | Tidsramme: 1–2 uker

### Steg 2.1 – Bygg en standard fotoworkflow (Dag 1–3 i fasen)

Bildekvaliteten inn bestemmer videokvaliteten ut. Dette steget er undervurdert.

**Konkrete krav til bilder (basert på beste praksis for image-to-video):**
- **Oppløsning:** Minimum 1920×1080, ideelt 4K
- **Format:** JPG eller PNG, ikke komprimert WebP
- **Vinkel:** Bred vinkel (16–24mm ekvivalent), fotografert fra hjørner for å maksimere romdybde
- **Antall bilder per rom:** 2–3 (start, midt, slutt av den tenkte kamerabanen)
- **Lys:** Natural lys + kunstig lys kombinert, unngå hard skyggekast

**Leilighetssekvens som fungerer:**
1. Entré (start) → 2. Stue (bevegelse inn) → 3. Kjøkken → 4. Soverom → 5. Bad → 6. Balkong/utsikt (slutt)

---

### Steg 2.2 – Produser første testvideoer i Kling (Dag 4–7 i fasen)

**Konkrete handlinger:**
1. Last opp bilde av stue som **startbilde** og bilde av kjøkken som **sluttbilde** i Klings «Start/End frame»-funksjon
2. Bruk denne prompten som utgangspunkt:
   > *«Smooth cinematic camera dolly forward through a modern Scandinavian living room, natural daylight, 4K, realistic interior photography style, no people»*
3. Generer i **Professional-modus** (høyeste kvalitet)
4. Evaluer etter disse kriteriene: Er vegger/møbler stabile? Er overgangen naturlig? Ser det ut som en leilighet eller et datasimulert rom?

**Kjør parallelt:** Test samme bilder i **Google Veo** hvis tilgjengelig, for å ha et sammenligningsgrunnlag.

---

### Steg 2.3 – Sammenkobling av klipp (Dag 7–10 i fasen)

Individuelle klipp må sys sammen til en sammenhengende video.

**Verktøy:**
- **CapCut** (gratis) eller **DaVinci Resolve** (gratis) for klipping
- Sørg for at hvert klipp starter og slutter med tilnærmet samme kamerabevegelse for sømløs overgang
- Legg til: stilren undertekst med romstørrelse og m², norsk voiceover (ElevenLabs eller Murf.ai for realistisk norsk stemme), bakgrunnsmusikk

**Tidsestimat per ferdige video:** 2–4 timer første gang, 45–60 min når du har malen.

---

## FASE 3: Vurder dedikerte eiendomsverktøy som skaleringsalternativ
### Prioritet: Middels | Tidsramme: Parallelt med Fase 2 (dag 4–10)

### Steg 3.1 – Test Styldod eller AutoReel

**Konkrete handlinger:**
- Gå til **styldod.com** – verifiser faktisk pris per video (research sier $5, men dette er ubekreftet)
- Test med én leilighet: last opp 5–8 bilder og se output
- Vurder ærlig: Ser det ut som pan/zoom på flat bilde (Kenneth-fra-Horten vil se det), eller er det troverdig nok for din målgruppe?

**Viktig distinksjon:** Disse verktøyene er ikke 3D-walkthrough – de zoomer og panorerer på stillbilder. For budsjettbevisste kjøpere kan dette holde. For luksusleiligheter vil det fremstå billig.

**Beslutningskriterium:**
- Leiligheter under 3 MNOK → Styldod/AutoReel kan holde
- Leiligheter over 3 MNOK → Kling er nødvendig for å matche forventningsnivå

---

## FASE 4: Produksjonsoppsett og skaleringsplan
### Prioritet: Middels | Tidsramme: Uke 3–4

### Steg 4.1 – Lag en repeterbar produksjonsmal

Når piloten er godkjent, dokumenter følgende:

```
PRODUKSJONSMAL PER LEILIGHET:
──────────────────────────────
Bilder: [antall, krav, format]
Kling-prompt: [standardtekst tilpasset leilighetstype]
Klipp-sekvens: [rekkefølge og lengde per rom]
Voiceover-tekst: [standardmal med variabelfelter]
Eksportkrav Finn.no: [format, størrelse, lengde]
Total produksjonstid: [X timer]
Kostnad per video: [Y NOK]
```

---

### Steg 4.2 – Prissett tjenesten din realistisk

Basert på ukjente priser i research, anbefaler jeg du kartlegger dette selv:

| Kostnadspost | Handling |
|-------------|----------|
| Kling Professional | Beregn per-video-kostnad ut fra abonnement delt på antall videomnd |
| Din arbeidstid | 45–60 min × timepris |
| Voiceover (ElevenLabs) | Ca. $5–22/mnd avh. av volum |
| Musikklisensiering | Epidemic Sound ca. 150 NOK/mnd |

**Ikke bruk Styldods «403% flere henvendelser»-påstand** i din markedsføring – dette er udokumentert leverandørdata.

---

## FASE 5: Oppskalering med Gaussian Splatting (valgfritt, langsiktig)
### Prioritet: Lav (foreløpig) | Tidsramme: Måned 2–3

Gaussian Splatting (Luma AI, Polycam) gir overlegen realisme, men krever filmede opptak på stedet.

**Vurder dette dersom:**
- Du jobber med leiligheter over 5–6 MNOK der produksjonskostnad er proporsjonal
- Du eller din fotograf kan filme 5–10 minutters video med telefon/kamera under visning

**Minimumskrav for filming:** God belysning, langsom bevegelse gjennom alle rom, 360°-rotasjon i hvert rom, ingen personer i bildet.

---

## Risikomatrise

| Risiko | Sannsynlighet | Konsekvens | Tiltak |
|--------|--------------|------------|--------|
| Veo ikke tilgjengelig i Norge | Høy | Lav (Kling er tilstrekkelig) | Fokuser på Kling fra dag 1 |
| Kling-pris for høy ved volum | Middels | Høy | Beregn breakeven vs. Styldod i Fase 1 |
| Finn.no godtar ikke AI-video | Lav | Høy | Avklar i Steg 1.3 *før* produksjon |
| Output mangler realisme | Middels | Middels | Pilottest før klientforpliktelse |
| Opphavsrettsproblem | Lav | Høy | Juridisk avklaring i Steg 1.2 |

---

## Prioritert rekkefølge – neste 14 dager

```
UKE 1:
□ Dag 1: Opprett Kling-konto, verifiser norsk tilgang og pris
□ Dag 2: Les og forstå kommersielle vilkår (Kling + evt. Veo)
□ Dag 3: Sjekk Finn.no videokrav, ring support
□ Dag 4-5: Fotografer én testleilighet etter bildekravene i Steg 2.1

UKE 2:
□ Dag 6-7: Produser testklipp i Kling (start/slutt-bilder per rom)
□ Dag 8: Sy klipp sammen i CapCut, legg til voiceover
□ Dag 9: Test parallelll i Styldod med samme bilder – sammenlign
□ Dag 10: Evaluer kvalitet og kostnad – ta beslutning om verktøyvalg
```

**Første beslutningspunkt:** Etter dag 10 vet du om Kling gir tilstrekkelig kvalitet til din prisklasse og om kostnaden er bærekraftig. Ingenting av det følgende bør bestemmes før du har det svaret.