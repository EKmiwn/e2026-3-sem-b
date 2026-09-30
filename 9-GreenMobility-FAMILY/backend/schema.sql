-- GreenMobility FAMILY – familieabonnement, booking, datadrevet flådestyring og partnerfordele

CREATE TABLE plan (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL UNIQUE,
    monthly_price  REAL NOT NULL CHECK (monthly_price > 0),
    included_hours INTEGER NOT NULL CHECK (included_hours >= 0),
    discount_pct   INTEGER NOT NULL DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 100),
    max_members    INTEGER NOT NULL DEFAULT 4,
    description    TEXT NOT NULL
);

CREATE TABLE zone (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE car_type (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL UNIQUE,
    seats          INTEGER NOT NULL,
    child_seat     INTEGER NOT NULL DEFAULT 0 CHECK (child_seat IN (0, 1)),
    price_per_min  REAL NOT NULL CHECK (price_per_min > 0)
);

CREATE TABLE car (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plate       TEXT NOT NULL UNIQUE,
    car_type_id INTEGER NOT NULL REFERENCES car_type(id),
    zone_id     INTEGER NOT NULL REFERENCES zone(id),
    battery_pct INTEGER NOT NULL DEFAULT 80 CHECK (battery_pct BETWEEN 0 AND 100),
    status      TEXT NOT NULL DEFAULT 'KLAR' CHECK (status IN ('KLAR', 'SERVICE'))
);

-- Familiens medlemskab. Aktivt først, når betalingen er valideret
CREATE TABLE family (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    plan_id      INTEGER NOT NULL REFERENCES plan(id),
    status       TEXT NOT NULL CHECK (status IN ('AKTIV', 'OPSAGT')),
    card_last4   TEXT NOT NULL,
    payment_ref  TEXT NOT NULL,
    home_zone_id INTEGER REFERENCES zone(id),
    created_at   TEXT NOT NULL
);

CREATE TABLE member (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER NOT NULL REFERENCES family(id) ON DELETE CASCADE,
    name      TEXT NOT NULL,
    email     TEXT,
    is_driver INTEGER NOT NULL DEFAULT 0 CHECK (is_driver IN (0, 1))   -- voksen med kørekort
);

CREATE TABLE reservation (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id  INTEGER NOT NULL REFERENCES family(id),
    member_id  INTEGER NOT NULL REFERENCES member(id),
    car_id     INTEGER NOT NULL REFERENCES car(id),
    start_at   TEXT NOT NULL,
    end_at     TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'BEKRÆFTET' CHECK (status IN ('BEKRÆFTET', 'AFSLUTTET', 'ANNULLERET')),
    created_at TEXT NOT NULL
);

-- Turdata efter kørslen – grundlaget for forecast og flådeplanlægning
CREATE TABLE trip (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER REFERENCES reservation(id),        -- NULL for historiske ture
    family_id      INTEGER NOT NULL REFERENCES family(id),
    car_type_id    INTEGER NOT NULL REFERENCES car_type(id),
    zone_id        INTEGER NOT NULL REFERENCES zone(id),
    end_zone_id    INTEGER NOT NULL REFERENCES zone(id),
    started_at     TEXT NOT NULL,
    minutes        INTEGER NOT NULL CHECK (minutes > 0),
    km             REAL NOT NULL CHECK (km >= 0),
    included_min   INTEGER NOT NULL DEFAULT 0,
    price          REAL NOT NULL DEFAULT 0,
    credits_used   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE partner (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT NOT NULL UNIQUE,
    category             TEXT NOT NULL,
    benefit              TEXT NOT NULL,
    credits_per_activity INTEGER NOT NULL CHECK (credits_per_activity > 0)
);

-- GreenCredits: + ved partneraktivitet, − når de bruges på en tur
CREATE TABLE credit_transaction (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id   INTEGER NOT NULL REFERENCES family(id) ON DELETE CASCADE,
    partner_id  INTEGER REFERENCES partner(id),
    trip_id     INTEGER REFERENCES trip(id),
    amount      INTEGER NOT NULL,
    description TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

-- Operations' flytning af biler efter forecast
CREATE TABLE relocation (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id       INTEGER NOT NULL REFERENCES car(id),
    from_zone_id INTEGER NOT NULL REFERENCES zone(id),
    to_zone_id   INTEGER NOT NULL REFERENCES zone(id),
    reason       TEXT,
    created_at   TEXT NOT NULL
);
