# Movia – Den Forudsigelige Rejse – dokumentation af prototypen

Unge med usynlige handicap får en **forudsigelig og tryg busrejse**. Appen foreslår den **roligste afgang** ud fra støj- og trængselsdata fra bussens sensorer.
Når passageren stiger på, sender den et **digitalt solsikkesignal** til chaufføren, uden at passageren skal sige noget.
En **visuel tidslinje** og **tryghedsnotifikationer** guider rejsen. Appen viser også, om bussen har en fysisk **rolig zone**.
En **rejseguide med stemme** taler med passageren, finder og gemmer rejsen, læser beskeder højt undervejs og forklarer appen.

Kravgrundlag: [`Kravspecifikation.md`](Kravspecifikation.md)

## Hvad kan prototypen

| Skærm | Funktion |
|---|---|
| **1 · Planlæg** | Vælg fra og til (tidspunktet er nu, medmindre man folder *Vælg et andet tidspunkt* ud). Kun den **roligste afgang** vises stort med tid, linje, rolighed og rolig zone og knappen *Vælg denne rejse*. *Se hvor der er roligt i bussen* viser varmekortet, og *Se andre afgange* folder resten ud |
| **2 · Min rejse** | Tre trin (Planlagt → I bussen → Fremme), én stor besked, visuel tidslinje og én stor knap ad gangen. *Jeg er steget på* sender solsikkesignalet, og *Simulér: bussen kører til næste stop* flytter bussen. Feedback gives med fem ansigter |
| **Profil** | Solsikkesignal til/fra, oplæsning til/fra og hvor mange stop før man vil have besked |
| **Rejseguide** (knappen 🎙 nederst) | Tal (mikrofon) eller skriv til guiden. Den svarer i tekst og læser svaret højt. Hurtigknapper til de mest brugte spørgsmål |
| **Chauffør** (demo) | Chaufførens skærm med aktive solsikkesignaler (kun kode og stop) og knappen *Set ✓* |
| **Movia-data** (demo) | Nøgletal, alle busser med aktuelt varmekort, linjer og stoppesteder, feedback fra rejser, simulering af nye sensormålinger og manuel registrering af en måling |

Passageren vælges i toppen. Chauffør og Movia-data er skjult for passageren og vises med knappen *Vis demo-skærme* nederst på siden.

## Ændringer efter ønske fra gruppen

| Ønske | Implementering |
|---|---|
| AI-stemmesystem, der taler med brugeren og guider gennem rejsen og appen | Rejseguiden: `POST /api/assistant` forstår hensigten og svarer ud fra rejsens data. Browseren lytter med `SpeechRecognition` og læser højt med `speechSynthesis` (dansk). Guiden læser også nye beskeder højt, når rejsen ændrer sig (`guideSay()` i `app.js`) |
| Buslinjerne 5C, 2A, 4A, 250S, 350S og 150S | `seed.sql`: seks linjer med 29 stoppesteder og 18 busser. `GET /api/lines/<id>/stops` viser en linjes stoppesteder |
| Lettere og mere brugervenlig brugerflade | Én kolonne, større tekst og knapper på mindst 48 px, tre faner til passageren, én anbefaling og én handling ad gangen, detaljer foldet sammen, og feedback med ansigter i stedet for tal |

**Det kan rejseguiden:**

| Passageren siger | Guiden gør |
|---|---|
| "Jeg vil fra Husum Torv til Nørreport" · "til lufthavnen" | Finder den roligste afgang, viser den på skærmen og spørger, om rejsen skal gemmes |
| "Ja tak" | Gemmer den foreslåede rejse og åbner *Min rejse* |
| "Jeg er steget på" | Tjekker ind og sender solsikkesignalet |
| "Hvor langt er der igen?" · "Hvornår skal jeg af?" | Fortæller hvor bussen er, hvor mange stop der er tilbage, og hvornår man er fremme |
| "Hvor er der roligt i bussen?" | Fortæller hvilket område der er roligst lige nu |
| "Jeg er nervøs" | Svarer roligt og fortæller det næste konkrete skridt |
| "Hvad er solsikkesignalet?" · "Hvor kører 5C?" · "Hjælp mig" | Forklarer signalet, linjen eller den skærm, passageren står på |

Stoppesteder genkendes også uden "St." og med kaldenavne som *Hovedbanegården* og *lufthavnen*. Oplæsning kan slås fra i guiden eller i profilen (`passenger.voice_guide`), så guiden kun svarer med tekst.

## Fra krav til kode

