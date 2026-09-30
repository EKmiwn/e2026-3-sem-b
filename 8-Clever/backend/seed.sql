-- Fiktive testdata – ikke Clevers rigtige priser, standere eller strømdata
INSERT INTO operator (name, is_clever) VALUES ('Clever', 1), ('IONITY', 0), ('Allego', 0), ('Eviny', 0);

INSERT INTO tariff (name, price_per_kwh, start_fee, minute_price, valid_from) VALUES
  ('Clever AC', 3.49, 0, 0, '2026-09-01'),
  ('Clever lynlader', 4.49, 0, 0, '2026-09-01'),
  ('IONITY (roaming)', 5.99, 0, 0, '2026-09-01'),
  ('Allego (roaming)', 4.99, 5, 0, '2026-09-01'),
  ('Eviny (roaming)', 4.29, 0, 0.25, '2026-09-01');

INSERT INTO location (operator_id, name, address, city, country, price_area, lat, lng) VALUES
  (1, 'Greve Hallen', 'Hallevej 4', 'Greve', 'DK', 'DK2', 55.5886, 12.2990),
  (1, 'Greve Midtby Center', 'Greve Stationsvej 1', 'Greve', 'DK', 'DK2', 55.5855, 12.2930),
  (1, 'Fisketorvet', 'Kalvebod Brygge 59', 'København', 'DK', 'DK2', 55.6630, 12.5620),
  (1, 'Køge Nord Lynladepark', 'Nordhavnsvej 2', 'Køge', 'DK', 'DK2', 55.4900, 12.1500),
  (1, 'Ringsted Syd', 'Plantagevej 8', 'Ringsted', 'DK', 'DK2', 55.4300, 11.7900),
  (1, 'Odense Rosengårdcentret', 'Ørbækvej 75', 'Odense', 'DK', 'DK1', 55.3740, 10.4460),
  (2, 'Kolding Vest', 'Vejlevej 120', 'Kolding', 'DK', 'DK1', 55.4900, 9.4300),
  (1, 'Aarhus Ceres Byen', 'Ceres Allé 1', 'Aarhus', 'DK', 'DK1', 56.1590, 10.2000),
  (1, 'Padborg Transit', 'Industrivej 1', 'Padborg', 'DK', 'DK1', 54.8260, 9.3600),
  (2, 'Flensburg Nord', 'Harrisleer Str. 1', 'Flensburg', 'DE', NULL, 54.8000, 9.4400),
  (3, 'Hamburg Nord', 'Kieler Str. 700', 'Hamburg', 'DE', NULL, 53.6000, 10.0200),
  (4, 'Malmö Hyllie', 'Hyllie Boulevard 10', 'Malmö', 'SE', NULL, 55.5630, 12.9750),
  (4, 'Göteborg Kållered', 'Ekenleden 5', 'Göteborg', 'SE', NULL, 57.6100, 12.0500),
  (4, 'Oslo Økern', 'Økernveien 145', 'Oslo', 'NO', NULL, 59.9300, 10.8100),
  (4, 'Helsingborg Väla', 'Marknadsvägen 3', 'Helsingborg', 'SE', NULL, 56.0600, 12.7300),
  (4, 'Svinesund Grensehandel', 'Svinesundsparken 1', 'Halden', 'NO', NULL, 59.1000, 11.2700);

INSERT INTO charger (location_id, code, model, max_power_kw) VALUES
  (1, 'CLV-1001', 'Alfen Eve Double', 22), (1, 'CLV-1002', 'Kempower S-series', 150),
  (2, 'CLV-1011', 'Kempower S-series', 150), (2, 'CLV-1012', 'Alfen Eve Double', 22),
  (3, 'CLV-2001', 'Alfen Eve Double', 22), (3, 'CLV-2002', 'ABB Terra 54', 50),
  (4, 'CLV-3001', 'Kempower T-series', 300), (4, 'CLV-3002', 'Kempower T-series', 300), (4, 'CLV-3003', 'Kempower T-series', 300),
  (5, 'CLV-3101', 'Kempower S-series', 150),
  (6, 'CLV-4001', 'Kempower S-series', 150), (6, 'CLV-4002', 'Alfen Eve Double', 22),
  (7, 'ION-7001', 'Tritium PK350', 350),
  (8, 'CLV-5001', 'Kempower S-series', 150), (8, 'CLV-5002', 'Kempower S-series', 150),
  (9, 'CLV-6001', 'Kempower T-series', 300),
  (10, 'ION-7101', 'Tritium PK350', 350),
  (11, 'ALG-8001', 'Alpitronic HYC300', 300),
  (12, 'EVY-9001', 'Kempower S-series', 150),
  (13, 'EVY-9101', 'Kempower S-series', 150),
  (14, 'EVY-9201', 'Kempower S-series', 150),
  (15, 'EVY-9301', 'Kempower S-series', 150),
  (16, 'EVY-9401', 'Kempower S-series', 150);

