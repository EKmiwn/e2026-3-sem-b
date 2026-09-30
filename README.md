# Hold B – prototyper

Hver gruppemappe indeholder en prototype bygget ud fra gruppens kravspecifikation, med samme arkitektur og design som Hold A:

- `backend/`: Python Flask API med en SQLite3-database
- `frontend/`: HTML, CSS og JavaScript, der henter JSON fra API'et

| # | Projekt | Prototype | Lokal port | Dokumentation |
|---|---|---|---|---|
| 1 | Movia | Den Forudsigelige Rejse: roligste afgang ud fra støj/trængsel, digitalt solsikkesignal, visuel tidslinje og rolig zone | 5201 | [DOCS](1-Movia/DOCS.md) · [API](1-Movia/backend/README.md) |
| 2 | NORMAL | Søg produkt → vælg butik → lagerstatus og andre butikker med varen | 5202 | [DOCS](2-NORMAL/DOCS.md) · [API](2-NORMAL/backend/README.md) |
| 3 | COOP | Grønne Besparelser: gule mærker live fra egen SuperBrugsen, oprettet på håndterminalen | 5203 | [DOCS](3-COOP/DOCS.md) · [API](3-COOP/backend/README.md) |
| 4 | Habitus | Tale-til-tekst: optag, kategorisér, godkend (medicin altid) og overfør til Sofus/Outlook | 5204 | [DOCS](4-Habitus/DOCS.md) · [API](4-Habitus/backend/README.md) |
| 5 | &LIVING | Buyer Matchmaking: match købere, dan gruppe, find boliger, shortlist og fremvisning (engelsk UI) | 5205 | [DOCS](5-LIVING/DOCS.md) · [API](5-LIVING/backend/README.md) |
| 6 | Fotohuset Click | Bestil print i 5 trin med DPI-advarsel, betaling, produktionskø, ordreseddel og printjob | 5206 | [DOCS](6-Click/DOCS.md) · [API](6-Click/backend/README.md) |
| 7 | DYNACAP | Academy: seks oplæringsniveauer, niveaugodkendelse og statusrapport pr. kontor (dansk/engelsk) | 5207 | [DOCS](7-DYNACAP/DOCS.md) · [API](7-DYNACAP/backend/README.md) |
| 8 | Clever | Ladeapp: realtidsstatus, pris før start, live opladning, grøn status, fejlrapport og ruteplan | 5208 | [DOCS](8-Clever/DOCS.md) · [API](8-Clever/backend/README.md) |
| 9 | GreenMobility FAMILY | Familieabonnement, booking, GreenCredits og forecast til flådeplacering | 5209 | [DOCS](9-GreenMobility-FAMILY/DOCS.md) · [API](9-GreenMobility-FAMILY/backend/README.md) |
| 10 | Elevevaluering | Læringsrum 2.0: elever vurderer trivsel og møbler, lærere ser resultater og udvikling over tid | 5210 | [DOCS](10-Elevevaluering/DOCS.md) · [API](10-Elevevaluering/backend/README.md) |
| 11 | Hovedstadens Letbane | Rejseassistent: afgangstavle, rejsesøgning, driftsmeddelelser, favoritter og feedback | 5211 | [DOCS](11-Hovedstadens-Letbane/DOCS.md) · [API](11-Hovedstadens-Letbane/backend/README.md) |

- **`DOCS.md`** beskriver prototypen: krav, forretningsregler, ER-diagram og testdata.
- **`backend/README.md`** viser alle API-endepunkter.

## Struktur

Alle prototyper er bygget ens, og strukturen er den samme:

```
<projekt>/
├── DOCS.md
├── backend/
│   ├── app.py            projektets endepunkter og forretningsregler
│   ├── core.py           fælles Flask-kode (ens i alle projekter – også Hold A)
│   ├── database.py       fælles SQLite-kode (ens i alle projekter – også Hold A)
│   ├── schema.sql        tabeller
│   ├── seed.sql          testdata
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css         fælles stylesheet (projektfarver sættes i index.html)
    ├── api.js            fælles fetch- og DOM-hjælpere
    └── app.js            projektets frontend-logik
```

Hovedstadens Letbane bruger string-id'er fra gruppens data dictionary (fx `"HER"` og `"L-SYD"`) og har derfor egne endepunkter i stedet for `register_crud()`. `core.py` og `database.py` er stadig de fælles filer.

Flask serverer frontenden på `/` og API'et på `/api/...` fra samme adresse.
Prototyper med roller (Habitus, &LIVING, Click, DYNACAP, Clever, Elevevaluering og Letbanens personale) bruger et simuleret login, hvor den valgte bruger sendes i en header (`X-User-Id` eller `X-Personale-Id`).

## Kør lokalt

```bash
cd 1-Movia/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py                  # åbn http://localhost:5201
```

Databasen oprettes med testdata ved første start. Nulstil den med `python database.py --reset`.
Er porten optaget, bruger serveren automatisk den næste ledige og skriver adressen i terminalen.

## Deployment

Prototyperne er ikke deployet endnu. De kan køre på DigitalOcean på samme måde som Hold A (Gunicorn som systemd-service pr. projekt med skabelonen `gunicorn@.service`).
Brug fx portene `:8101` til `:8111`, så de ikke kolliderer med Hold A's `:8001` til `:8011`.