| Krav | Implementering |
|---|---|
| FR1 Roligste rute ud fra realtidsdata | `GET /api/journeys` (`find_journeys()`) finder de næste afgange på linjer, der kører mellem stoppene, og markerer den med højeste `expected_score` som `is_calmest` |
| FR2 Sensorisk varmekort | `bus_calm()` tager seneste måling pr. område (`FORREST`, `MIDTEN`, `BAGERST`). `GET /api/departures/<id>/heatmap` |
| FR3 Digitalt solsikkesignal ved boarding | `POST /api/trips/<id>/board` opretter et `sunflower_signal` til afgangens bus |
| FR4 Visuel tidslinje | `trip_view()` giver hvert stop tilstanden `PASSERET`, `HER` eller `KOMMENDE` |
| FR5 Tryghedsnotifikation før stop | `advance_notifications()` sender `STOP_NÆRMER_SIG`, når der er `notify_stops_before` stop tilbage, og `STÅ_AF_NU` ved målet |
| FR6 Slå solsikkesignal til/fra | `passenger.sunflower_enabled` (`PUT /api/passengers/<id>`). Er det slået fra, sendes intet signal |
| FR7 Feedback efter rejsen | `POST /api/trips/<id>/feedback`, kun når rejsen er `AFSLUTTET` |
| FR8 Rolig zone | `bus.quiet_zone` vises i søgeresultatet og på varmekortet. Har bussen en rolig zone, er det zonens rolighed, der vurderes |
| NFR1 Opdateres inden for få sekunder | Hver måling gemmes med tidspunkt, og vurderingen bruger altid den nyeste (`POST /api/sensor-readings`, `POST /api/sensors/simulate`) |
| NFR2/NFR4 Signalet må ikke identificere brugeren | Chaufføren ser kun et tilfældigt token (`SOL-4F2A`) og stoppet, aldrig navn eller diagnose |
| 4.1 Roligt, lav-stimuli udtryk | Afdæmpede farver, store knapper, få ord og ét budskab ad gangen på tidslinjen |

**Rolighed:** Støj (40–80 dB → 0–100 %) og trængsel (0–100 %) vægter lige meget: `score = 100 − (støj % + trængsel %) / 2`.
En score på mindst 65 er *rolig*, 40–64 er *middel*, og under 40 er *travl*.

**Events:** RejseSøgt → RoligRuteForeslået · AfgangValgt → RejseOprettet · BoardingRegistreret → SolsikkeSignalSendt · StopNærmerSig → NotifikationSendt · RejseAfsluttet → FeedbackAnmodet.

## Datamodel

```mermaid
erDiagram
    LINE ||--o{ LINE_STOP : "line_id"
    STOP ||--o{ LINE_STOP : "stop_id"
    LINE ||--o{ BUS : "line_id"
    LINE ||--o{ DEPARTURE : "line_id"
    BUS ||--o{ DEPARTURE : "bus_id"
    BUS ||--o{ SENSOR_READING : "bus_id"
    PASSENGER ||--o{ TRIP : "passenger_id"
    DEPARTURE ||--o{ TRIP : "departure_id"
    STOP ||--o{ TRIP : "from_stop_id"
    STOP ||--o{ TRIP : "to_stop_id"
    TRIP ||--o{ SUNFLOWER_SIGNAL : "trip_id"
    BUS ||--o{ SUNFLOWER_SIGNAL : "bus_id"
    TRIP ||--o{ NOTIFICATION : "trip_id"
    TRIP ||--o{ FEEDBACK : "trip_id"
    STOP {
        INTEGER id PK
        TEXT name
    }
    LINE {
        INTEGER id PK
        TEXT name
        TEXT description
    }
    LINE_STOP {
        INTEGER id PK
        INTEGER line_id FK
        INTEGER stop_id FK
        INTEGER seq
        INTEGER minutes_from_start
    }
    BUS {
        INTEGER id PK
        TEXT number
        INTEGER line_id FK
        TEXT quiet_zone
    }
    DEPARTURE {
        INTEGER id PK
        INTEGER line_id FK
        INTEGER bus_id FK
        TEXT departs_at
    }
    SENSOR_READING {
        INTEGER id PK
        INTEGER bus_id FK
        TEXT area
        REAL noise_db
        INTEGER crowding_pct
        TEXT measured_at
    }
    PASSENGER {
        INTEGER id PK
        TEXT name
        TEXT school
        INTEGER sunflower_enabled
        INTEGER voice_guide
        INTEGER notify_stops_before
    }
    TRIP {
        INTEGER id PK
        INTEGER passenger_id FK
        INTEGER departure_id FK
        INTEGER from_stop_id FK
        INTEGER to_stop_id FK
        TEXT status
        INTEGER current_seq
        TEXT created_at
        TEXT boarded_at
        TEXT finished_at
    }
    SUNFLOWER_SIGNAL {
        INTEGER id PK
        INTEGER trip_id FK
        INTEGER bus_id FK
        TEXT token
        TEXT stop_name
        TEXT status
        TEXT sent_at
        TEXT acknowledged_at
    }
    NOTIFICATION {
        INTEGER id PK
        INTEGER trip_id FK
        TEXT type
        TEXT message
        TEXT created_at
    }
    FEEDBACK {
        INTEGER id PK
        INTEGER trip_id FK
        INTEGER calm_rating
        INTEGER felt_safe
        TEXT comment
        TEXT created_at
    }
```

