-- Bispebjerg Akutmodtagelse – digital patientregistrering

-- Afdeling, der modtager bestilte undersøgelser (FR6)
CREATE TABLE department (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Personale. Den valgte medarbejder sendes i headeren X-User-Id (simuleret login).
-- Rollen AFDELING er personale på en modtagende afdeling og ser kun afdelingens egne bestillinger.
CREATE TABLE staff (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('SYGEPLEJERSKE', 'LÆGE', 'AFDELING')),
    department_id INTEGER REFERENCES department(id)
);

-- Undersøgelser, personalet kan markere behov for (FR7)
CREATE TABLE exam_type (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    department_id INTEGER NOT NULL REFERENCES department(id)
);

-- Patientens registrering af symptomer og helbredsoplysninger (FR1, FR2, FR8, FR9)
CREATE TABLE registration (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    reg_number         TEXT NOT NULL UNIQUE,                 -- unikt registreringsnummer, fx BBH-4821
    name               TEXT NOT NULL,
    birth_date         TEXT NOT NULL,                        -- bruges sammen med nummeret, når patienten slår sig selv op
    language           TEXT NOT NULL DEFAULT 'da' CHECK (language IN ('da', 'en')),
    symptoms           TEXT NOT NULL,
    injury_type        TEXT NOT NULL CHECK (injury_type IN ('SYGDOM', 'FALD', 'BRUD', 'FORSTUVNING', 'SÅR', 'FORBRÆNDING', 'HOVEDSKADE', 'ANDET')),
    pain_level         INTEGER NOT NULL CHECK (pain_level BETWEEN 0 AND 10),
    medication         TEXT NOT NULL DEFAULT '',
    allergies          TEXT NOT NULL DEFAULT '',
    registered_from    TEXT NOT NULL CHECK (registered_from IN ('HJEMMEFRA', 'VED_ANKOMST')),
    fill_seconds       INTEGER,                              -- tid brugt på at udfylde (krav: højst 5 minutter)
    status             TEXT NOT NULL CHECK (status IN ('REGISTRERET', 'VENTER_PÅ_SYGEPLEJERSKE', 'UNDERSØGELSE_BESTILT', 'VENTER_PÅ_LÆGE', 'AFSLUTTET')),
    triage_level       TEXT CHECK (triage_level IN ('RØD', 'ORANGE', 'GUL', 'GRØN', 'BLÅ')),   -- sættes altid af personalet
    triage_note        TEXT,
    triaged_by         INTEGER REFERENCES staff(id),
    triaged_at         TEXT,
    created_at         TEXT NOT NULL,
    arrived_at         TEXT,
    patient_updated_at TEXT,
    closed_at          TEXT
);

-- Statushistorik, så patient og personale kan følge forløbet (FR9)
CREATE TABLE status_event (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id INTEGER NOT NULL REFERENCES registration(id) ON DELETE CASCADE,
    status          TEXT NOT NULL,
    staff_id        INTEGER REFERENCES staff(id),            -- NULL = patienten selv
    created_at      TEXT NOT NULL
);

-- Bestilt undersøgelse, sendt videre til den relevante afdeling (FR6, FR7)
CREATE TABLE examination (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id INTEGER NOT NULL REFERENCES registration(id) ON DELETE CASCADE,
    exam_type_id    INTEGER NOT NULL REFERENCES exam_type(id),
    ordered_by      INTEGER NOT NULL REFERENCES staff(id),
    status          TEXT NOT NULL DEFAULT 'BESTILT' CHECK (status IN ('BESTILT', 'UDFØRT')),
    ordered_at      TEXT NOT NULL,
    completed_by    INTEGER REFERENCES staff(id),
    completed_at    TEXT
);

-- Logning af personalets adgang til og ændringer i patientdata (afsnit 14 og 15)
CREATE TABLE access_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id        INTEGER NOT NULL REFERENCES staff(id),
    registration_id INTEGER NOT NULL REFERENCES registration(id) ON DELETE CASCADE,
    action          TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
