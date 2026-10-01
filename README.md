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
| 8 | Clever | Ladeapp: realtidsstatus, pris før start, live opladning, grøn status, fejlrapport og ruteplan | 5208 | [DOCS](8-Clever/DOCS.md) · [API](8-Clever/backend/README.md) |
| 9 | GreenMobility FAMILY | Familieabonnement, booking, GreenCredits og forecast til flådeplacering | 5209 | [DOCS](9-GreenMobility-FAMILY/DOCS.md) · [API](9-GreenMobility-FAMILY/backend/README.md) |
| 10 | Elevevaluering | Læringsrum 2.0: elever vurderer trivsel og møbler, lærere ser resultater og udvikling over tid | 5210 | [DOCS](10-Elevevaluering/DOCS.md) · [API](10-Elevevaluering/backend/README.md) |
| 11 | Hovedstadens Letbane | Rejseassistent: afgangstavle, rejsesøgning, driftsmeddelelser, favoritter og feedback | 5211 | [DOCS](11-Hovedstadens-Letbane/DOCS.md) · [API](11-Hovedstadens-Letbane/backend/README.md) |
| 12 | Bispebjerg Akutmodtagelse | Digital registrering: symptomer før/ved ankomst, registreringsnummer, patientstatus, triage og undersøgelser sendt til afdelinger (dansk/engelsk) | 5212 | [DOCS](12-Bispebjerg-Akut/DOCS.md) · [API](12-Bispebjerg-Akut/backend/README.md) |

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
Prototyper med roller (Habitus, &LIVING, Click, Clever, Elevevaluering, Letbanens personale og Bispebjergs personale) bruger et simuleret login, hvor den valgte bruger sendes i en header (`X-User-Id` eller `X-Personale-Id`).

## Kør lokalt

Kræver Python 3.10 eller nyere. Kommandoerne køres fra projektets `backend`-mappe, fx `1-Movia/backend`.

### Mac og Linux (Terminal)

```bash
cd 1-Movia/backend
python3 -m venv .venv                # første gang
source .venv/bin/activate
pip install -r requirements.txt      # første gang
python app.py                        # åbn http://localhost:5201
```

### Windows – trin for trin

Eksemplet bruger `1-Movia`. Skift mappenavnet ud for at starte en anden prototype – porten står i tabellen øverst.

1. **Installér Python.** Hent Python 3.10 eller nyere fra [python.org](https://www.python.org/downloads/) og sæt flueben i *"Add python.exe to PATH"* i installationsprogrammet.
2. **Åbn PowerShell i projektmappen.** Åbn mappen `Hold-B-kravspecifikationer` i Stifinder, højreklik på et tomt område og vælg *"Åbn i Terminal"*. I VS Code kan du i stedet bruge *Terminal → New Terminal*.
3. **Tjek at Python virker.** Kommandoen skal vise et versionsnummer på 3.10 eller højere:

   ```powershell
   py --version
   ```

   Er `py` ikke fundet, så brug `python` i stedet for `py` her og i trin 5. Virker ingen af dem, så gentag trin 1 og åbn et nyt terminalvindue.
4. **Gå til prototypens `backend`-mappe:**

   ```powershell
   cd 1-Movia\backend
   ```

5. **Opret et virtuelt miljø og installér pakkerne** (kun første gang):

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   Når miljøet er aktivt, står der `(.venv)` forrest på linjen.
6. **Start appen:**

   ```powershell
   python app.py
   ```

7. **Åbn appen i browseren** på <http://localhost:5201>. Lad terminalvinduet stå åbent, så længe du bruger appen.
8. **Stop appen** med `Ctrl` + `C` i terminalen.

Næste gang er det nok at aktivere miljøet og starte appen:

```powershell
cd 1-Movia\backend
.venv\Scripts\Activate.ps1
python app.py
```

**Fejlen *"running scripts is disabled on this system"*:** Tillad lokale scripts én gang med kommandoen herunder, og kør derefter `.venv\Scripts\Activate.ps1` igen.

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Kommandoprompt (cmd) i stedet for PowerShell:** Trinene er de samme, men miljøet aktiveres med `.venv\Scripts\activate.bat`.

### Gælder for alle

- Databasen oprettes med testdata ved første start. Nulstil den med `python database.py --reset`, mens serveren er stoppet.
- Stop serveren med `Ctrl` + `C`. Deaktivér det virtuelle miljø med `deactivate`.
- Er porten optaget, bruger serveren automatisk den næste ledige og skriver adressen i terminalen.
- **11-Hovedstadens-Letbane på Windows:** Windows har ikke tidszonedata indbygget. Kør `pip install tzdata` én gang, så tiderne vises i dansk tid (`Europe/Copenhagen`). Uden pakken bruges maskinens egen tidszone.

| Opgave | Mac og Linux | Windows (PowerShell) | Windows (cmd) |
|---|---|---|---|
| Vælg selv port | `PORT=5300 python app.py` | `$env:PORT=5300; python app.py` | `set PORT=5300 && python app.py` |
| Se hvad der bruger porten | `lsof -nP -iTCP:5201 -sTCP:LISTEN` | `Get-NetTCPConnection -LocalPort 5201` | `netstat -ano \| findstr :5201` |
| Stop en glemt server | `lsof -t -iTCP:5201 -sTCP:LISTEN \| xargs kill` | `Stop-Process -Id <PID>` | `taskkill /PID <PID> /F` |

Kommandoerne i hvert projekts `DOCS.md` er skrevet til Mac og Linux. På Windows bruges `\` i stier og `.venv\Scripts\` i stedet for `.venv/bin/`.

## Deployment

Prototyperne er ikke deployet endnu. De kan køre på DigitalOcean på samme måde som Hold A (Gunicorn som systemd-service pr. projekt med skabelonen `gunicorn@.service`).
Brug fx portene `:8101` til `:8112`, så de ikke kolliderer med Hold A's `:8001` til `:8011`.
