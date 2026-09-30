-- NORMAL – produkttilgængelighed i butikkerne

-- Grænser for lagerstatus kan justeres uden ny kode
CREATE TABLE setting (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL UNIQUE,
    value       REAL NOT NULL,
    description TEXT
);

CREATE TABLE store (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    city          TEXT NOT NULL,
    address       TEXT NOT NULL,
    opening_hours TEXT NOT NULL DEFAULT 'Man–lør 9–20, søn 10–18',
    employees     INTEGER NOT NULL DEFAULT 0 CHECK (employees >= 0)
);

CREATE TABLE category (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE product (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sku         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    brand       TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES category(id),
    price       REAL NOT NULL CHECK (price >= 0),
    keywords    TEXT
);

-- Lagerstatus pr. produkt pr. butik
CREATE TABLE stock (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id   INTEGER NOT NULL REFERENCES store(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    quantity   INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    updated_at TEXT NOT NULL,
    UNIQUE (store_id, product_id)
);

-- Kundernes søgninger og opslag – grundlag for nøgletal om efterspørgsel
CREATE TABLE search_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    query       TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE lookup_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    store_id   INTEGER NOT NULL REFERENCES store(id) ON DELETE CASCADE,
    status     TEXT NOT NULL CHECK (status IN ('PÅ_LAGER', 'FÅ_TILBAGE', 'UDSOLGT')),
    created_at TEXT NOT NULL
);
