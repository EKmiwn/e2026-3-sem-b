-- Fotohuset Click – bestillingsplatform for billedprint

-- DPI-tærskel, opbevaringsperiode og fragt kan ændres uden kodeændring (§14)
CREATE TABLE setting (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL UNIQUE,
    value       REAL NOT NULL,
    description TEXT
);

-- Produkt = størrelse + overflade + kvalitet (D3). Mål i millimeter internt (§16)
CREATE TABLE product (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    label         TEXT NOT NULL,
    width_mm      INTEGER NOT NULL CHECK (width_mm BETWEEN 89 AND 305),
    height_mm     INTEGER NOT NULL CHECK (height_mm BETWEEN 127 AND 1219),
    roll_width_mm INTEGER NOT NULL CHECK (roll_width_mm IN (102, 127, 152, 203, 210, 254, 305)),
    surface       TEXT NOT NULL CHECK (surface IN ('BLANK', 'SILKE')),
    quality       TEXT NOT NULL CHECK (quality IN ('STANDARD', 'HØJ')),
    price         REAL NOT NULL CHECK (price > 0),
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    UNIQUE (width_mm, height_mm, surface, quality)
);

CREATE TABLE customer (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    phone      TEXT NOT NULL,
    address    TEXT,
    created_at TEXT NOT NULL
);

-- Operatør i butikken. Operatørfladen kræver login (§15)
CREATE TABLE operator (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    pin  TEXT NOT NULL
);

-- Ordre (D1). access_key giver kunden adgang til sin ordre og sine billeder (§15)
CREATE TABLE photo_order (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    access_key     TEXT NOT NULL UNIQUE,
    customer_id    INTEGER REFERENCES customer(id),
    status         TEXT NOT NULL DEFAULT 'KURV'
                   CHECK (status IN ('KURV', 'MODTAGET', 'I_PRODUKTION', 'KLAR', 'AFHENTET')),
    delivery       TEXT CHECK (delivery IN ('AFHENTNING', 'FORSENDELSE')),
    payment_status TEXT NOT NULL DEFAULT 'IKKE_BETALT'
                   CHECK (payment_status IN ('IKKE_BETALT', 'AFVENTER', 'BETALT', 'AFVIST')),
    payment_ref    TEXT,
    consent_at     TEXT,
    total          REAL NOT NULL DEFAULT 0,
    note           TEXT,
    created_at     TEXT NOT NULL,
    received_at    TEXT,
    desired_ready  TEXT,
    notified_at    TEXT,
    closed_at      TEXT
);

-- Billedfil med metadata (D2). Prototypen gemmer en miniature i stedet for selve filen
CREATE TABLE image (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES photo_order(id) ON DELETE CASCADE,
    filename    TEXT NOT NULL,
    file_type   TEXT NOT NULL CHECK (file_type IN ('JPEG', 'PNG', 'TIFF')),
    px_width    INTEGER NOT NULL CHECK (px_width > 0),
    px_height   INTEGER NOT NULL CHECK (px_height > 0),
    file_size   INTEGER NOT NULL CHECK (file_size > 0),
    orientation TEXT NOT NULL CHECK (orientation IN ('LIGGENDE', 'STÅENDE', 'KVADRATISK')),
    thumbnail   TEXT,
    uploaded_at TEXT NOT NULL,
    deleted_at  TEXT
);

-- Ét billede i ét format i ét antal
CREATE TABLE order_line (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id         INTEGER NOT NULL REFERENCES photo_order(id) ON DELETE CASCADE,
    image_id         INTEGER NOT NULL REFERENCES image(id) ON DELETE CASCADE,
    product_id       INTEGER NOT NULL REFERENCES product(id),
    quantity         INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 999),
    crop             TEXT NOT NULL DEFAULT 'FYLD' CHECK (crop IN ('FYLD', 'TILPAS_MED_KANT', 'HELT_TIL_KANT')),
    rotation         INTEGER NOT NULL DEFAULT 0 CHECK (rotation IN (0, 90, 180, 270)),
    color_correction INTEGER NOT NULL DEFAULT 1 CHECK (color_correction IN (0, 1)),
    effective_dpi    INTEGER NOT NULL,
    dpi_warning      INTEGER NOT NULL DEFAULT 0 CHECK (dpi_warning IN (0, 1)),
    line_price       REAL NOT NULL
);

-- Printjob afleveret til C8 (1:1 med ordren)
CREATE TABLE print_job (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL UNIQUE REFERENCES photo_order(id) ON DELETE CASCADE,
    operator_id INTEGER NOT NULL REFERENCES operator(id),
    payload     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
