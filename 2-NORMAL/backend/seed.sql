-- Fiktive testdata – ikke NORMALs rigtige sortiment eller lager
INSERT INTO setting (key, value, description) VALUES
  ('low_stock_limit', 3, 'Højst så mange stk. = "Få tilbage"');

INSERT INTO store (name, city, address, employees) VALUES
  ('NORMAL Strøget', 'København', 'Amagertorv 29, 1160 København K', 14),
  ('NORMAL Fisketorvet', 'København', 'Kalvebod Brygge 59, 1560 København V', 9),
  ('NORMAL Lyngby Storcenter', 'Kgs. Lyngby', 'Firskovvej 18, 2800 Kgs. Lyngby', 8),
  ('NORMAL Aarhus C', 'Aarhus', 'Søndergade 43, 8000 Aarhus C', 11),
  ('NORMAL Bruuns Galleri', 'Aarhus', 'M.P. Bruuns Gade 25, 8000 Aarhus C', 7),
  ('NORMAL Odense', 'Odense', 'Vestergade 20, 5000 Odense C', 8);

INSERT INTO category (name) VALUES ('Hårpleje'), ('Hudpleje'), ('Tandpleje'), ('Makeup'), ('Snacks'), ('Rengøring');

INSERT INTO product (sku, name, brand, category_id, price, keywords) VALUES
  ('100231', 'Shampoo Repair 400 ml', 'Elvital', 1, 29, 'shampoo hår vask'),
  ('100232', 'Balsam Repair 400 ml', 'Elvital', 1, 29, 'balsam conditioner hår'),
  ('100410', 'Tør shampoo Original 200 ml', 'Batiste', 1, 25, 'shampoo tørshampoo spray'),
  ('200118', 'Dagcreme SPF 15 50 ml', 'Nivea', 2, 35, 'creme ansigt solfaktor'),
  ('200560', 'Micellar vand 400 ml', 'Garnier', 2, 30, 'makeupfjerner rens ansigt'),
  ('300077', 'Tandpasta Total 75 ml', 'Colgate', 3, 15, 'tænder tandpasta'),
  ('300090', 'Eltandbørstehoveder 4 stk.', 'Oral-B', 3, 79, 'tandbørste børstehoveder'),
  ('400301', 'Mascara Lash Sensational', 'Maybelline', 4, 59, 'mascara vipper makeup'),
  ('400512', 'Concealer Fit Me', 'Maybelline', 4, 45, 'concealer makeup'),
  ('500020', 'Chips Sour Cream 175 g', 'Kims', 5, 15, 'chips snack'),
  ('500145', 'Energidrik 250 ml', 'Monster', 5, 12, 'drik energi'),
  ('600033', 'Opvasketabs 40 stk.', 'Fairy', 6, 49, 'opvask maskine tabs');

-- Lager: nogle varer er udsolgt i nogle butikker, så kunden skal vælge en anden butik
INSERT INTO stock (store_id, product_id, quantity, updated_at)
SELECT s.id, p.id,
       CASE WHEN (s.id * 7 + p.id * 3) % 5 = 0 THEN 0
            WHEN (s.id + p.id) % 4 = 0 THEN 2
            ELSE 4 + (s.id * p.id) % 17 END,
       '2026-09-30 08:00:00'
FROM store s, product p ORDER BY s.id, p.id;

INSERT INTO search_log (query, result_count, created_at) VALUES
  ('shampoo', 3, '2026-09-29 10:12:00'), ('mascara', 1, '2026-09-29 11:40:00'),
  ('shampoo', 3, '2026-09-29 15:02:00'), ('solcreme', 0, '2026-09-29 16:30:00'),
  ('tandpasta', 1, '2026-09-30 08:15:00');

INSERT INTO lookup_log (product_id, store_id, status, created_at) VALUES
  (1, 1, 'PÅ_LAGER', '2026-09-29 10:13:00'), (8, 3, 'UDSOLGT', '2026-09-29 11:41:00'),
  (8, 1, 'PÅ_LAGER', '2026-09-29 11:42:00'), (3, 4, 'FÅ_TILBAGE', '2026-09-29 15:03:00'),
  (6, 2, 'PÅ_LAGER', '2026-09-30 08:16:00');
