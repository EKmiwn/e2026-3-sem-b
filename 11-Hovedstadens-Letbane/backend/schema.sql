-- Hovedstadens Letbane – rejseassistent (PendlerKids)
-- Navne og typer følger data dictionary i kravspec.md afsnit 5: snake_case uden æ/ø/å, string-id'er, ISO 8601 med tidszone

CREATE TABLE station (
    station_id       TEXT PRIMARY KEY CHECK (length(station_id) = 3),
    navn             TEXT NOT NULL,
    kommune          TEXT NOT NULL,
    latitude         REAL NOT NULL,
    longitude        REAL NOT NULL,
    er_skiftestation INTEGER NOT NULL DEFAULT 0 CHECK (er_skiftestation IN (0, 1)),
    har_elevator     INTEGER NOT NULL DEFAULT 1 CHECK (har_elevator IN (0, 1)),
    cykelparkering   INTEGER NOT NULL DEFAULT 1 CHECK (cykelparkering IN (0, 1))
);

CREATE TABLE rute (
    rute_id             TEXT PRIMARY KEY,
    navn                TEXT NOT NULL,
    retning             TEXT NOT NULL CHECK (retning IN ('SYD', 'NORD')),
    start_station_id    TEXT NOT NULL REFERENCES station(station_id),
    slut_station_id     TEXT NOT NULL REFERENCES station(station_id),
    frekvens_min        INTEGER NOT NULL CHECK (frekvens_min BETWEEN 1 AND 60),
    samlet_rejsetid_min INTEGER NOT NULL CHECK (samlet_rejsetid_min > 0)
);

CREATE TABLE rutestop (
    rute_id                  TEXT NOT NULL REFERENCES rute(rute_id),
    station_id               TEXT NOT NULL REFERENCES station(station_id),
    raekkefoelge             INTEGER NOT NULL,
    holdetid_sek             INTEGER NOT NULL CHECK (holdetid_sek BETWEEN 0 AND 300),
    koeretid_fra_forrige_sek INTEGER NOT NULL CHECK (koeretid_fra_forrige_sek >= 0),
    PRIMARY KEY (rute_id, raekkefoelge)
);

CREATE TABLE skinnestraekning (
    straekning_id         TEXT PRIMARY KEY,
    fra_station_id        TEXT NOT NULL REFERENCES station(station_id),
    til_station_id        TEXT NOT NULL REFERENCES station(station_id),
    laengde_m             INTEGER NOT NULL CHECK (laengde_m > 0),
    planlagt_koeretid_sek INTEGER NOT NULL CHECK (planlagt_koeretid_sek > 0),
    status                TEXT NOT NULL DEFAULT 'AABEN' CHECK (status IN ('AABEN', 'SPORARBEJDE', 'LUKKET'))
);

CREATE TABLE koeretoej (
    koeretoej_id TEXT PRIMARY KEY,
    kapacitet    INTEGER NOT NULL CHECK (kapacitet > 0),
    cykelpladser INTEGER DEFAULT 0 CHECK (cykelpladser >= 0)
);

-- Afgange og stoptider for driftsdøgnet oprettes af backenden ud fra køreplanen (rute + rutestop)
CREATE TABLE afgang (
    afgang_id       TEXT PRIMARY KEY,
    rute_id         TEXT NOT NULL REFERENCES rute(rute_id),
    koeretoej_id    TEXT REFERENCES koeretoej(koeretoej_id),
    dato            TEXT NOT NULL,
    planlagt_afgang TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PLANLAGT'
                    CHECK (status IN ('PLANLAGT', 'I_DRIFT', 'FORSINKET', 'AFLYST', 'DELVIST_AFLYST', 'GENNEMFOERT'))
);

CREATE TABLE stoptid (
    afgang_id         TEXT NOT NULL REFERENCES afgang(afgang_id) ON DELETE CASCADE,
    station_id        TEXT NOT NULL REFERENCES station(station_id),
    raekkefoelge      INTEGER NOT NULL,
    planlagt_ankomst  TEXT NOT NULL,
    forventet_ankomst TEXT,
    faktisk_ankomst   TEXT,
    forsinkelse_min   INTEGER NOT NULL DEFAULT 0,
    er_aflyst         INTEGER NOT NULL DEFAULT 0 CHECK (er_aflyst IN (0, 1)),
    PRIMARY KEY (afgang_id, station_id)
);

