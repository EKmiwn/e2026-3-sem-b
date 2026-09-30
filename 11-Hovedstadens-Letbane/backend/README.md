# Hovedstadens Letbane – rejseassistent – prototype

Mobil-først web-app til pendlere: afgangstavle for begge retninger med planlagt og forventet tid, forsinkelse og aflysning, rejsesøgning med rejsetid og skift til S-tog og bus, aktive driftsmeddelelser med alternativ rejse, favoritrejser uden konto og notifikation ved kritiske forstyrrelser, feedback, dansk/engelsk og stor tekst. Personalet udsender driftsmeddelelser. Navne, id'er og JSON-felter følger data dictionary i kravspec.md (afsnit 5), og endepunkterne i afsnit 9.2 findes med samme navne. Driftsdata er simulerede (C-5).

Kravgrundlag: [`../kravspec.md`](../kravspec.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5211** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5211 er optaget – bruger port 5212 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5211/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: station, rute, rutestop, skinnestraekning, koeretoej, afgang, stoptid, personale, vagt, driftsmeddelelse (+ _station, _afgang), transportmiddel, skifteforbindelse, bruger, favoritrejse, feedback
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Forside · Afgange · Rejse · Feedback · Indstillinger · Personale
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
| `POST` | `/api/brugere` | Opretter en anonym bruger. bruger_id genereres som UUID – ingen navn eller e-mail (D-3). |
| `DELETE` | `/api/brugere/<bruger_id>` | Slet brugeren og alle tilknyttede data (GDPR). |
| `GET` | `/api/brugere/<bruger_id>` | Brugerens indstillinger. |
| `PUT` | `/api/brugere/<bruger_id>` | Sprog (da/en), stor tekst og samtykke til notifikationer. |
| `GET` | `/api/brugere/<bruger_id>/data` | S-4: brugeren kan se, hvilke data der gemmes, og hvorfor. |
| `GET` | `/api/brugere/<bruger_id>/favoritter` | Favoritrejser med næste afgang og status – status på favoritrejse på højst 2 tryk (G-1, U-2). |
| `GET` | `/api/brugere/<bruger_id>/notifikationer` | Notifikation = bruger_id + meddelelse_id + titel_da + (favorit_id) for KRITISKE meddelelser på favoritrejser (BR-5). |
| `GET` | `/api/driftsmeddelelser` | Liste af Driftsmeddelelse. ?aktive=true giver kun de aktive – KRITISK først. |
| `POST` | `/api/driftsmeddelelser` | Personale opretter en driftsmeddelelse (S-2). AFLYSNING markerer berørte afgange som aflyst. KRITISK udløser notifikation til brugere med berørte favoritrejser (BR-5). |
| `PUT` | `/api/driftsmeddelelser/<meddelelse_id>/afslut` | Personale afslutter en driftsmeddelelse nu. Aflysninger for resten af dagen ophæves. |
| `POST` | `/api/favoritter` | Gem en favoritrejse uden at oprette konto (F-8). |
| `DELETE` | `/api/favoritter/<favorit_id>` | Slet en favoritrejse. |
| `POST` | `/api/feedback` | Feedbackindsendelse = (bruger_id) + (afgang_id) + vurdering + kategori + (kommentar). |
| `GET` | `/api/feedback/rapport` | Ugentlig feedbackrapport til personalet (BE-8): antal og gennemsnit pr. kategori de seneste 7 dage. |
| `GET` | `/api/health` | Systemstatus |
| `GET` | `/api/personale` | Personale til det simulerede personale-login – kun id og rolle, aldrig navn (D-4). |
| `GET` | `/api/rejse` | Rejseforslag = {Rejseben} + samlet_rejsetid_min + (Driftsmeddelelse). ?fra=&til=&tid= (ISO eller HH:MM). |
| `GET` | `/api/stationer` | Liste af Station med tilgængelighed (elevator og cykelparkering). |
| `GET` | `/api/stationer/<station_id>` | Én station. |
| `GET` | `/api/stationer/<station_id>/afgange` | Afgangstavle = station_id + opdateret_tid + {Afgangslinje} for de næste afgange i begge retninger. |
| `GET` | `/api/stationer/<station_id>/skift` | Liste af Skifteforbindelse med transportmiddel og gangtid. |
| `GET` | `/api/status` | Punktlighed i dag indtil nu: andel afgange ≤ 2 min forsinket ved endestation (definition 5.1, antagelse A-2). |
