# Læringsrum 2.0 – Elevevaluering – prototype

Elever logger ind og besvarer korte spørgsmål om trivsel, læring, møbler og miljø på en skala fra 1 til 5 (smileys). Svarene gemmes pr. måling, og eleven får personlig feedback og kan følge sin egen udvikling. Læreren ser klassens resultater samlet med gennemsnit og procenttal, sammenligner over tid og fortæller klassen, hvad der gøres. Læringsrum 2.0 (administrator) ser alle klasser og redigerer spørgsmål og målinger. Resultater vises først ved mindst 3 svar. Brugeren logger ind med brugernavn og sendes i headeren `X-User-Id` (simuleret login).

Kravgrundlag: [`../Kravspecifikation.md`](../Kravspecifikation.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5210** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5210 er optaget – bruger port 5211 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5210/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: school, class, app_user, question, survey_round, response, answer, follow_up
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Login · Spørgeskema · Min udvikling · Klassens resultater · Udvikling over tid · Overblik · Spørgsmål og målinger (fanerne vises efter rolle)
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
| `GET` | `/api/classes` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/classes` | Opret (CRUD) |
| `POST` | `/api/classes/<class_id>/follow-ups` | Læreren fortæller klassen, hvad der gøres ved resultaterne – eleverne ser det på deres side. |
| `GET` | `/api/classes/<class_id>/results` | Klassens resultater for én måling: gennemsnit og procenttal pr. spørgsmål og kategori (kun ved mindst 3 svar). |
| `GET` | `/api/classes/<class_id>/trend` | Sammenlign klassens svar over tid: gennemsnit og andel positive pr. kategori for hver måling. |
| `DELETE` | `/api/classes/<item_id>` | Slet (CRUD) |
| `GET` | `/api/classes/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/classes/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/health` | Systemstatus |
| `POST` | `/api/login` | Log ind med brugernavn (simuleret – ingen adgangskode i prototypen). |
| `GET` | `/api/my/development` | Elevens egen udvikling over tid, personlig feedback og lærerens opfølgning ("Det gør vi nu"). |
| `POST` | `/api/my/responses` | Gem elevens besvarelse (1–5 pr. spørgsmål). Svaret giver personlig feedback med det samme. |
| `GET` | `/api/my/survey` | Den åbne måling med spørgsmål – og om eleven allerede har svaret. |
| `GET` | `/api/overview` | Administratorens overblik: deltagelse og andel positive pr. kategori for alle klasser i hver måling. |
| `GET` | `/api/questions` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/questions` | Opret (CRUD) |
| `DELETE` | `/api/questions/<item_id>` | Slet (CRUD) |
| `GET` | `/api/questions/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/questions/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/rounds` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/rounds` | Opret (CRUD) |
| `DELETE` | `/api/rounds/<item_id>` | Slet (CRUD) |
| `GET` | `/api/rounds/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/rounds/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/schools` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/schools` | Opret (CRUD) |
| `DELETE` | `/api/schools/<item_id>` | Slet (CRUD) |
| `GET` | `/api/schools/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/schools/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/users` | Testbrugere til login-siden (brugernavn og rolle). |