## Eksempel på dataudveksling

Passageren Emil (id 1) siger til rejseguiden, hvor han vil hen:

```bash
curl -X POST http://localhost:5201/api/assistant \
  -H 'Content-Type: application/json' \
  -d '{"message": "Jeg vil fra Husum Torv til Nørreport", "passenger_id": 1}'
```

Svar `200` (tidspunkterne afhænger af, hvad klokken er):

```json
{
  "intent": "PLANLAEG",
  "reply": "Den roligste bus er linje 5C klokken 14:19 fra Husum Torv. Du er fremme ved Nørreport St. klokken 14:34. Der er roligt i bussen. Der er en rolig zone forrest i bussen. Skal jeg gemme rejsen?",
  "action": { "type": "SHOW_JOURNEY", "from_stop_id": 15, "to_stop_id": 17, "departure_id": 244 }
}
```

Varmekortet for 150S kl. 07:50. Bussen har en rolig zone forrest, så den samlede vurdering er *rolig*, selv om midten og bagenden er mere fyldt:

```bash
curl http://localhost:5201/api/departures/303/heatmap
```

Svar `200` (forkortet):

```json
{
  "line": "150S",
  "departs_at": "08:20",
  "bus_number": "Bus 1503",
  "quiet_zone": "FORREST",
  "average_score": 54,
  "expected_score": 72,
  "level": "ROLIG",
  "areas": [
    { "area": "FORREST", "noise_db": 50.0, "crowding_pct": 30, "score": 72, "level": "ROLIG", "quiet_zone": true },
    { "area": "MIDTEN", "noise_db": 60.0, "crowding_pct": 50, "score": 50, "level": "MIDDEL", "quiet_zone": false },
    { "area": "BAGERST", "noise_db": 64.0, "crowding_pct": 60, "score": 40, "level": "MIDDEL", "quiet_zone": false }
  ]
}
```

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Terminalen skriver ` * Åbn http://localhost:5201`. Åbn adressen i browseren. Flask serverer både API'et (`/api/...`) og frontenden.

- **Port:** Prototypen bruger port **5201** (5200 + projektnummer). Er porten optaget, vælger `run()` i `core.py` selv den næste ledige og skriver fx ` * Port 5201 er optaget – bruger port 5202 i stedet`. Du kan også vælge port selv med `PORT=5300 python app.py`.
- **Stop serveren** med `Ctrl` + `C` i terminalen, hvor den kører.
- **Kodeændringer:** Serveren kører i debug-tilstand og genstarter selv, når du gemmer en `.py`-fil. Den bliver på samme port. Ændringer i `frontend/` kræver kun, at du genindlæser siden.
- **Database:** `backend/database.db` oprettes med testdata ved første start. Nulstil den med `python database.py --reset`, mens serveren er stoppet.
- **Tjek at backenden svarer:** `curl http://localhost:5201/api/health`

### Fejlfinding

| Problem | Årsag | Løsning |
|---|---|---|
| ` * Port 5201 er optaget – bruger port …` | En anden proces, ofte en glemt server, bruger porten | Brug den adresse, der står i terminalen. Se hvad der optager porten med `lsof -nP -iTCP:5201 -sTCP:LISTEN`. En Flask-server i debug-tilstand er to processer, så stop dem begge med `lsof -t -iTCP:5201 -sTCP:LISTEN \| xargs kill` |
| `ModuleNotFoundError: No module named 'flask'` | Det virtuelle miljø er ikke aktiveret, eller Flask er ikke installeret | `source .venv/bin/activate` og `pip install -r requirements.txt` |
| Siden viser "Kan ikke hente data fra backenden" | Serveren kører ikke, eller `index.html` er åbnet direkte fra disken, mens serveren kører på en anden port | Start serveren og åbn adressen fra terminalen i stedet for filen |
| De gamle linjer (300S) vises stadig, eller `no such column: voice_guide` | `database.db` er oprettet før de nye linjer og rejseguiden | Stop serveren og kør `python database.py --reset` |
| Rejseguiden siger ikke noget | Oplæsning er slået fra, eller browseren har ingen dansk stemme | Tryk på *🔇 Kun tekst* i guiden for at slå oplæsning til. Svarene står altid som tekst |
| Mikrofonen virker ikke | Browseren understøtter ikke talegenkendelse (fx Firefox), eller der er ikke givet adgang til mikrofonen | Brug Chrome, Edge eller Safari og tillad mikrofonen, eller skriv til guiden |
| Tallene passer ikke efter mange tests | Databasen indeholder testdata fra tidligere afprøvninger | Stop serveren og kør `python database.py --reset` |
| `no such table …` | `database.db` er tom eller ødelagt | `python database.py --reset` |

