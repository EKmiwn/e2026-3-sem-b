-- Fiktive testdata. Linjerne er Movias 2A, 4A, 5C, 150S, 250S og 350S med et forenklet udvalg af stoppesteder.
-- Stoppesteder og køretider er ikke kontrolleret mod Movias køreplan.
INSERT INTO stop (name) VALUES
  ('Tingbjerg'), ('Brønshøj Torv'), ('Forum St.'), ('Rådhuspladsen'), ('Københavns Hovedbanegård'),      -- 1–5
  ('Christianshavn St.'), ('Refshaleøen'), ('Buddinge St.'), ('Emdrup Torv'), ('Bispebjerg St.'),         -- 6–10
  ('Flintholm St.'), ('Valby St.'), ('Friheden St.'), ('Herlev Hospital'), ('Husum Torv'),                -- 11–15
  ('Nørrebro St.'), ('Nørreport St.'), ('Sundbyvester Plads'), ('Københavns Lufthavn'), ('Kokkedal St.'), -- 16–20
  ('Gl. Holte'), ('DTU'), ('Ryparken St.'), ('Bagsværd St.'), ('Gladsaxe Trafikplads'),                   -- 21–25
  ('Bispebjerg Hospital'), ('Dragør Stationsplads'), ('Ballerup St.'), ('Skovlunde St.');                 -- 26–29

INSERT INTO line (name, description) VALUES
  ('2A', 'A-bus: Tingbjerg – Refshaleøen via Rådhuspladsen og Hovedbanegården'),
  ('4A', 'A-bus: Buddinge St. – Friheden St. via Bispebjerg og Valby'),
  ('5C', 'C-bus: Herlev Hospital – Københavns Lufthavn via Nørrebro og Nørreport'),
  ('150S', 'S-bus: Kokkedal St. – Nørreport St. via DTU og Ryparken'),
  ('250S', 'S-bus: Bagsværd St. – Dragør Stationsplads via Bispebjerg og Hovedbanegården'),
  ('350S', 'S-bus: Ballerup St. – Nørreport St. via Husum og Nørrebro');

INSERT INTO line_stop (line_id, stop_id, seq, minutes_from_start) VALUES
  (1, 1, 1, 0), (1, 2, 2, 7), (1, 3, 3, 16), (1, 4, 4, 22), (1, 5, 5, 26), (1, 6, 6, 33), (1, 7, 7, 42),
  (2, 8, 1, 0), (2, 9, 2, 8), (2, 10, 3, 13), (2, 11, 4, 22), (2, 12, 5, 31), (2, 13, 6, 40),
  (3, 14, 1, 0), (3, 15, 2, 9), (3, 16, 3, 16), (3, 17, 4, 24), (3, 5, 5, 30), (3, 18, 6, 41), (3, 19, 7, 50),
  (4, 20, 1, 0), (4, 21, 2, 12), (4, 22, 3, 22), (4, 23, 4, 34), (4, 17, 5, 45),
  (5, 24, 1, 0), (5, 25, 2, 6), (5, 26, 3, 15), (5, 5, 4, 29), (5, 18, 5, 40), (5, 27, 6, 58),
  (6, 28, 1, 0), (6, 29, 2, 6), (6, 15, 3, 15), (6, 16, 4, 22), (6, 17, 5, 30);

-- Tre busser pr. linje
INSERT INTO bus (number, line_id, quiet_zone) VALUES
  ('Bus 2A-1', 1, 'BAGERST'), ('Bus 2A-2', 1, 'INGEN'), ('Bus 2A-3', 1, 'FORREST'),
  ('Bus 4A-1', 2, 'INGEN'), ('Bus 4A-2', 2, 'BAGERST'), ('Bus 4A-3', 2, 'INGEN'),
  ('Bus 5C-1', 3, 'BAGERST'), ('Bus 5C-2', 3, 'FORREST'), ('Bus 5C-3', 3, 'INGEN'),
  ('Bus 150S-1', 4, 'BAGERST'), ('Bus 150S-2', 4, 'INGEN'), ('Bus 150S-3', 4, 'FORREST'),
  ('Bus 250S-1', 5, 'BAGERST'), ('Bus 250S-2', 5, 'BAGERST'), ('Bus 250S-3', 5, 'INGEN'),
  ('Bus 350S-1', 6, 'INGEN'), ('Bus 350S-2', 6, 'FORREST'), ('Bus 350S-3', 6, 'INGEN');

