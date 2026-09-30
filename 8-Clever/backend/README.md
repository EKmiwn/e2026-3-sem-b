# Clever – Opladning der bare virker – prototype

En forbedret Clever-app: realtidsstatus og antal ledige udtag, pris før start med prisadvarsel (pris-trafiklys), start via automatisk genkendelse, QR-kode eller stander-ID, live effekt, kWh og pris med forklaring, når effekten falder, dokumenteret grøn status, kvittering med betalingsstatus med det samme, faste stop med push-advarsler, fejlrapportering uden at ringe, ruteplan med ladestop i DK, SE, NO og DE og et månedligt forbrugsoverblik. Brugeren vælges i toppen og sendes i headeren `X-User-Id` (simuleret login). Opladningen er simuleret, så ét sekund svarer til ét minut.

Kravgrundlag: [`../Readme.MD`](../Readme.MD)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5208** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5208 er optaget – bruger port 5209 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5208/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: operator, tariff, location, charger, connector, app_user, car, subscription, energy_mix, session, payment, favorite, fault_report, alert
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Find stander · Opladning · Faste stop · Planlæg tur · Rapportér fejl · Forbrug · Drift
  style.css         fælles stylesheet (projektfarver står i index.html)
  api.js            fælles klient: fetch() + JSON og små DOM-hjælpere
  app.js            præsentationslag for netop dette projekt
```

Klienten og serveren taler kun sammen via HTTP og JSON. Svarene vises i DOM'en, og det seneste
rå JSON-svar kan ses nederst på siden under "Seneste JSON-svar fra API'et".

Fejl returneres altid som JSON: `{"error": "…", "path": "/api/…"}` med statuskode 400, 401, 403, 404 eller 409.

## API

| Metode | Endepunkt | Beskrivelse |
| --- | --- | --- |
| `GET` | `/api/cars` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/cars` | Opret (CRUD) |
| `DELETE` | `/api/cars/<item_id>` | Slet (CRUD) |
| `GET` | `/api/cars/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/cars/<item_id>` | Opdatér (CRUD) |
| `PUT` | `/api/chargers/<charger_id>/status` | Drift (OCPP): standerens status ændres. Går den ude af drift, advares brugere med den som favorit (FR-10). |
| `GET` | `/api/energy-mix` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `GET` | `/api/energy-mix/<item_id>` | Hent én (CRUD) |
| `GET` | `/api/fault-reports` | Fejlrapporter. Med X-User-Id kun brugerens egne (sagsstatus i appen) – uden: alle (drift). |
| `POST` | `/api/fault-reports` | Fejlrapport via guiden med kategori, beskrivelse og evt. foto – sendes til drift med stander-ID og placering. |
| `PUT` | `/api/fault-reports/<report_id>` | Drift opdaterer sagens status. Brugeren får besked. |
| `GET` | `/api/health` | Systemstatus |
| `GET` | `/api/locations` | Lokationer med realtidsstatus, antal ledige udtag, effekt, pris og grøn status. Filtre: ?min_power=&plug=&max_price=&operator_id=&only_free=1&lat=&lng= (afstand). |
| `GET` | `/api/locations/<location_id>/detail` | Én lokation med alle standere og udtag. |
| `GET` | `/api/my/active-session` | Brugerens igangværende opladning – eller null. |
| `GET` | `/api/my/alerts` | Push-advarsler til brugeren (nyeste først). |
| `GET` | `/api/my/favorites` | Brugerens faste stop med status. |
| `POST` | `/api/my/favorites` | Gem en lokation som fast stop med et navn, fx "Hallen" (maks. 2 tryk). |
| `DELETE` | `/api/my/favorites/<favorite_id>` | Fjern et fast stop. |
| `GET` | `/api/my/overview` | Forbrug, pris og CO₂ pr. måned de seneste 12 måneder og abonnement sammenlignet med forbrug. |
| `GET` | `/api/operators` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/operators` | Opret (CRUD) |
| `DELETE` | `/api/operators/<item_id>` | Slet (CRUD) |
| `GET` | `/api/operators/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/operators/<item_id>` | Opdatér (CRUD) |
| `POST` | `/api/quote` | Pris før start (FR-3), prisadvarsel i forhold til brugerens normale pris (FR-11) og grøn status nu (FR-8). |
| `GET` | `/api/route` | Rute med ladestop fra Sjælland til en by i DK, SE, NO eller DE (roaming). Ruten følger vejforløbet. Hvert stop er den lynlader længst fremme på ruten, der kan nås med mindst 15 % batteri. Der lades til 80 %. |
| `POST` | `/api/route/send-to-car` | FR-14 (could): send ruten til bilens skærm (CarPlay / Android Auto) – simuleret. |
| `POST` | `/api/sessions` | Start opladning. Kræver, at prisen er vist og bekræftet (FR-3, AFIR). Pris og strømmix låses ved start. |
| `GET` | `/api/sessions/<session_id>` | Live effekt, kWh, løbende pris og grøn status – og forklaring, hvis effekten falder (FR-6 – FR-8). |
| `POST` | `/api/sessions/<session_id>/stop` | Stop opladningen. Kun brugeren, der startede den, kan stoppe den. Kvitteringen kommer med det samme. |
| `GET` | `/api/tariffs` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/tariffs` | Opret (CRUD) |
| `DELETE` | `/api/tariffs/<item_id>` | Slet (CRUD) |
| `GET` | `/api/tariffs/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/tariffs/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/users` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/users` | Opret (CRUD) |
| `DELETE` | `/api/users/<item_id>` | Slet (CRUD) |
| `GET` | `/api/users/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/users/<item_id>` | Opdatér (CRUD) |
| `PUT` | `/api/users/<user_id>/filters` | Filtre bevares mellem sessioner (FR-16). |