INSERT INTO connector (charger_id, plug_type, status, tariff_id, updated_at) VALUES
  (1, 'TYPE2', 'LEDIG', 1, datetime('now', 'localtime', '-3 minutes')),
  (1, 'TYPE2', 'OPTAGET', 1, datetime('now', 'localtime', '-40 minutes')),
  (2, 'CCS', 'UDE_AF_DRIFT', 2, datetime('now', 'localtime', '-2 hours')),
  (3, 'CCS', 'LEDIG', 2, datetime('now', 'localtime', '-1 minutes')),
  (4, 'TYPE2', 'OPTAGET', 1, datetime('now', 'localtime', '-12 minutes')),
  (4, 'TYPE2', 'LEDIG', 1, datetime('now', 'localtime', '-12 minutes')),
  (5, 'TYPE2', 'OPTAGET', 1, datetime('now', 'localtime', '-25 minutes')),
  (5, 'TYPE2', 'OPTAGET', 1, datetime('now', 'localtime', '-8 minutes')),
  (6, 'CCS', 'LEDIG', 2, datetime('now', 'localtime', '-5 minutes')),
  (7, 'CCS', 'LEDIG', 2, datetime('now', 'localtime', '-1 minutes')),
  (8, 'CCS', 'OPTAGET', 2, datetime('now', 'localtime', '-15 minutes')),
  (9, 'CCS', 'LEDIG', 2, datetime('now', 'localtime', '-2 minutes')),
  (10, 'CCS', 'LEDIG', 2, datetime('now', 'localtime', '-4 minutes')),
  (11, 'CCS', 'LEDIG', 2, datetime('now', 'localtime', '-6 minutes')),
  (12, 'TYPE2', 'LEDIG', 1, datetime('now', 'localtime', '-6 minutes')),
  (13, 'CCS', 'LEDIG', 3, datetime('now', 'localtime', '-9 minutes')),
  (14, 'CCS', 'OPTAGET', 2, datetime('now', 'localtime', '-20 minutes')),
  (15, 'CCS', 'LEDIG', 2, datetime('now', 'localtime', '-3 minutes')),
  (16, 'CCS', 'LEDIG', 2, datetime('now', 'localtime', '-7 minutes')),
  (17, 'CCS', 'LEDIG', 3, datetime('now', 'localtime', '-11 minutes')),
  (18, 'CCS', 'LEDIG', 4, datetime('now', 'localtime', '-14 minutes')),
  (19, 'CCS', 'LEDIG', 5, datetime('now', 'localtime', '-10 minutes')),
  (20, 'CCS', 'LEDIG', 5, datetime('now', 'localtime', '-10 minutes')),
  (21, 'CCS', 'OPTAGET', 5, datetime('now', 'localtime', '-16 minutes')),
  (22, 'CCS', 'LEDIG', 5, datetime('now', 'localtime', '-5 minutes')),
  (23, 'CCS', 'LEDIG', 5, datetime('now', 'localtime', '-4 minutes'));

INSERT INTO app_user (name, email, language, card_valid, filters) VALUES
  ('Mikkel (Bekvemmelighedsfamilien)', 'mikkel@test.dk', 'da', 1, '{}'),
  ('Freja (urban pendler)', 'freja@test.dk', 'da', 1, '{"max_price": 4.5, "only_free": 1}'),
  ('Christian', 'christian@test.dk', 'da', 0, '{}');

INSERT INTO car (user_id, model, plug_type, max_power_kw, battery_kwh, range_km) VALUES
  (1, 'Kia EV6', 'CCS', 240, 77.4, 500),
  (2, 'VW ID.3', 'CCS', 120, 58, 420),
  (3, 'Renault Zoe', 'TYPE2', 22, 52, 390);

INSERT INTO subscription (user_id, type, monthly_price, start_date) VALUES
  (1, 'CLEVER_ONE', 799, '2025-03-01'), (2, 'INGEN', 0, '2026-01-01'), (3, 'CLEVER_BOX', 399, '2024-11-01');

-- Simuleret døgnprofil. Kilde: Energinet Energi Data Service (i drift hentes tallene derfra)
INSERT INTO energy_mix (hour, price_area, renewable_pct, gco2_per_kwh, source)
WITH RECURSIVE h(n) AS (SELECT 0 UNION ALL SELECT n + 1 FROM h WHERE n < 23)
SELECT n, 'DK1', 50 + (n * 7) % 35, 380 - (50 + (n * 7) % 35) * 3, 'Energinet Energi Data Service (simuleret)' FROM h
UNION ALL
SELECT n, 'DK2', 40 + (n * 11) % 35, 400 - (40 + (n * 11) % 35) * 3, 'Energinet Energi Data Service (simuleret)' FROM h;