CREATE TABLE personale (
    personale_id TEXT PRIMARY KEY CHECK (personale_id GLOB 'P-[0-9][0-9][0-9]'),
    rolle        TEXT NOT NULL CHECK (rolle IN ('TOGFOERER', 'TRAFIKLEDER', 'KUNDESERVICE', 'TEKNIKER')),
    navn         TEXT NOT NULL                        -- persondata – kun intern visning (D-4)
);

CREATE TABLE vagt (
    vagt_id      TEXT PRIMARY KEY,
    personale_id TEXT NOT NULL REFERENCES personale(personale_id),
    afgang_id    TEXT,
    start_tid    TEXT NOT NULL,
    slut_tid     TEXT NOT NULL
);

CREATE TABLE driftsmeddelelse (
    meddelelse_id      TEXT PRIMARY KEY,
    type               TEXT NOT NULL CHECK (type IN ('FORSINKELSE', 'AFLYSNING', 'SPORARBEJDE', 'TEKNISK_FEJL', 'ANDET')),
    alvorlighed        TEXT NOT NULL CHECK (alvorlighed IN ('INFO', 'ADVARSEL', 'KRITISK')),
    titel_da           TEXT NOT NULL CHECK (length(titel_da) BETWEEN 1 AND 80),
    tekst_da           TEXT NOT NULL CHECK (length(tekst_da) BETWEEN 1 AND 500),
    titel_en           TEXT,
    tekst_en           TEXT,
    start_tid          TEXT NOT NULL,
    forventet_slut_tid TEXT,
    alternativ_rejse   TEXT CHECK (alternativ_rejse IS NULL OR length(alternativ_rejse) <= 300),
    oprettet_af        TEXT NOT NULL REFERENCES personale(personale_id)
);

-- N : M – Driftsmeddelelse berører Station / Afgang (beroerte_stationer og beroerte_afgange i JSON)
CREATE TABLE driftsmeddelelse_station (
    meddelelse_id TEXT NOT NULL REFERENCES driftsmeddelelse(meddelelse_id) ON DELETE CASCADE,
    station_id    TEXT NOT NULL REFERENCES station(station_id),
    PRIMARY KEY (meddelelse_id, station_id)
);

CREATE TABLE driftsmeddelelse_afgang (
    meddelelse_id TEXT NOT NULL REFERENCES driftsmeddelelse(meddelelse_id) ON DELETE CASCADE,
    afgang_id     TEXT NOT NULL,
    PRIMARY KEY (meddelelse_id, afgang_id)
);

CREATE TABLE transportmiddel (
    transportmiddel_id TEXT PRIMARY KEY,
    type               TEXT NOT NULL CHECK (type IN ('S_TOG', 'REGIONALTOG', 'BUS', 'METRO')),
    linje              TEXT NOT NULL,
    operatoer          TEXT NOT NULL
);

CREATE TABLE skifteforbindelse (
    skifte_id          TEXT PRIMARY KEY,
    station_id         TEXT NOT NULL REFERENCES station(station_id),
    transportmiddel_id TEXT NOT NULL REFERENCES transportmiddel(transportmiddel_id),
    gangtid_min        INTEGER NOT NULL CHECK (gangtid_min BETWEEN 0 AND 20),
    beskrivelse        TEXT
);

-- Anonym bruger – ingen navn eller e-mail (D-3)
CREATE TABLE bruger (
    bruger_id          TEXT PRIMARY KEY,
    sprog              TEXT NOT NULL DEFAULT 'da' CHECK (sprog IN ('da', 'en')),
    stor_tekst         INTEGER NOT NULL DEFAULT 0 CHECK (stor_tekst IN (0, 1)),
    notifikationer_til INTEGER NOT NULL DEFAULT 0 CHECK (notifikationer_til IN (0, 1)),
    rejsekredit_kr     INTEGER NOT NULL DEFAULT 0 CHECK (rejsekredit_kr >= 0),      -- fra indløste belønninger
    gratis_billetter   INTEGER NOT NULL DEFAULT 0 CHECK (gratis_billetter >= 0),    -- fra indløste belønninger
    oprettet           TEXT NOT NULL
);

