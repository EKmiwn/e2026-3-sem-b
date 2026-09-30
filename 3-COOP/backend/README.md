# Coop – Grønne Besparelser – prototype

Kunden vælger sin SuperBrugsen i Coop-appen og ser butikkens gule mærker live med vare, ny pris, førpris, dato og antal på hylden. Medarbejderen opretter et mærke på håndterminalen ved at scanne varen og vælge rabat. Udsolgte og udløbne mærker forsvinder automatisk, og kunder med samtykke får besked, når deres butik nedsætter en vare.

Kravgrundlag: [`../Kravspecifikation.md`](../Kravspecifikation.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5203** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5203 er optaget – bruger port 5204 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5203/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: store, product, employee, customer, yellow_label, sale, notification
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Coop-appen · Håndterminal (medarbejder) · Nøgletal · Varer og kunder
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
| `GET` | `/api/customers` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/customers` | Opret (CRUD) |
| `GET` | `/api/customers/<customer_id>/notifications` | Kundens beskeder om nye gule mærker. |
| `PUT` | `/api/customers/<customer_id>/preferences` | Kunden vælger sin butik og slår notifikationer til/fra. Samtykket gemmes med tidspunkt (GDPR). |
| `DELETE` | `/api/customers/<item_id>` | Slet (CRUD) |
| `GET` | `/api/customers/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/customers/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/employees` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/employees` | Opret (CRUD) |
| `DELETE` | `/api/employees/<item_id>` | Slet (CRUD) |
| `GET` | `/api/employees/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/employees/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/health` | Systemstatus |
| `GET` | `/api/labels` | Alle mærker i en butik – også udsolgte og udløbne (medarbejderens overblik). |
| `POST` | `/api/labels` | Opret gult mærke: scan vare, vælg rabat (og antal). Kunder med samtykke i butikken får besked (F5). |
| `POST` | `/api/labels/<label_id>/remove` | Medarbejderen fjerner et mærke manuelt (fx hvis varen er kasseret). |
| `POST` | `/api/labels/<label_id>/sell` | Simulerer et salg i kassen. Når sidste vare er solgt, forsvinder mærket fra appen med det samme. |
| `GET` | `/api/products` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/products` | Opret (CRUD) |
| `DELETE` | `/api/products/<item_id>` | Slet (CRUD) |
| `GET` | `/api/products/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/products/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/products/ean/<ean>` | Scanning på håndterminalen: slå varen op på stregkode (EAN). |
| `GET` | `/api/stats` | Nøgletal pr. butik: mærker, solgt før udløb, madspild og tid pr. oprettelse. |
| `GET` | `/api/stores` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/stores` | Opret (CRUD) |
| `DELETE` | `/api/stores/<item_id>` | Slet (CRUD) |
| `GET` | `/api/stores/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/stores/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/stores/<store_id>/feed` | Feed med aktive gule mærker fra netop denne butik (F1) med vare, ny pris, førpris, dato og antal (F2). |