-- Afgange hvert 10. minut kl. 06:00–22:00 på hver linje. Linjens tre busser kører på skift.
INSERT INTO departure (line_id, bus_id, departs_at)
WITH RECURSIVE t(m) AS (SELECT 360 UNION ALL SELECT m + 10 FROM t WHERE m < 1320)
SELECT l.id, (l.id - 1) * 3 + 1 + (t.m / 10) % 3, printf('%02d:%02d', t.m / 60, t.m % 60)
FROM line l, t ORDER BY l.id, t.m;

-- Seneste måling pr. bus og område. Busser uden rolig zone er mest fyldte, og den rolige zone er det roligste område.
INSERT INTO sensor_reading (bus_id, area, noise_db, crowding_pct, measured_at)
SELECT b.id, a.area,
       CASE WHEN a.area = b.quiet_zone THEN 45 + (b.id * 3) % 8
            WHEN b.quiet_zone = 'INGEN' THEN 64 + (b.id * 5 + a.n * 3) % 14
            ELSE 55 + (b.id * 5 + a.n * 3) % 12 END,
       CASE WHEN a.area = b.quiet_zone THEN 15 + (b.id * 7) % 20
            WHEN b.quiet_zone = 'INGEN' THEN 60 + (b.id * 11 + a.n * 7) % 40
            ELSE 35 + (b.id * 11 + a.n * 7) % 35 END,
       '2026-09-30 07:40:00'
FROM bus b, (SELECT 'FORREST' AS area, 1 AS n UNION ALL SELECT 'MIDTEN', 2 UNION ALL SELECT 'BAGERST', 3) a
ORDER BY b.id, a.n;

INSERT INTO passenger (name, school, sunflower_enabled, voice_guide, notify_stops_before) VALUES
  ('Emil (17)', 'Lyngby Tekniske Gymnasium', 1, 1, 1),
  ('Sara (19)', 'KEA Nørrebro', 1, 1, 2),
  ('Noah (16)', 'Ballerup HF', 0, 0, 1);

-- Emil: 150S kl. 07:50 fra DTU til Nørreport St. · Sara: 5C kl. 08:10 fra Herlev Hospital til Nørrebro St.
INSERT INTO trip (passenger_id, departure_id, from_stop_id, to_stop_id, status, current_seq, created_at, boarded_at, finished_at) VALUES
  (1, 303, 22, 17, 'AFSLUTTET', 5, '2026-09-29 08:05:00', '2026-09-29 08:12:00', '2026-09-29 08:35:00'),
  (2, 208, 14, 16, 'AFSLUTTET', 3, '2026-09-29 08:05:00', '2026-09-29 08:10:00', '2026-09-29 08:26:00');

INSERT INTO sunflower_signal (trip_id, bus_id, token, stop_name, status, sent_at, acknowledged_at) VALUES
  (1, 12, 'SOL-4F2A', 'DTU', 'AFSLUTTET', '2026-09-29 08:12:00', '2026-09-29 08:12:20'),
  (2, 8, 'SOL-9C71', 'Herlev Hospital', 'AFSLUTTET', '2026-09-29 08:10:00', '2026-09-29 08:10:40');

INSERT INTO feedback (trip_id, calm_rating, felt_safe, comment, created_at) VALUES
  (1, 4, 1, 'Rolig zone forrest var fin.', '2026-09-29 08:36:00'),
  (2, 3, 1, 'Lidt larm ved Husum Torv.', '2026-09-29 08:27:00');
