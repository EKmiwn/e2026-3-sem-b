# DYNACAP Academy – prototype

Portal til DYNACAPs oplæringsstruktur i seks niveauer. HR opretter et forløb for hver ny konsulent. Konsulenten ser sit niveau, næste skridt og hvad der mangler, og markerer aktiviteter som gennemført. Vejlederen godkender eller afviser niveauet med kommentar, og godkendelse låser op for næste niveau. Ledelsen får en statusrapport pr. kontor. Samme indhold i Danmark og Norge, på dansk og engelsk. Brugeren vælges i toppen og sendes i headeren `X-User-Id` (simuleret login), og rollen styrer adgangen.

Kravgrundlag: [`../Kravspecifikation.md`](../Kravspecifikation.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5207** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5207 er optaget – bruger port 5208 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5207/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: office, person, level, activity, programme, activity_completion, level_review, certification, status_report
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Min oplæring · Konsulenter · Forløb og indhold · Statusrapport (fanerne vises efter rolle)
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
| `GET` | `/api/activities` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/activities` | Opret (CRUD) |
| `DELETE` | `/api/activities/<item_id>` | Slet (CRUD) |
| `GET` | `/api/activities/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/activities/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/consultants` | Konsulenter, brugeren må se, med niveau og fremdrift. |
| `POST` | `/api/consultants` | HR opretter en ny konsulent med et forløb med de seks niveauer – uden udvikler (F1). |
| `POST` | `/api/consultants/<consultant_id>/activities/<activity_id>/toggle` | Konsulenten markerer en aktivitet som gennemført (eller fortryder). Status opdateres med det samme (F3). |
| `POST` | `/api/consultants/<consultant_id>/certifications` | Registrér en bestået Salesforce-certificering manuelt (F8). |
| `POST` | `/api/consultants/<consultant_id>/levels/<level_id>/review` | Vejlederen godkender eller afviser et niveau med kommentar. Godkendelse låser op for næste niveau (F4, F5). |
| `GET` | `/api/consultants/<consultant_id>/progress` | Konsulentens forside: aktuelt niveau, fremdrift og hvad der mangler til næste niveau (F2). ?lang=en for engelsk. |
| `GET` | `/api/health` | Systemstatus |
| `GET` | `/api/levels` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/levels` | Opret (CRUD) |
| `DELETE` | `/api/levels/<item_id>` | Slet (CRUD) |
| `GET` | `/api/levels/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/levels/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/me` | Den indloggede bruger. |
| `GET` | `/api/offices` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/offices` | Opret (CRUD) |
| `DELETE` | `/api/offices/<item_id>` | Slet (CRUD) |
| `GET` | `/api/offices/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/offices/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/people` | Testbrugere til det simulerede login. |
| `POST` | `/api/reports/send` | Send statusrapporten til ledelsen nu. I drift sker det automatisk hver 14. dag. |
| `GET` | `/api/reports/status` | Statusrapport fordelt på kontor – samme niveaukrav i Danmark og Norge (F6, F7). |
