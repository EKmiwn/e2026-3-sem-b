-- Elevevaluering (Læringsrum 2.0) – elever vurderer trivsel, læring og møbler

-- Skole (virksomhed/skole-information)
CREATE TABLE school (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL
);

CREATE TABLE class (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER NOT NULL REFERENCES school(id) ON DELETE CASCADE,
    name      TEXT NOT NULL,
    grade     INTEGER NOT NULL CHECK (grade BETWEEN 0 AND 10),     -- klassetrin
    UNIQUE (school_id, name)
);

-- Alle brugere. Rollen styrer brugerrettigheder: elev, lærer eller administrator (Læringsrum 2.0)
CREATE TABLE app_user (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    role     TEXT NOT NULL CHECK (role IN ('ELEV', 'LÆRER', 'ADMINISTRATOR')),
    class_id INTEGER REFERENCES class(id),                            -- elevens klasse / lærerens klasse
    school_id INTEGER REFERENCES school(id)
);

CREATE TABLE question (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    text     TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('TRIVSEL', 'LÆRING', 'MØBLER', 'MILJØ')),
    emoji    TEXT,
    active   INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    sort     INTEGER NOT NULL DEFAULT 0
);

-- Måling: en runde, hvor klasserne besvarer spørgsmålene (fx hver måned), så svar kan sammenlignes over tid
CREATE TABLE survey_round (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    opens_on  TEXT NOT NULL,
    closes_on TEXT NOT NULL
);

-- Elev → Besvarelse → Spørgsmål → Resultat (ER-diagrammet i kravspecifikationen)
CREATE TABLE response (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    round_id    INTEGER NOT NULL REFERENCES survey_round(id),
    comment     TEXT,
    submitted_at TEXT NOT NULL,
    UNIQUE (student_id, round_id)
);

CREATE TABLE answer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id INTEGER NOT NULL REFERENCES response(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES question(id),
    value       INTEGER NOT NULL CHECK (value BETWEEN 1 AND 5),
    UNIQUE (response_id, question_id)
);

-- Lærerens opfølgning, så eleverne kan se, at deres svar bliver taget alvorligt
CREATE TABLE follow_up (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id   INTEGER NOT NULL REFERENCES class(id) ON DELETE CASCADE,
    teacher_id INTEGER NOT NULL REFERENCES app_user(id),
    category   TEXT NOT NULL,
    text       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
