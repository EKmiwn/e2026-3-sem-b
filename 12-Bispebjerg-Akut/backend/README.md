# Bispebjerg Akutmodtagelse – Digital registrering – prototype

Patienten registrerer symptomer, skadetype, smertegrad, medicin og allergier før eller ved ankomst og får et unikt registreringsnummer. Med nummeret og sin fødselsdato kan patienten følge status i forløbet og opdatere sine oplysninger. Sygeplejersker og læger ser oplysningerne i en patientkø, sætter triage og bestiller undersøgelser, som sendes til den afdeling, der udfører dem. Personalet vælges i toppen og sendes i headeren `X-User-Id` (simuleret login).

Kravgrundlag: [`../Kravspecifikation.md`](../Kravspecifikation.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5212** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5212 er optaget – bruger port 5213 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5212/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: department, staff, exam_type, registration, status_event, examination, access_log
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Patient: Registrér · Patient: Min status · Patientkø · Undersøgelser · Overblik · Opsætning
  style.css         fælles stylesheet (projektfarver står i index.html)
  api.js            fælles klient: fetch() + JSON og små DOM-hjælpere
  app.js            præsentationslag for netop dette projekt
```

Klienten og serveren taler kun sammen via HTTP og JSON. Svarene vises i DOM'en, og det seneste
rå JSON-svar kan ses nederst på siden under "Seneste JSON-svar fra API'et".

Fejl returneres altid som JSON: `{"error": "…", "path": "/api/…"}` med statuskode 400, 401, 403, 404 eller 409.

## API

Endepunkter under `/api/patient/` bruges af patienten uden login. Resten af de projektspecifikke endepunkter kræver headeren `X-User-Id`.

| Metode | Endepunkt | Beskrivelse |
| --- | --- | --- |
| `GET` | `/api/access-log` | De seneste 50 opslag og ændringer i patientdata – hvem, hvad og hvornår. |
| `GET` | `/api/departments` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/departments` | Opret (CRUD) |
| `DELETE` | `/api/departments/<item_id>` | Slet (CRUD) |
| `GET` | `/api/departments/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/departments/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/exam-types` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/exam-types` | Opret (CRUD) |
| `DELETE` | `/api/exam-types/<item_id>` | Slet (CRUD) |
| `GET` | `/api/exam-types/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/exam-types/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/examinations` | Bestilte undersøgelser. Afdelingspersonale ser kun egen afdeling og kun de oplysninger, undersøgelsen kræver (?status=BESTILT). |
| `POST` | `/api/examinations/<examination_id>/complete` | Markér en undersøgelse som udført. Når alle patientens undersøgelser er udført, venter patienten på lægen. |
| `GET` | `/api/health` | Systemstatus |
| `POST` | `/api/patient/registrations` | Patienten indtaster symptomer, skadetype, smertegrad, medicin og allergier og får et unikt registreringsnummer. |
| `GET` | `/api/patient/registrations/<reg_number>` | Patienten ser egne oplysninger og status i forløbet (kræver ?birth_date=ÅÅÅÅ-MM-DD). |
| `PUT` | `/api/patient/registrations/<reg_number>` | Patienten opdaterer sine oplysninger ved behov. Personalet kan se, at der er ændret. |
| `POST` | `/api/patient/registrations/<reg_number>/arrive` | Patienten, der har registreret sig hjemmefra, melder sin ankomst og kommer i kø til sygeplejersken. |
| `GET` | `/api/registrations` | Patientkøen for sygeplejersker og læger: ikke-vurderede først, derefter efter triage og ventetid (?status=… eller ?status=ALLE). |
| `GET` | `/api/registrations/<registration_id>` | Patientprofil: symptomer, forløb, undersøgelser og tidligere besøg. Opslaget logges. |
| `POST` | `/api/registrations/<registration_id>/examinations` | Personalet markerer behov for undersøgelser. Bestillingen sendes til den afdeling, der udfører den. |
| `POST` | `/api/registrations/<registration_id>/status` | Send patienten videre til lægen (VENTER_PÅ_LÆGE) eller afslut forløbet (AFSLUTTET – kun læger). |
| `POST` | `/api/registrations/<registration_id>/triage` | Sygeplejersken eller lægen sætter triageniveau og note. Systemet foreslår aldrig selv et niveau. |
| `GET` | `/api/staff` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/staff` | Opret (CRUD) |
| `DELETE` | `/api/staff/<item_id>` | Slet (CRUD) |
| `GET` | `/api/staff/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/staff/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/stats` | Nøgletal uden persondata: patienter pr. status, ventetid, udfyldelsestid og åbne undersøgelser. |
