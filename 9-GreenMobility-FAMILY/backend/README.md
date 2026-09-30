# GreenMobility FAMILY – prototype

Familier tegner et månedligt Family-abonnement (profil, plan og valideret betaling), finder ledige biler efter zone, tidspunkt og biltype, reserverer og afslutter turen, så turdata logges. Partneraktiviteter udløser GreenCredits, og familien får personlige forslag ud fra sin historik (Book igen). Operations får et forecast pr. zone, biltype, ugedag og tidsrum ud fra historiske ture og anbefalede flytninger af biler.

Kravgrundlag: [`../Kravspecifikation.md`](../Kravspecifikation.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5209** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5209 er optaget – bruger port 5210 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5209/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: plan, zone, car_type, car, family, member, reservation, trip, partner, credit_transaction, relocation
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Opdag og tilmeld · Vores familie · Book bil · GreenCredits og partnere · Operations
  style.css         fælles stylesheet (projektfarver står i index.html)
  api.js            fælles klient: fetch() + JSON og små DOM-hjælpere
  app.js            præsentationslag for netop dette projekt
```

Klienten og serveren taler kun sammen via HTTP og JSON. Svarene vises i DOM'en, og det seneste
rå JSON-svar kan ses nederst på siden under "Seneste JSON-svar fra API'et".

Fejl returneres altid som JSON: `{"error": "…", "path": "/api/…"}` med statuskode 400, 402, 403, 404 eller 409.

## API

| Metode | Endepunkt | Beskrivelse |
| --- | --- | --- |
| `GET` | `/api/availability` | Tilgængelige biler i zonen for biltype og tidsrum, alternativer i andre zoner og forventet efterspørgsel. |
| `GET` | `/api/car-types` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/car-types` | Opret (CRUD) |
| `DELETE` | `/api/car-types/<item_id>` | Slet (CRUD) |
| `GET` | `/api/car-types/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/car-types/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/cars` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/cars` | Opret (CRUD) |
| `DELETE` | `/api/cars/<item_id>` | Slet (CRUD) |
| `GET` | `/api/cars/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/cars/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/families` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/families` | Tilmeld: opret profil, vælg plan og valider betaling. Medlemskabet er aktivt, når betalingen er godkendt. |
| `GET` | `/api/families/<family_id>/dashboard` | Familiens overblik: abonnement, forbrug af inkluderede timer, GreenCredits, reservationer, ture og forslag. |
| `GET` | `/api/families/<item_id>` | Hent én (CRUD) |
| `GET` | `/api/forecast` | Forecast pr. zone og biltype for en ugedag og et tidsrum ud fra historiske ture, sammenholdt med biler i zonen. |
| `GET` | `/api/health` | Systemstatus |
| `GET` | `/api/offer` | Opdager-fasen: abonnementer med pris og fordele samt partnerfordele. |
| `POST` | `/api/partner-activities` | Partneren registrerer en aktivitet, som udløser GreenCredits til familien. |
| `GET` | `/api/partners` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/partners` | Opret (CRUD) |
| `DELETE` | `/api/partners/<item_id>` | Slet (CRUD) |
| `GET` | `/api/partners/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/partners/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/plans` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/plans` | Opret (CRUD) |
| `DELETE` | `/api/plans/<item_id>` | Slet (CRUD) |
| `GET` | `/api/plans/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/plans/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/relocations` | Log over flytninger. |
| `POST` | `/api/relocations` | Operations flytter en bil til en anden zone efter forecastet. |
| `POST` | `/api/reservations` | Reserver en bil. Kræver aktivt medlemskab, en fører med kørekort og at bilen er ledig i tidsrummet. |
| `POST` | `/api/reservations/<reservation_id>/cancel` | Annullér en reservation, så bilen bliver ledig igen. |
| `POST` | `/api/reservations/<reservation_id>/complete` | Kør: efter kørslen logges turdata. Inkluderede minutter bruges først, derefter rabatpris. GreenCredits kan bruges. |
| `GET` | `/api/stats` | Nøgletal: familier, ture, kørte km, GreenCredits og biltyper. |
| `GET` | `/api/zones` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/zones` | Opret (CRUD) |
| `DELETE` | `/api/zones/<item_id>` | Slet (CRUD) |
| `GET` | `/api/zones/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/zones/<item_id>` | Opdatér (CRUD) |
