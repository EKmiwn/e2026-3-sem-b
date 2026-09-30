-- &LIVING Buyer Matchmaking – købere slår deres købekraft sammen

-- Vægte og grænser for match er åbne punkter i kravspecifikationen, så de kan justeres som indstillinger
CREATE TABLE setting (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL UNIQUE,
    value       REAL NOT NULL,
    description TEXT
);

CREATE TABLE agent (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT NOT NULL,
    office TEXT NOT NULL
);

-- Køberprofil. consent_at skal være sat, før køberen kan matches (GDPR)
CREATE TABLE buyer (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    email              TEXT NOT NULL UNIQUE,
    phone              TEXT,
    age                INTEGER NOT NULL CHECK (age BETWEEN 18 AND 99),
    budget             INTEGER NOT NULL CHECK (budget > 0),            -- egen andel af maks. pris, DKK
    preapproved_loan   INTEGER NOT NULL DEFAULT 0 CHECK (preapproved_loan >= 0),
    down_payment       INTEGER NOT NULL DEFAULT 0 CHECK (down_payment >= 0),
    preferred_location TEXT NOT NULL,
    property_type      TEXT NOT NULL CHECK (property_type IN ('APARTMENT', 'TOWNHOUSE', 'HOUSE')),
    min_area           INTEGER NOT NULL CHECK (min_area > 0),
    max_transport_min  INTEGER NOT NULL CHECK (max_transport_min > 0),
    pets               INTEGER NOT NULL DEFAULT 0 CHECK (pets IN (0, 1)),
    smoker             INTEGER NOT NULL DEFAULT 0 CHECK (smoker IN (0, 1)),
    has_children       INTEGER NOT NULL DEFAULT 0 CHECK (has_children IN (0, 1)),
    social_level       INTEGER NOT NULL DEFAULT 3 CHECK (social_level BETWEEN 1 AND 5),   -- 1 stille … 5 social
    share_contact      INTEGER NOT NULL DEFAULT 0 CHECK (share_contact IN (0, 1)),
    consent_at         TEXT
);

CREATE TABLE buyer_group (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    agent_id   INTEGER REFERENCES agent(id),
    created_at TEXT NOT NULL
);

-- Medlemshistorik: købere kan tilslutte sig og forlade en gruppe
CREATE TABLE group_member (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id  INTEGER NOT NULL REFERENCES buyer_group(id) ON DELETE CASCADE,
    buyer_id  INTEGER NOT NULL REFERENCES buyer(id),
    joined_at TEXT NOT NULL,
    left_at   TEXT
);

-- &LIVINGs portefølje, inkl. boliger der ikke er offentligt annonceret (skuffesager)
CREATE TABLE property (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    address       TEXT NOT NULL,
    location      TEXT NOT NULL,
    property_type TEXT NOT NULL CHECK (property_type IN ('APARTMENT', 'TOWNHOUSE', 'HOUSE')),
    price         INTEGER NOT NULL CHECK (price > 0),
    area          INTEGER NOT NULL CHECK (area > 0),
    rooms         INTEGER NOT NULL CHECK (rooms > 0),
    transport_min INTEGER NOT NULL CHECK (transport_min >= 0),         -- til centrum
    monthly_cost  INTEGER NOT NULL DEFAULT 0,
    off_market    INTEGER NOT NULL DEFAULT 0 CHECK (off_market IN (0, 1)),
    agent_id      INTEGER REFERENCES agent(id)
);

-- Beskeder i gruppen – kontaktoplysninger deles kun, hvis køberen selv vælger det
CREATE TABLE message (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id   INTEGER NOT NULL REFERENCES buyer_group(id) ON DELETE CASCADE,
    sender_id  INTEGER NOT NULL REFERENCES buyer(id),
    text       TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE shortlist_item (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id    INTEGER NOT NULL REFERENCES buyer_group(id) ON DELETE CASCADE,
    property_id INTEGER NOT NULL REFERENCES property(id),
    added_by    INTEGER NOT NULL REFERENCES buyer(id),
    added_at    TEXT NOT NULL,
    UNIQUE (group_id, property_id)
);

CREATE TABLE vote (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    shortlist_item_id INTEGER NOT NULL REFERENCES shortlist_item(id) ON DELETE CASCADE,
    buyer_id          INTEGER NOT NULL REFERENCES buyer(id),
    value             INTEGER NOT NULL CHECK (value IN (-1, 1)),
    comment           TEXT,
    created_at        TEXT NOT NULL,
    UNIQUE (shortlist_item_id, buyer_id)
);

CREATE TABLE viewing_request (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id       INTEGER NOT NULL REFERENCES buyer_group(id) ON DELETE CASCADE,
    property_id    INTEGER NOT NULL REFERENCES property(id),
    requested_by   INTEGER NOT NULL REFERENCES buyer(id),
    type           TEXT NOT NULL CHECK (type IN ('OPEN_HOUSE', 'PRIVATE')),
    preferred_date TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'REQUESTED' CHECK (status IN ('REQUESTED', 'CONFIRMED', 'DECLINED')),
    agent_note     TEXT,
    created_at     TEXT NOT NULL
);
