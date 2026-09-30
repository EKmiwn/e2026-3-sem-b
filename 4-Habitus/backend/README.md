# Habitus – Tale til dokumentation – prototype

Medarbejderen starter og stopper en optagelse, og talen omdannes til tekst. Systemet kategoriserer teksten (observation, udvikling eller medicin), foreslår beboeren og markerer alt, det er usikkert på. Medicin kræver altid manuel bekræftelse. Den godkendte tekst overføres til det rette felt i journalsystemet (Sofus) og evt. til Outlook, og lydfilen slettes. Medarbejderen vælges i toppen og sendes i headeren `X-User-Id` (simuleret login).

Kravgrundlag: [`../Kravspecifikation.md`](../Kravspecifikation.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5204** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5204 er optaget – bruger port 5205 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5204/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: department, staff, resident, medication, recording, journal_entry
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Optag · Til godkendelse · Journal · Overblik · Beboere og medicin
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
| `GET` | `/api/departments` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/departments` | Opret (CRUD) |
| `DELETE` | `/api/departments/<item_id>` | Slet (CRUD) |
| `GET` | `/api/departments/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/departments/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/health` | Systemstatus |
| `DELETE` | `/api/journal/<entry_id>` | Slet en forkert post. |
| `PUT` | `/api/journal/<entry_id>` | Ret en post efterfølgende. Hvem og hvornår gemmes. |
| `GET` | `/api/medications` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/medications` | Opret (CRUD) |
| `DELETE` | `/api/medications/<item_id>` | Slet (CRUD) |
| `GET` | `/api/medications/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/medications/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/my-residents` | Beboere, som den indloggede medarbejder har adgang til (egen afdeling – lederen ser alle). |
| `GET` | `/api/recordings` | Optagelser i medarbejderens afdeling (filtrér med ?status=AFVENTER_GODKENDELSE). |
| `POST` | `/api/recordings` | Modtager en afsluttet optagelse som tekst og laver et struktureret udkast. Medicin og usikre resultater kræver altid godkendelse – øvrigt gemmes med det samme og kan rettes bagefter. |
| `POST` | `/api/recordings/<recording_id>/approve` | Medarbejderen gennemser, retter og godkender udkastet. Derefter overføres det, og lydfilen slettes. |
| `POST` | `/api/recordings/<recording_id>/reject` | Forkast et forkert genkendt udkast. Lydfilen slettes, og intet gemmes i journalen. |
| `GET` | `/api/residents` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/residents` | Opret (CRUD) |
| `DELETE` | `/api/residents/<item_id>` | Slet (CRUD) |
| `GET` | `/api/residents/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/residents/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/residents/<resident_id>/journal` | Beboerens dokumentation grupperet efter system og felt – som den ville stå i Sofus og Outlook. |
| `GET` | `/api/staff` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/staff` | Opret (CRUD) |
| `DELETE` | `/api/staff/<item_id>` | Slet (CRUD) |
| `GET` | `/api/staff/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/staff/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/stats` | Optagelser, godkendelser og anslået sparet tid til direkte beboerkontakt. |