CREATE TABLE favoritrejse (
    favorit_id     TEXT PRIMARY KEY,
    bruger_id      TEXT NOT NULL REFERENCES bruger(bruger_id) ON DELETE CASCADE,
    fra_station_id TEXT NOT NULL REFERENCES station(station_id),
    til_station_id TEXT NOT NULL REFERENCES station(station_id),
    navn           TEXT CHECK (navn IS NULL OR length(navn) <= 30),
    saedvanlig_tid TEXT                            -- HH:MM (i data dictionary skrevet "sædvanlig_tid", jf. navnekonvention 5.7)
);

CREATE TABLE feedback (
    feedback_id TEXT PRIMARY KEY,
    bruger_id   TEXT REFERENCES bruger(bruger_id) ON DELETE SET NULL,
    afgang_id   TEXT,
    vurdering   INTEGER NOT NULL CHECK (vurdering BETWEEN 1 AND 5),
    kategori    TEXT NOT NULL CHECK (kategori IN ('PUNKTLIGHED', 'INFORMATION', 'PLADS', 'SKIFT', 'ANDET')),
    kommentar   TEXT CHECK (kommentar IS NULL OR length(kommentar) <= 300),
    tidspunkt   TEXT NOT NULL
);

-- Billet købt i appen (betalingen er simuleret). Status beregnes: BRUGT, hvis brugt_tid er sat – UDLOEBET efter gyldig_til
CREATE TABLE billet (
    billet_id       TEXT PRIMARY KEY,
    bruger_id       TEXT NOT NULL REFERENCES bruger(bruger_id) ON DELETE CASCADE,
    fra_station_id  TEXT NOT NULL REFERENCES station(station_id),
    til_station_id  TEXT NOT NULL REFERENCES station(station_id),
    afgang_id       TEXT,                           -- den planlagte afgang – bruges til at følge letbanen live
    billettype      TEXT NOT NULL CHECK (billettype IN ('VOKSEN', 'BARN')),
    antal           INTEGER NOT NULL CHECK (antal BETWEEN 1 AND 9),
    zoner           INTEGER NOT NULL CHECK (zoner >= 2),
    pris_kr         INTEGER NOT NULL CHECK (pris_kr >= 0),
    betalingsmetode TEXT NOT NULL CHECK (betalingsmetode IN ('KORT', 'MOBILEPAY', 'REJSEKREDIT', 'GRATIS_BILLET')),
    kontrolkode     TEXT NOT NULL,
    koebt_tid       TEXT NOT NULL,
    gyldig_til      TEXT NOT NULL,
    brugt_tid       TEXT                            -- sættes, når rejsen afsluttes og giver point
);

-- Belønninger, som point kan bruges på
CREATE TABLE beloenning (
    beloenning_id  TEXT PRIMARY KEY,
    type           TEXT NOT NULL CHECK (type IN ('GRATIS_BILLET', 'REJSEKREDIT', 'STOR')),
    navn_da        TEXT NOT NULL,
    navn_en        TEXT NOT NULL,
    beskrivelse_da TEXT NOT NULL,
    beskrivelse_en TEXT NOT NULL,
    pris_point     INTEGER NOT NULL CHECK (pris_point > 0),
    vaerdi_kr      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE indloesning (
    indloesning_id TEXT PRIMARY KEY,
    bruger_id      TEXT NOT NULL REFERENCES bruger(bruger_id) ON DELETE CASCADE,
    beloenning_id  TEXT NOT NULL REFERENCES beloenning(beloenning_id),
    kode           TEXT,                            -- kun for belønninger, der vises frem (type STOR)
    tidspunkt      TEXT NOT NULL
);

-- Optjente (+) og brugte (–) point. Brugerens saldo er summen
CREATE TABLE point_transaktion (
    transaktion_id TEXT PRIMARY KEY,
    bruger_id      TEXT NOT NULL REFERENCES bruger(bruger_id) ON DELETE CASCADE,
    point          INTEGER NOT NULL,
    type           TEXT NOT NULL CHECK (type IN ('REJSE', 'INDLOESNING')),
    billet_id      TEXT REFERENCES billet(billet_id) ON DELETE SET NULL,
    indloesning_id TEXT REFERENCES indloesning(indloesning_id) ON DELETE SET NULL,
    tidspunkt      TEXT NOT NULL
);
