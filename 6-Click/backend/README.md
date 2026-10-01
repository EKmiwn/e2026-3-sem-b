# Fotohuset Click – Bestil print – prototype

Kunden uploader billeder, vælger format, overflade, kvalitet, beskæring, rotation og antal, ser live pris og en advarsel ved for lav effektiv DPI, vælger afhentning eller forsendelse og betaler hos en (simuleret) betalingsudbyder. Ordren lander i butikkens produktionskø. Operatøren logger ind med PIN, sorterer og filtrerer køen, udskriver ordresedler grupperet efter papirrullebredde, afleverer printjobbet til C8 og skifter status. Kunden får besked, når ordren er klar. Billedfiler slettes automatisk efter opbevaringsfristen.

Kravgrundlag: [`../Kravspecifikation.md`](../Kravspecifikation.md)

## Kør prototypen

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # første gang
pip install -r requirements.txt                       # første gang
python app.py
```

Åbn **http://localhost:5206** – Flask serverer både API'et (`/api/...`) og frontenden fra `../frontend`.
Er porten optaget, vælger serveren selv den næste ledige port og skriver adressen i terminalen
(fx ` * Port 5206 er optaget – bruger port 5207 i stedet`). Du kan også vælge port selv med `PORT=5300 python app.py`.
`frontend/index.html` kan også åbnes direkte fra disken. Så kalder den `http://localhost:5206/api` (attributten `data-api-port` i `index.html`).

Databasen `backend/database.db` (SQLite3) oprettes og fyldes med fiktive testdata fra `seed.sql` ved første start.
Nulstil den med `python database.py --reset`.

## Struktur

```
backend/
  app.py            logiklag: forretningsregler og endepunkter for netop dette projekt
  core.py           fælles for alle prototyper: Flask-app, JSON-fejl, CORS og generisk CRUD
  database.py       fælles for alle prototyper: SQLite3-forbindelse og hjælpefunktioner
  schema.sql        tabeller: setting, product, customer, operator, photo_order, image, order_line, print_job
  seed.sql          fiktive testdata
  requirements.txt
frontend/
  index.html        skærmbilleder: Bestil print (5 trin) · Min ordre · Ordrekø (operatør) · Produktkatalog
  style.css         fælles stylesheet (projektfarver står i index.html)
  api.js            fælles klient: fetch() + JSON og små DOM-hjælpere
  app.js            præsentationslag for netop dette projekt
```

Klienten og serveren taler kun sammen via HTTP og JSON. Svarene vises i DOM'en. Åbnes siden med `?debug=1`,
kan det seneste rå JSON-svar ses nederst under "Seneste JSON-svar fra API'et". Kunderne ser det ikke.

Fejl returneres altid som JSON: `{"error": "…", "path": "/api/…"}` med statuskode 400, 401, 402, 403, 404 eller 409.

## API

| Metode | Endepunkt | Beskrivelse |
| --- | --- | --- |
| `GET` | `/api/health` | Systemstatus |
| `POST` | `/api/maintenance/purge-images` | Kør sletning af billedfiler efter opbevaringsfristen nu (sker også automatisk, når køen åbnes). |
| `POST` | `/api/operators/login` | Operatøren logger ind med PIN (simuleret login). |
| `POST` | `/api/orders` | Opretter en tom kurv med en tilfældig adgangsnøgle. |
| `GET` | `/api/orders/<order_id>` | Kundens ordre med billeder, ordrelinjer og pris (kræver ?key=). Bruges også til indsigt (§17). |
| `POST` | `/api/orders/<order_id>/checkout` | Kunden godkender kurven, vælger afhentning/forsendelse, udfylder kontaktoplysninger og giver samtykke. |
| `DELETE` | `/api/orders/<order_id>/images` | Ret til sletning (§17): kunden sletter sine billedfiler. Ordrelinjerne bevares til regnskab. |
| `POST` | `/api/orders/<order_id>/images` | 1.0 Håndtér billedupload: filtype, pixelmål, filstørrelse og miniature (FK1, FK2). |
| `DELETE` | `/api/orders/<order_id>/images/<image_id>` | Fjern et billede fra kurven (og dets ordrelinjer). |
| `POST` | `/api/orders/<order_id>/lines` | 2.0 Konfigurér printordre: format, overflade, kvalitet, beskæring, rotation og antal (FK3–FK9). |
| `PUT` | `/api/orders/<order_id>/lines` | Læg alle billeders valg i kurven på én gang. Body: `{"lines": [...]}`. Erstatter kurvens linjer. |
| `DELETE` | `/api/orders/<order_id>/lines/<line_id>` | Fjern en ordrelinje fra kurven. |
| `POST` | `/api/orders/<order_id>/payment` | Svar fra betalingsudbyderen (simuleret). Ved godkendt betaling placeres ordren i produktionskøen (FK12, FK13). |
| `POST` | `/api/orders/<order_id>/release` | Frigiv ordren til print: opretter printjobbet til C8 og sætter status 'i produktion' (FK18). |
| `GET` | `/api/orders/<order_id>/slip` | 5.0 Ordreseddel: ordre-id, kunde og ordrelinjer grupperet efter papirrullebredde (FK16, FK17). |
| `PUT` | `/api/orders/<order_id>/status` | Operatøren skifter status manuelt. Ved 'klar' underrettes kunden (FK19–FK21). |
| `GET` | `/api/products` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/products` | Opret (CRUD) |
| `DELETE` | `/api/products/<item_id>` | Slet (CRUD) |
| `GET` | `/api/products/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/products/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/queue` | 4.0 Produktionskøen sorteret efter ønsket færdigdato. Filtrér med ?roll_width=… (FK14, FK15). |
| `POST` | `/api/quote` | Live pris og DPI-kontrol for ét billede i ét format (FK8, FK9 – vises inden for ét sekund). |
| `GET` | `/api/settings` | Hent liste (filtrér med ?felt=værdi) (CRUD) |
| `POST` | `/api/settings` | Opret (CRUD) |
| `DELETE` | `/api/settings/<item_id>` | Slet (CRUD) |
| `GET` | `/api/settings/<item_id>` | Hent én (CRUD) |
| `PUT` | `/api/settings/<item_id>` | Opdatér (CRUD) |
| `GET` | `/api/stats` | Ordredata til indkøb og prissætning: formater, ordrer og omsætning (kræver login). |

`POST`, `PUT` og `DELETE` på `/api/products` og `/api/settings` kræver operatørlogin (`X-User-Id`).
