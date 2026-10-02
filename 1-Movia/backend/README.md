# Movia – Den Forudsigelige Rejse – prototype

Appen foreslår den roligste afgang ud fra støj- og trængselsdata fra bussens sensorer. Den sender et diskret digitalt solsikkesignal til chaufføren, når passageren stiger på, og guider rejsen med en visuel tidslinje og tryghedsnotifikationer. Den viser også, om bussen har en fysisk rolig zone. En rejseguide med stemme (`POST /api/assistant`) taler med passageren og guider gennem rejsen og appen. Linjerne er 2A, 4A, 5C, 150S, 250S og 350S.

Kravgrundlag: [`../Kravspecifikation.md`](../Kravspecifikation.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5201** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5201 er optaget – bruger port 5202 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5201/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: stop, line, line_stop, bus, departure, sensor_reading, passenger, trip,
                    sunflower_signal, notification, feedback
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Planlæg · Min rejse · Profil · Rejseguide (stemme) · Chauffør og Movia-data (demo)
  style.css         fælles stylesheet (projektfarver står i index.html)
  api.js            fælles klient: fetch() + JSON og små DOM-hjælpere
  app.js            præsentationslag for netop dette projekt
```

Klienten og serveren taler kun sammen via HTTP og JSON. Svarene vises i DOM'en, og det seneste
rå JSON-svar kan ses nederst på siden under "Seneste JSON-svar fra API'et".

Fejl returneres altid som JSON: `{"error": "…", "path": "/api/…"}` med statuskode 400, 404 eller 409.

## API

| Metode | Endepunkt | Beskrivelse |
| --- | --- | --- |
| `POST` | `/api/assistant` | Rejseguiden: modtager det, passageren siger eller skriver, og svarer i klart sprog. Kan finde den roligste rejse, gemme den, tjekke passageren ind, fortælle hvor langt der er igen og forklare appen. action fortæller frontenden, hvad der skal vises. |
| `GET` | `/api/buses` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/buses` | Opret (CRUD) |
| `GET` | `/api/buses/<bus_id>/signals` | Chaufførens skærm: aktive solsikkesignaler – kun token og stop, aldrig navn (NFR2, NFR4). |
| `DELETE` | `/api/buses/<item_id>` | Slet (CRUD) |
| `GET` | `/api/buses/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/buses/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/departures/<departure_id>/heatmap` | Sensorisk varmekort for én afgang: støj og trængsel forrest, i midten og bagerst (FR2, FR8). |
| `GET` | `/api/fleet` | Alle busser med aktuelt varmekort. |
| `GET` | `/api/health` | Systemstatus |
| `GET` | `/api/journeys` | Søg afgange mellem to stop og foreslå den roligste (sensordata) blandt de næste afgange. |
| `GET` | `/api/lines` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `GET` | `/api/lines/<item_id>` | Hent én (CRUD) |
| `GET` | `/api/lines/<line_id>/stops` | Linjens stoppesteder i rækkefølge med køretid fra første stop. |
| `GET` | `/api/passengers` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/passengers` | Opret (CRUD) |
| `DELETE` | `/api/passengers/<item_id>` | Slet (CRUD) |
| `GET` | `/api/passengers/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/passengers/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/passengers/<passenger_id>/trips` | Passagerens rejser, nyeste først. |
| `GET` | `/api/sensor-readings` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/sensor-readings` | Opret (CRUD) |
| `DELETE` | `/api/sensor-readings/<item_id>` | Slet (CRUD) |
| `GET` | `/api/sensor-readings/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/sensor-readings/<item_id>` | Opdatér (CRUD) |
| `POST` | `/api/sensors/simulate` | Simulerer, at alle busser sender en ny måling (i virkeligheden hvert få sekund). |
| `POST` | `/api/signals/<signal_id>/ack` | Chaufføren bekræfter diskret, at signalet er set. |
| `GET` | `/api/stats` | Nøgletal for Movia: rejser, solsikkesignaler og feedback. |
| `GET` | `/api/stops` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/stops` | Opret (CRUD) |
| `DELETE` | `/api/stops/<item_id>` | Slet (CRUD) |
| `GET` | `/api/stops/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/stops/<item_id>` | Opdatér (CRUD) |
| `POST` | `/api/trips` | Passageren vælger en afgang (AfgangValgt → RejseOprettet). |
| `GET` | `/api/trips/<trip_id>` | Visuel tidslinje, solsikkesignal og notifikationer for én rejse (FR4). |
| `POST` | `/api/trips/<trip_id>/advance` | Simulerer, at bussen kører til næste stop (i virkeligheden bussens GPS). |
| `POST` | `/api/trips/<trip_id>/board` | Passageren tjekker ind ved boarding. Er solsikkesignalet slået til, sendes det diskret til chaufføren (FR3, FR6). |
| `POST` | `/api/trips/<trip_id>/feedback` | Feedback efter endt rejse (FR7). |
