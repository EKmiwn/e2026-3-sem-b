-- Movia – Den Forudsigelige Rejse

CREATE TABLE stop (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- S-buslinje med fast rækkefølge af stoppesteder
CREATE TABLE line (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE line_stop (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id      INTEGER NOT NULL REFERENCES line(id) ON DELETE CASCADE,
    stop_id      INTEGER NOT NULL REFERENCES stop(id),
    seq          INTEGER NOT NULL,
    minutes_from_start INTEGER NOT NULL,
    UNIQUE (line_id, seq)
);

-- Bus med sensorer. quiet_zone = fysisk rolig zone (FR8)
CREATE TABLE bus (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    number     TEXT NOT NULL UNIQUE,
    line_id    INTEGER NOT NULL REFERENCES line(id),
    quiet_zone TEXT NOT NULL DEFAULT 'INGEN' CHECK (quiet_zone IN ('INGEN', 'FORREST', 'BAGERST'))
);

-- Planlagt afgang fra linjens første stop (klokkeslæt HH:MM)
CREATE TABLE departure (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id    INTEGER NOT NULL REFERENCES line(id),
    bus_id     INTEGER NOT NULL REFERENCES bus(id),
    departs_at TEXT NOT NULL
);

-- Støj- og trængselsmåling fra bussens sensorer, pr. område i bussen (P2)
CREATE TABLE sensor_reading (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_id       INTEGER NOT NULL REFERENCES bus(id),
    area         TEXT NOT NULL CHECK (area IN ('FORREST', 'MIDTEN', 'BAGERST')),
    noise_db     REAL NOT NULL CHECK (noise_db BETWEEN 30 AND 100),
    crowding_pct INTEGER NOT NULL CHECK (crowding_pct BETWEEN 0 AND 100),
    measured_at  TEXT NOT NULL
);

-- Den unge passagers profil i appen
CREATE TABLE passenger (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    school            TEXT,
    sunflower_enabled INTEGER NOT NULL DEFAULT 1 CHECK (sunflower_enabled IN (0, 1)),
    notify_stops_before INTEGER NOT NULL DEFAULT 1 CHECK (notify_stops_before BETWEEN 1 AND 3)
);

CREATE TABLE trip (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    passenger_id INTEGER NOT NULL REFERENCES passenger(id),
    departure_id INTEGER NOT NULL REFERENCES departure(id),
    from_stop_id INTEGER NOT NULL REFERENCES stop(id),
    to_stop_id   INTEGER NOT NULL REFERENCES stop(id),
    status       TEXT NOT NULL DEFAULT 'PLANLAGT' CHECK (status IN ('PLANLAGT', 'OMBORD', 'AFSLUTTET')),
    current_seq  INTEGER,
    created_at   TEXT NOT NULL,
    boarded_at   TEXT,
    finished_at  TEXT
);

-- Digitalt solsikkesignal til chaufføren. Indeholder et tilfældigt token – aldrig passagerens navn (NFR2, NFR4)
CREATE TABLE sunflower_signal (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id         INTEGER NOT NULL REFERENCES trip(id) ON DELETE CASCADE,
    bus_id          INTEGER NOT NULL REFERENCES bus(id),
    token           TEXT NOT NULL UNIQUE,
    stop_name       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'SENDT' CHECK (status IN ('SENDT', 'SET_AF_CHAUFFØR', 'AFSLUTTET')),
    sent_at         TEXT NOT NULL,
    acknowledged_at TEXT
);

CREATE TABLE notification (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id    INTEGER NOT NULL REFERENCES trip(id) ON DELETE CASCADE,
    type       TEXT NOT NULL CHECK (type IN ('ROLIG_RUTE', 'SOLSIKKE_SENDT', 'STOP_NÆRMER_SIG', 'STÅ_AF_NU', 'FEEDBACK')),
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id     INTEGER NOT NULL UNIQUE REFERENCES trip(id) ON DELETE CASCADE,
    calm_rating INTEGER NOT NULL CHECK (calm_rating BETWEEN 1 AND 5),
    felt_safe   INTEGER NOT NULL CHECK (felt_safe IN (0, 1)),
    comment     TEXT,
    created_at  TEXT NOT NULL
);
