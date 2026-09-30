-- Clever – ladeappen: realtidsstatus, pris før start, live opladning, grøn status og fejlrapporter

-- Ladeoperatør. Clever selv eller roaming-partner
CREATE TABLE operator (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL UNIQUE,
    is_clever INTEGER NOT NULL DEFAULT 0 CHECK (is_clever IN (0, 1))
);

CREATE TABLE tariff (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    price_per_kwh REAL NOT NULL CHECK (price_per_kwh > 0),
    start_fee     REAL NOT NULL DEFAULT 0,
    minute_price  REAL NOT NULL DEFAULT 0,
    valid_from    TEXT NOT NULL
);

CREATE TABLE location (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id   INTEGER NOT NULL REFERENCES operator(id),
    name          TEXT NOT NULL,
    address       TEXT NOT NULL,
    city          TEXT NOT NULL,
    country       TEXT NOT NULL CHECK (country IN ('DK', 'SE', 'NO', 'DE')),
    price_area    TEXT CHECK (price_area IN ('DK1', 'DK2')),     -- bruges til grøn status (kun DK)
    lat           REAL NOT NULL,
    lng           REAL NOT NULL,
    opening_hours TEXT NOT NULL DEFAULT 'Døgnåben'
);

-- Stander med stander-ID, som også står i QR-koden (FR-4)
CREATE TABLE charger (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id  INTEGER NOT NULL REFERENCES location(id) ON DELETE CASCADE,
    code         TEXT NOT NULL UNIQUE,
    model        TEXT NOT NULL,
    max_power_kw REAL NOT NULL CHECK (max_power_kw > 0)
);

-- Udtag med realtidsstatus (FR-1) og tarif
CREATE TABLE connector (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    charger_id INTEGER NOT NULL REFERENCES charger(id) ON DELETE CASCADE,
    plug_type  TEXT NOT NULL CHECK (plug_type IN ('CCS', 'TYPE2', 'CHADEMO')),
    status     TEXT NOT NULL DEFAULT 'LEDIG' CHECK (status IN ('LEDIG', 'OPTAGET', 'UDE_AF_DRIFT')),
    tariff_id  INTEGER NOT NULL REFERENCES tariff(id),
    updated_at TEXT NOT NULL
);

-- Appbruger. filters gemmer valgte filtre mellem sessioner (FR-16)
CREATE TABLE app_user (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    language       TEXT NOT NULL DEFAULT 'da' CHECK (language IN ('da', 'en', 'sv', 'no')),
    notify_faults  INTEGER NOT NULL DEFAULT 1 CHECK (notify_faults IN (0, 1)),
    notify_prices  INTEGER NOT NULL DEFAULT 1 CHECK (notify_prices IN (0, 1)),
    card_valid     INTEGER NOT NULL DEFAULT 1 CHECK (card_valid IN (0, 1)),   -- simulerer fejlet betaling
    filters        TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE car (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    model        TEXT NOT NULL,
    plug_type    TEXT NOT NULL CHECK (plug_type IN ('CCS', 'TYPE2', 'CHADEMO')),
    max_power_kw REAL NOT NULL,
    battery_kwh  REAL NOT NULL,
    range_km     INTEGER NOT NULL
);

CREATE TABLE subscription (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL UNIQUE REFERENCES app_user(id) ON DELETE CASCADE,
    type          TEXT NOT NULL CHECK (type IN ('CLEVER_ONE', 'CLEVER_BOX', 'INGEN')),
    monthly_price REAL NOT NULL DEFAULT 0,
    start_date    TEXT NOT NULL
);

-- Strømmix pr. time og prisområde (Energinet Energi Data Service – her en simuleret døgnprofil)
CREATE TABLE energy_mix (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    hour           INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    price_area     TEXT NOT NULL CHECK (price_area IN ('DK1', 'DK2')),
    renewable_pct  INTEGER NOT NULL CHECK (renewable_pct BETWEEN 0 AND 100),
    gco2_per_kwh   INTEGER NOT NULL,
    source         TEXT NOT NULL,
    UNIQUE (hour, price_area)
);

-- Opladning. Pris og strømmix låses ved start, så kvitteringen svarer til det viste
CREATE TABLE session (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES app_user(id),
    connector_id      INTEGER NOT NULL REFERENCES connector(id),
    car_id            INTEGER NOT NULL REFERENCES car(id),
    start_method      TEXT NOT NULL CHECK (start_method IN ('AUTO', 'QR', 'ID')),
    price_per_kwh     REAL NOT NULL,
    start_fee         REAL NOT NULL,
    minute_price      REAL NOT NULL,
    battery_start_pct INTEGER NOT NULL,
    renewable_pct     INTEGER,
    gco2_per_kwh      INTEGER,
    status            TEXT NOT NULL DEFAULT 'AKTIV' CHECK (status IN ('AKTIV', 'AFSLUTTET')),
    started_at        TEXT NOT NULL,
    ended_at          TEXT,
    minutes           REAL,
    kwh               REAL,
    avg_power_kw      REAL,
    price_total       REAL
);

CREATE TABLE payment (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL UNIQUE REFERENCES session(id),
    amount     REAL NOT NULL,
    method     TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('GENNEMFØRT', 'FEJLET')),
    receipt_no TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE favorite (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES location(id) ON DELETE CASCADE,
    label       TEXT NOT NULL,
    UNIQUE (user_id, location_id)
);

CREATE TABLE fault_report (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES app_user(id),
    charger_id  INTEGER NOT NULL REFERENCES charger(id),
    category    TEXT NOT NULL CHECK (category IN ('STARTER_IKKE', 'FORKERT_STATUS', 'STIK_BESKADIGET', 'BETALING', 'ANDET')),
    description TEXT,
    photo       TEXT,
    status      TEXT NOT NULL DEFAULT 'MODTAGET' CHECK (status IN ('MODTAGET', 'UNDER_BEHANDLING', 'LØST')),
    created_at  TEXT NOT NULL,
    updated_at  TEXT
);

-- Push-advarsler (FR-10, FR-11)
CREATE TABLE alert (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    type       TEXT NOT NULL CHECK (type IN ('FAVORIT_UDE_AF_DRIFT', 'HØJ_PRIS', 'SAG_OPDATERET')),
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
