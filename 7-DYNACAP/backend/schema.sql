-- DYNACAP Academy – oplæringsstruktur i seks niveauer

CREATE TABLE office (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL CHECK (country IN ('DK', 'NO'))
);

-- Alle brugere. Rollen styrer adgangen (afsnit 15). mentor_id og start_date bruges kun for konsulenter
CREATE TABLE person (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    role       TEXT NOT NULL CHECK (role IN ('KONSULENT', 'VEJLEDER', 'HR', 'LEDELSE')),
    office_id  INTEGER NOT NULL REFERENCES office(id),
    language   TEXT NOT NULL DEFAULT 'da' CHECK (language IN ('da', 'en')),
    mentor_id  INTEGER REFERENCES person(id),
    start_date TEXT
);

-- De seks niveauer. Samme indhold på alle kontorer (F6), på dansk og engelsk (afsnit 16)
CREATE TABLE level (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    number             INTEGER NOT NULL UNIQUE CHECK (number BETWEEN 1 AND 6),
    title_da           TEXT NOT NULL,
    title_en           TEXT NOT NULL,
    goal_da            TEXT NOT NULL,
    goal_en            TEXT NOT NULL,
    learning_form      TEXT NOT NULL,
    estimate_weeks_min INTEGER NOT NULL,
    estimate_weeks_max INTEGER NOT NULL,
    requires_certification TEXT                   -- fx 'Salesforce Administrator' på niveau 5
);

CREATE TABLE activity (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    level_id INTEGER NOT NULL REFERENCES level(id) ON DELETE CASCADE,
    title_da TEXT NOT NULL,
    title_en TEXT NOT NULL,
    type     TEXT NOT NULL CHECK (type IN ('INTRO', 'TRAILHEAD', 'ØVELSE', 'CASE', 'PROJEKT', 'SAMTALE')),
    link     TEXT,
    sort     INTEGER NOT NULL DEFAULT 0
);

-- Oplæringsforløb pr. konsulent (F1)
CREATE TABLE programme (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    consultant_id INTEGER NOT NULL UNIQUE REFERENCES person(id) ON DELETE CASCADE,
    created_by    INTEGER NOT NULL REFERENCES person(id),
    created_at    TEXT NOT NULL
);

CREATE TABLE activity_completion (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    consultant_id INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    activity_id   INTEGER NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
    completed_at  TEXT NOT NULL,
    UNIQUE (consultant_id, activity_id)
);

-- Niveaugodkendelse: vejlederens vurdering med dato og kommentar (F4). Historikken bevares
CREATE TABLE level_review (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    consultant_id INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    level_id      INTEGER NOT NULL REFERENCES level(id),
    mentor_id     INTEGER NOT NULL REFERENCES person(id),
    decision      TEXT NOT NULL CHECK (decision IN ('GODKENDT', 'AFVIST')),
    comment       TEXT,
    reviewed_at   TEXT NOT NULL
);

CREATE TABLE certification (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    consultant_id INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    passed_at     TEXT NOT NULL,
    registered_by INTEGER NOT NULL REFERENCES person(id)
);

-- Statusrapporter sendt til ledelsen (F7)
CREATE TABLE status_report (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sent_at    TEXT NOT NULL,
    sent_to    TEXT NOT NULL,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('AUTOMATISK', 'MANUEL')),
    summary    TEXT NOT NULL
);