INSERT INTO favorite (user_id, location_id, label) VALUES (1, 1, 'Hallen'), (1, 3, 'Arbejde'), (2, 3, 'Arbejde'), (2, 5, 'Mor og far');

-- Historik: afsluttede opladninger de seneste måneder (FR-15)
INSERT INTO session (user_id, connector_id, car_id, start_method, price_per_kwh, start_fee, minute_price, battery_start_pct,
                     renewable_pct, gco2_per_kwh, status, started_at, ended_at, minutes, kwh, avg_power_kw, price_total) VALUES
  (1, 1, 1, 'AUTO', 3.49, 0, 0, 35, 62, 214, 'AFSLUTTET', '2026-07-04 17:10:00', '2026-07-04 19:10:00', 120, 38.0, 19.0, 132.62),
  (1, 10, 1, 'QR', 4.49, 0, 0, 18, 55, 235, 'AFSLUTTET', '2026-07-19 11:02:00', '2026-07-19 11:26:00', 24, 48.5, 121.3, 217.77),
  (1, 1, 1, 'AUTO', 3.49, 0, 0, 40, 70, 190, 'AFSLUTTET', '2026-08-06 16:45:00', '2026-08-06 18:15:00', 90, 29.0, 19.3, 101.21),
  (1, 13, 1, 'ID', 5.99, 0, 0, 22, NULL, NULL, 'AFSLUTTET', '2026-08-15 12:30:00', '2026-08-15 12:52:00', 22, 45.0, 122.7, 269.55),
  (1, 1, 1, 'AUTO', 3.49, 0, 0, 30, 58, 226, 'AFSLUTTET', '2026-09-10 17:00:00', '2026-09-10 19:00:00', 120, 40.0, 20.0, 139.60),
  (1, 9, 1, 'AUTO', 4.49, 0, 0, 25, 64, 208, 'AFSLUTTET', '2026-09-22 08:05:00', '2026-09-22 08:45:00', 40, 20.0, 30.0, 89.80),
  (2, 10, 2, 'QR', 4.49, 0, 0, 20, 48, 256, 'AFSLUTTET', '2026-08-02 09:15:00', '2026-08-02 09:45:00', 30, 35.0, 70.0, 157.15),
  (2, 9, 2, 'AUTO', 4.49, 0, 0, 30, 66, 202, 'AFSLUTTET', '2026-08-29 18:00:00', '2026-08-29 18:35:00', 35, 30.0, 51.4, 134.70),
  (2, 13, 2, 'ID', 4.49, 0, 0, 15, 52, 244, 'AFSLUTTET', '2026-09-18 07:40:00', '2026-09-18 08:20:00', 40, 38.0, 57.0, 170.62);

INSERT INTO payment (session_id, amount, method, status, receipt_no, created_at) VALUES
  (1, 132.62, 'Clever One', 'GENNEMFØRT', 'KV-260704-001', '2026-07-04 19:10:10'),
  (2, 217.77, 'Clever One', 'GENNEMFØRT', 'KV-260719-002', '2026-07-19 11:26:10'),
  (3, 101.21, 'Clever One', 'GENNEMFØRT', 'KV-260806-003', '2026-08-06 18:15:10'),
  (4, 269.55, 'Kort (roaming)', 'GENNEMFØRT', 'KV-260815-004', '2026-08-15 12:52:10'),
  (5, 139.60, 'Clever One', 'GENNEMFØRT', 'KV-260910-005', '2026-09-10 19:00:10'),
  (6, 89.80, 'Clever One', 'GENNEMFØRT', 'KV-260922-006', '2026-09-22 08:45:10'),
  (7, 157.15, 'Kort', 'GENNEMFØRT', 'KV-260802-007', '2026-08-02 09:45:10'),
  (8, 134.70, 'Kort', 'GENNEMFØRT', 'KV-260829-008', '2026-08-29 18:35:10'),
  (9, 170.62, 'Kort', 'GENNEMFØRT', 'KV-260918-009', '2026-09-18 08:20:10');

INSERT INTO fault_report (user_id, charger_id, category, description, status, created_at, updated_at) VALUES
  (1, 2, 'STARTER_IKKE', 'Lynladeren ved hallen reagerer ikke – skærmen er sort.', 'UNDER_BEHANDLING',
   datetime('now', 'localtime', '-2 hours'), datetime('now', 'localtime', '-1 hours'));

INSERT INTO alert (user_id, type, message, created_at) VALUES
  (1, 'FAVORIT_UDE_AF_DRIFT', 'Lynladeren ved Hallen er ude af drift – nærmeste ledige: Greve Midtby Center (0,4 km)',
   datetime('now', 'localtime', '-2 hours'));
