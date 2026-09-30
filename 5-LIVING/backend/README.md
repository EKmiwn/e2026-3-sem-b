# &LIVING – Buyer Matchmaking – prototype

Købere opretter en profil med økonomi, boligønsker og livsstil og giver samtykke til match. Systemet beregner en matchscore ud fra økonomisk kompatibilitet og livsstil. Matchede købere danner en gruppe, skriver sammen uden at dele kontaktoplysninger, finder boliger inden for gruppens samlede købekraft og pladsbehov (også skuffesager), stemmer på en fælles shortlist og anmoder om fremvisning. Mægleren ser kvalificerede grupper og bekræfter fremvisninger. Køberen vælges i toppen og sendes i headeren `X-User-Id` (simuleret login). Brugerfladen er på engelsk.

Kravgrundlag: [`../Requirement_Specifications.md`](../Requirement_Specifications.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5205** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5205 er optaget – bruger port 5206 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5205/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: setting, agent, buyer, buyer_group, group_member, property, message, shortlist_item, vote, viewing_request
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: My profile · Matches · Our group · Homes · Shortlist & viewings · &LIVING agent
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
| `GET` | `/api/agent/groups` | Kvalificerede købergrupper (mindst to medlemmer) med købekraft, shortlist og fremvisningsønsker. |
| `GET` | `/api/agents` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/agents` | Opret (CRUD) |
| `DELETE` | `/api/agents/<item_id>` | Slet (CRUD) |
| `GET` | `/api/agents/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/agents/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/buyers` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/buyers` | Opret (CRUD) |
| `POST` | `/api/buyers/<buyer_id>/consent` | Udtrykkeligt samtykke til at bruge økonomi- og livsstilsdata til match. Trækkes det tilbage, matches køberen ikke længere. |
| `DELETE` | `/api/buyers/<item_id>` | Slet (CRUD) |
| `GET` | `/api/buyers/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/buyers/<item_id>` | Opdatér (CRUD) |
| `POST` | `/api/groups` | Forbind med et match: opretter en gruppe eller tilføjer køberen til den indloggede købers gruppe. |
| `POST` | `/api/groups/<group_id>/leave` | Forlad gruppen. Historikken bevares, og de øvrige medlemmer beholder shortlisten. |
| `POST` | `/api/groups/<group_id>/messages` | Skriv til gruppen uden at dele personlige kontaktoplysninger. |
| `GET` | `/api/groups/<group_id>/properties` | Boliger inden for gruppens samlede købekraft og pladsbehov, bedste match først. |
| `POST` | `/api/groups/<group_id>/shortlist` | Gem en bolig på gruppens fælles shortlist. |
| `POST` | `/api/groups/<group_id>/viewings` | Anmod om åbent hus eller privat fremvisning via gruppens fælles profil. |
| `GET` | `/api/health` | Systemstatus |
| `GET` | `/api/matches` | Kompatible købere for den indloggede køber, bedste først, med delscorer og begrundelser. |
| `GET` | `/api/my-group` | Den indloggede købers nuværende gruppe – eller null. |
| `GET` | `/api/properties` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/properties` | Opret (CRUD) |
| `DELETE` | `/api/properties/<item_id>` | Slet (CRUD) |
| `GET` | `/api/properties/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/properties/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/settings` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/settings` | Opret (CRUD) |
| `DELETE` | `/api/settings/<item_id>` | Slet (CRUD) |
| `GET` | `/api/settings/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/settings/<item_id>` | Opdatér (CRUD) |
| `POST` | `/api/shortlist/<item_id>/vote` | Stem for (+1) eller imod (−1) en bolig på shortlisten med en valgfri kommentar. En ny stemme erstatter den gamle. |
| `PUT` | `/api/viewings/<viewing_id>` | Mægleren bekræfter eller afviser en fremvisning. |
