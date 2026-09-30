-- Habitus – tale-til-tekst-dokumentation på botilbud

CREATE TABLE department (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    site TEXT NOT NULL
);

-- Medarbejder. Den valgte medarbejder sendes i headeren X-User-Id (simuleret login)
CREATE TABLE staff (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('PÆDAGOG', 'MEDHJÆLPER', 'LEDER')),
    department_id INTEGER NOT NULL REFERENCES department(id)
);

CREATE TABLE resident (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    nickname      TEXT,
    room          TEXT,
    department_id INTEGER NOT NULL REFERENCES department(id)
);

-- Beboerens ordinerede medicin – bruges til at genkende og kontrollere medicin i talen
CREATE TABLE medication (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL REFERENCES resident(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    dose        TEXT NOT NULL,
    is_pn       INTEGER NOT NULL DEFAULT 0 CHECK (is_pn IN (0, 1))   -- PN = efter behov
);

-- Én optagelse: transskription, klassificering og godkendelse
CREATE TABLE recording (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id               INTEGER NOT NULL REFERENCES staff(id),
    resident_id            INTEGER REFERENCES resident(id),        -- bekræftet beboer
    suggested_resident_id  INTEGER REFERENCES resident(id),        -- foreslået ud fra talen
    transcript             TEXT NOT NULL,
    final_text             TEXT,
    category               TEXT NOT NULL CHECK (category IN ('OBSERVATION', 'UDVIKLING', 'MEDICIN')),
    category_confidence    REAL NOT NULL,
    transcript_confidence  REAL NOT NULL,
    contains_medication    INTEGER NOT NULL DEFAULT 0 CHECK (contains_medication IN (0, 1)),
    handover               INTEGER NOT NULL DEFAULT 0 CHECK (handover IN (0, 1)),
    uncertain              TEXT NOT NULL DEFAULT '[]',              -- JSON-liste med markeringer
    requires_approval      INTEGER NOT NULL CHECK (requires_approval IN (0, 1)),
    status                 TEXT NOT NULL CHECK (status IN ('AFVENTER_GODKENDELSE', 'GODKENDT', 'FORKASTET')),
    audio_stored           INTEGER NOT NULL DEFAULT 1 CHECK (audio_stored IN (0, 1)),
    duration_sec           INTEGER,
    recorded_at            TEXT NOT NULL,
    approved_at            TEXT,
    approved_by            INTEGER REFERENCES staff(id)
);

-- Struktureret dokumentationspost i det felt, den hører til i journalsystemet (Sofus) eller Outlook
CREATE TABLE journal_entry (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    recording_id  INTEGER REFERENCES recording(id),
    resident_id   INTEGER NOT NULL REFERENCES resident(id),
    staff_id      INTEGER NOT NULL REFERENCES staff(id),
    target_system TEXT NOT NULL CHECK (target_system IN ('SOFUS', 'OUTLOOK')),
    target_field  TEXT NOT NULL,
    category      TEXT NOT NULL,
    text          TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT,
    updated_by    INTEGER REFERENCES staff(id)
);
