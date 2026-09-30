-- Fiktive testdata. Datoer i mærkerne sættes relativt til i dag, så feedet altid har aktive mærker.
INSERT INTO store (name, city, closing_time) VALUES
  ('SuperBrugsen Sorø', 'Sorø', '21:00'),
  ('SuperBrugsen Ringsted', 'Ringsted', '21:00'),
  ('SuperBrugsen Slagelse', 'Slagelse', '20:00'),
  ('SuperBrugsen Holbæk', 'Holbæk', '21:00'),
  ('SuperBrugsen Næstved', 'Næstved', '22:00');

INSERT INTO product (ean, name, category, normal_price) VALUES
  ('5701234000011', 'Hakket oksekød 8-12 % 500 g', 'Kød', 45.95),
  ('5701234000028', 'Kyllingebryst 900 g', 'Kød', 69.95),
  ('5701234000035', 'Laks fersk 250 g', 'Fisk', 49.95),
  ('5701234000042', 'Skyr naturel 1 kg', 'Mejeri', 22.95),
  ('5701234000059', 'Sødmælk 1 l', 'Mejeri', 13.50),
  ('5701234000066', 'Rugbrød grovbolle 1 kg', 'Brød', 24.95),
  ('5701234000073', 'Salatmix 150 g', 'Frugt og grønt', 18.00),
  ('5701234000080', 'Leverpostej 500 g', 'Pålæg', 21.95),
  ('5701234000097', 'Frikadeller 600 g', 'Færdigretter', 39.95),
  ('5701234000103', 'Flødeboller 8 stk.', 'Kage', 29.95);

INSERT INTO employee (name, store_id) VALUES
  ('Søren (butikschef)', 1), ('Hanne', 1), ('Bent', 1), ('Lise', 2), ('Kim', 3);

INSERT INTO customer (name, email, store_id, notifications_consent, consent_at) VALUES
  ('Ingrid', 'ingrid@test.dk', 1, 1, '2026-09-20 18:00:00'),
  ('Peter', 'peter@test.dk', 1, 0, NULL),
  ('Amira', 'amira@test.dk', 2, 1, '2026-09-22 09:30:00');

INSERT INTO yellow_label (store_id, product_id, employee_id, old_price, discount_pct, new_price, expiry_date, quantity,
                          quantity_sold, status, creation_seconds, created_at) VALUES
  (1, 1, 2, 45.95, 40, 27.57, date('now', 'localtime', '+1 day'), 6, 2, 'AKTIV', 14, datetime('now', 'localtime', '-3 hours')),
  (1, 4, 3, 22.95, 50, 11.48, date('now', 'localtime', '+1 day'), 4, 0, 'AKTIV', 11, datetime('now', 'localtime', '-2 hours')),
  (1, 9, 2, 39.95, 30, 27.97, date('now', 'localtime', '+2 days'), 3, 0, 'AKTIV', 18, datetime('now', 'localtime', '-1 hours')),
  (1, 3, 3, 49.95, 50, 24.98, date('now', 'localtime'), 2, 2, 'UDSOLGT', 9, datetime('now', 'localtime', '-5 hours')),
  (1, 7, 2, 18.00, 40, 10.80, date('now', 'localtime', '-1 day'), 5, 3, 'UDLØBET', 16, datetime('now', 'localtime', '-1 day')),
  (2, 2, 4, 69.95, 40, 41.97, date('now', 'localtime', '+1 day'), 5, 1, 'AKTIV', 21, datetime('now', 'localtime', '-2 hours')),
  (3, 6, 5, 24.95, 50, 12.48, date('now', 'localtime', '+1 day'), 8, 0, 'AKTIV', 13, datetime('now', 'localtime', '-4 hours'));

INSERT INTO sale (label_id, quantity, sold_at) VALUES
  (1, 2, datetime('now', 'localtime', '-2 hours')), (4, 2, datetime('now', 'localtime', '-4 hours')),
  (5, 3, datetime('now', 'localtime', '-1 day')), (6, 1, datetime('now', 'localtime', '-1 hours'));

INSERT INTO notification (customer_id, label_id, message, created_at) VALUES
  (1, 2, 'SuperBrugsen Sorø har nedsat Skyr naturel 1 kg til 11,48 kr. (før 22,95 kr.)', datetime('now', 'localtime', '-2 hours'));