## Arkitektur

Prototypen følger holdets fælles tre-lags struktur (se [`../README.md`](../README.md)):

```mermaid
flowchart LR
    subgraph Klient["Browser – præsentationslag"]
        HTML["index.html + style.css"] --- JS["app.js"] --- API["api.js · api()"]
    end
    subgraph Server["Flask – logiklag"]
        ROUTES["app.py · endepunkter og forretningsregler"] --- CORE["core.py · run(), register_crud(), ApiError"]
    end
    subgraph Data["Datalag"]
        DBPY["database.py"] --- DB[("SQLite3 · database.db")]
    end
    API <-->|"HTTP + JSON"| ROUTES
    CORE --- DBPY
```

| Fil | Lag | Indhold |
|---|---|---|
| `frontend/index.html` | Præsentation | Skærmbilleder som faneblade og formularer. Projektets farver og `data-api-port` |
| `frontend/app.js` | Præsentation | Henter data med `api()`, tegner dem i DOM'en og sender formularer. Rejseguidens tale ind og ud (Web Speech API) |
| `frontend/api.js` | Præsentation | Fælles for alle prototyper: `api()` (fetch + JSON), `h()`, `renderTable()`, `fillSelect()`, `formToJson()`, `bindCrudForm()` og `toast()` |
| `frontend/style.css` | Præsentation | Fælles responsivt design |
| `backend/app.py` | Logik | Projektets forretningsregler og endepunkter |
| `backend/core.py` | Logik | Fælles: `create_app()` (Flask, CORS, JSON-fejl), `run()` (start på ledig port), `ApiError` og `register_crud()` |
| `backend/database.py` | Data | Fælles: forbindelse, `query_all/query_one/execute`, `transaction()` og `init_db()` |
| `backend/schema.sql` · `seed.sql` | Data | Tabeller og fiktive testdata |

Alle fejl returneres som JSON (`{"error": "…", "path": "/api/…"}`) med statuskode 400, 401, 403, 404 eller 409 og vises som en rød besked i frontenden.
Nederst på siden kan man åbne **"Seneste JSON-svar fra API'et"** og se den rå dataudveksling.
Den fulde endepunktsliste står i [`backend/README.md`](backend/README.md).

## Design og responsivitet

- Samme stylesheet i alle prototyper. Kun farverne (`--brand`, `--brand-dark`, `--brand-soft`) sættes i `index.html`.
- Layoutet virker fra mobil (375 px) til desktop uden vandret scroll. Kort lægger sig under hinanden på små skærme, og brede tabeller scroller inde i deres kort.
- Formularfelter kan ikke blive bredere end deres kort. En `<select>` med lange valgmuligheder skubber altså ikke formularen ud over kanten.
- Beskeder vises kort i toppen (grøn = gennemført, rød = fejl fra serveren).


## Testdata

6 buslinjer (2A, 4A, 5C, 150S, 250S, 350S) med 29 stoppesteder, 18 busser (10 med rolig zone) og afgange hvert 10. minut kl. 06:00–22:00.
Seneste sensormåling pr. bus og område. 3 passagerer: Emil og Sara har solsikkesignal og oplæsning slået til, Noah har begge dele slået fra.
Prøv fx rejsen Husum Torv → Nørreport St., hvor både 5C og 350S kører.

## Afgrænsning

Ingen rigtig Bluetooth-forbindelse til chaufføren, GPS eller integration med Rejseplanen. Bussens position flyttes med knappen *Simulér*, og sensormålinger simuleres.
Afgange er en fast daglig køreplan uden forsinkelser. Den fysiske rolige zone er kun registreret som en egenskab ved bussen.
Rejseguiden er ikke en rigtig sprogmodel: den genkender hensigten med nøgleord (`assistant()` i `app.py`) og kan derfor kun det, der står i tabellen ovenfor. Talegenkendelse og oplæsning sker i browseren og afhænger af, om browseren har en dansk stemme.
Linjernes stoppesteder og køretider er et forenklet udvalg og er ikke kontrolleret mod Movias køreplan. Linjerne kører kun i én retning i prototypen.
