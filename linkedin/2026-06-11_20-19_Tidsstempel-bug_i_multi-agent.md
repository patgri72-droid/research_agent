## Ferdig post (kopier teksten under)

En knapp som ikke gjorde noen ting holdt på å knekke meg i forrige uke. 🐛

Jeg har bygget et lite multi-agent-system: du gir det et tema, og tre AI-agenter jobber etter tur — én søker og researcher, én analyserer kritisk, én lager en handlingsplan. Alt lagres som rapporter du kan åpne igjen fra en historikk-liste.

Problemet: jeg klikket på en gammel rapport i historikken, og ingenting skjedde. Ingen feilmelding. Bare stillhet.

Det tok en stund før vi fant rotårsaken sammen, og den var lumsk: hver agent kalte `datetime.now()` på sitt eget tidspunkt. Forskningsagenten lagret filene sine 21:36. Resten ble lagret 21:37 — og historikken registrerte ALLE filstier med det siste tidsstempelet. Så lenken pekte på en fil som rett og slett ikke fantes.

Løsningen var nesten pinlig enkel: lag ett tidsstempel ÉN gang, og send det videre til alle. Én sannhet, ikke fire.

Det som sitter igjen hos meg: AI skriver kode som ser helt riktig ut linje for linje. Bugen lå ikke i en linje — den lå i antakelsen om at "nå" betyr det samme for alle. Den slags helhet må jeg fortsatt eie selv.

Hvor ofte har en bug egentlig handlet om en skjult antakelse hos deg, ikke en feil i koden? 🤔

— — — — — — — — — —
🇬🇧 English version below
— — — — — — — — — —

A button that did absolutely nothing nearly broke me last week. 🐛

I've been building a small multi-agent system: you hand it a topic, and three AI agents work in sequence — one searches and researches, one analyzes critically, one builds an action plan. Everything gets saved as reports you can reopen from a history list.

The problem: I clicked an old report in the history, and nothing happened. No error. Just silence.

It took a while before we found the root cause together, and it was sneaky: each agent called `datetime.now()` at its own moment. The research agent saved its files at 21:36. The rest were saved at 21:37 — and the history logged ALL the file paths with that last timestamp. So the link pointed to a file that simply didn't exist.

The fix was almost embarrassingly simple: generate one timestamp ONCE, and pass it to everyone. One source of truth, not four.

What stuck with me: AI writes code that looks perfectly correct line by line. The bug wasn't in any line — it was in the assumption that "now" means the same thing for everyone. That kind of whole-picture thinking is still mine to own.

How often has a bug really been about a hidden assumption of yours, rather than a flaw in the code? 🤔

#vibecoding #buildinginpublic #aiagents #python #debugging #læringsreise

---

## 🎨 Bilde-prompter (lim inn i Midjourney/DALL-E/Gemini)

**toppbilde:**
> A conceptual illustration of three robot agents standing in a line, each holding a clock showing a slightly different time (21:36, 21:37), connected by glowing data threads, one thread broken and dangling, dark moody developer-desk background, soft cinematic lighting, clean modern flat-illustration style with subtle depth

**alternativt:**
> Close-up of a single glowing clock at the center being shared by three abstract AI figures via light beams, symbolizing one shared source of truth, minimalist tech aesthetic, deep blue and amber palette, high detail

## 📸 Skjermbilder fra prosjektet ditt

- Kodebit som viser den gamle versjonen der hver funksjon kaller datetime.now() vs. den nye der ett felles ts sendes inn som parameter
- Streamlit-historikk-panelet med listen over tidligere søk — gjerne med en oppføring uthevet (den som tidligere var "død")
- Terminal/diff som viser endringen i run.py der ts genereres én gang og kjedes videre til kjor_research og lagre_alt

*Vinkling: Hvordan jeg fikset en lumsk tidsstempel-bug i multi-agent-systemet mitt, og hva det laerte meg om aa bygge med AI*
*Generert: 11.06.2026 20:19*
