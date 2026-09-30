-- COOP – Grønne Besparelser: digitale gule mærker i Coop-appen

-- SuperBrugsen-butik. closing_time bruges til at fjerne mærker ved lukketid (F4)
CREATE TABLE store (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    city         TEXT NOT NULL,
    closing_time TEXT NOT NULL DEFAULT '21:00'
);

-- Vare fra Coop One (SAP) – slås op på EAN ved scanning
CREATE TABLE product (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ean          TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    category     TEXT NOT NULL,
    normal_price REAL NOT NULL CHECK (normal_price > 0)
);

CREATE TABLE employee (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    store_id INTEGER NOT NULL REFERENCES store(id)
);

-- Kunde i Coop-appen. Notifikationer kræver samtykke (GDPR)
CREATE TABLE customer (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT NOT NULL,
    email                 TEXT NOT NULL UNIQUE,
    store_id              INTEGER REFERENCES store(id),
    notifications_consent INTEGER NOT NULL DEFAULT 0 CHECK (notifications_consent IN (0, 1)),
    consent_at            TEXT
);

-- Gult mærke: nedsat datovare på hylden
CREATE TABLE yellow_label (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id         INTEGER NOT NULL REFERENCES store(id),
    product_id       INTEGER NOT NULL REFERENCES product(id),
    employee_id      INTEGER NOT NULL REFERENCES employee(id),
    old_price        REAL NOT NULL,
    discount_pct     INTEGER NOT NULL CHECK (discount_pct BETWEEN 1 AND 90),
    new_price        REAL NOT NULL,
    expiry_date      TEXT NOT NULL,           -- sidste anvendelsesdato
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    quantity_sold    INTEGER NOT NULL DEFAULT 0 CHECK (quantity_sold >= 0),
    status           TEXT NOT NULL DEFAULT 'AKTIV' CHECK (status IN ('AKTIV', 'UDSOLGT', 'UDLØBET', 'FJERNET')),
    creation_seconds INTEGER,                 -- tid fra scanning til oprettelse (usability-krav)
    created_at       TEXT NOT NULL,
    removed_at       TEXT
);

-- Salg registreret i kassen (Coop One)
CREATE TABLE sale (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    label_id INTEGER NOT NULL REFERENCES yellow_label(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    sold_at  TEXT NOT NULL
);

CREATE TABLE notification (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customer(id) ON DELETE CASCADE,
    label_id    INTEGER NOT NULL REFERENCES yellow_label(id),
    message     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
