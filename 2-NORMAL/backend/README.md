# NORMAL – Er varen på lager? – prototype

Kunden søger efter et produkt, vælger produktet og en NORMAL-butik og ser produktets lagerstatus (på lager, få tilbage eller udsolgt). Er varen udsolgt, foreslås andre butikker med varen på lager, først i samme by. Medarbejdere retter lagertal, og søgninger og opslag samles til nøgletal.

Kravgrundlag: [`../kravspec.md`](../kravspec.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5202** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5202 er optaget – bruger port 5203 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5202/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: setting, store, category, product, stock, search_log, lookup_log
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Find vare i butik · Medarbejder: lager · Nøgletal · Sortiment og butikker
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
| `GET` | `/api/categories` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/categories` | Opret (CRUD) |
| `DELETE` | `/api/categories/<item_id>` | Slet (CRUD) |
| `GET` | `/api/categories/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/categories/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/health` | Systemstatus |
| `GET` | `/api/products` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/products` | Opret (CRUD) |
| `DELETE` | `/api/products/<item_id>` | Slet (CRUD) |
| `GET` | `/api/products/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/products/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/products/<product_id>/availability` | Lagerstatus for et produkt i den valgte butik. Er det udsolgt, foreslås andre butikker med varen på lager. |
| `GET` | `/api/search` | Søg efter produkt på navn, mærke, kategori, varenummer eller søgeord. Søgningen logges til nøgletal. |
| `GET` | `/api/settings` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/settings` | Opret (CRUD) |
| `DELETE` | `/api/settings/<item_id>` | Slet (CRUD) |
| `GET` | `/api/settings/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/settings/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/stats` | Nøgletal: søgninger, opslag, forgæves opslag (udsolgt) og efterspurgte produkter. |
| `GET` | `/api/stores` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/stores` | Opret (CRUD) |
| `DELETE` | `/api/stores/<item_id>` | Slet (CRUD) |
| `GET` | `/api/stores/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/stores/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/stores/<store_id>/stock` | Butikkens lager med status pr. produkt (til medarbejdere). |
| `PUT` | `/api/stores/<store_id>/stock/<product_id>` | Medarbejderen retter antal på lager (i virkeligheden fra NORMALs lagersystem). |
