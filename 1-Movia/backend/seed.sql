-- Fiktive testdata (stoppesteder og køretider er forenklede)
INSERT INTO stop (name) VALUES
  ('Lyngby St.'), ('Jægersborg St.'), ('Ryparken St.'), ('Østerport St.'), ('Nørreport St.'),
  ('Gentofte Hospital'), ('Hellerup St.'), ('Ballerup St.'), ('Herlev Hospital'), ('Husum Torv'), ('Nørrebro St.');

INSERT INTO line (name, description) VALUES
  ('150S', 'Lyngby St. – Nørreport St. via Ryparken'),
  ('300S', 'Lyngby St. – Nørreport St. via Hellerup'),
  ('350S', 'Ballerup St. – Nørreport St. via Herlev Hospital');

INSERT INTO line_stop (line_id, stop_id, seq, minutes_from_start) VALUES
  (1, 1, 1, 0), (1, 2, 2, 6), (1, 3, 3, 14), (1, 4, 4, 22), (1, 5, 5, 27),
  (2, 1, 1, 0), (2, 6, 2, 7), (2, 7, 3, 14), (2, 4, 4, 21), (2, 5, 5, 28),
  (3, 8, 1, 0), (3, 9, 2, 8), (3, 10, 3, 15), (3, 11, 4, 22), (3, 5, 5, 30);

INSERT INTO bus (number, line_id, quiet_zone) VALUES
  ('Bus 1501', 1, 'BAGERST'), ('Bus 1502', 1, 'INGEN'), ('Bus 1503', 1, 'FORREST'),
  ('Bus 3001', 2, 'BAGERST'), ('Bus 3002', 2, 'BAGERST'), ('Bus 3003', 2, 'INGEN'),
  ('Bus 3501', 3, 'INGEN'), ('Bus 3502', 3, 'FORREST'), ('Bus 3503', 3, 'INGEN');

-- Afgange hvert 10. minut kl. 06:00–22:00 på hver linje. Linjens tre busser kører på skift.
INSERT INTO departure (line_id, bus_id, departs_at)
WITH RECURSIVE t(m) AS (SELECT 360 UNION ALL SELECT m + 10 FROM t WHERE m < 1320)
SELECT l.id, (l.id - 1) * 3 + 1 + (t.m / 10) % 3, printf('%02d:%02d', t.m / 60, t.m % 60)
FROM line l, t ORDER BY l.id, t.m;

-- Seneste måling pr. bus og område
INSERT INTO sensor_reading (bus_id, area, noise_db, crowding_pct, measured_at) VALUES
  (1, 'FORREST', 58, 45, '2026-09-30 07:40:00'), (1, 'MIDTEN', 62, 55, '2026-09-30 07:40:00'), (1, 'BAGERST', 48, 20, '2026-09-30 07:40:00'),
  (2, 'FORREST', 72, 85, '2026-09-30 07:40:00'), (2, 'MIDTEN', 76, 95, '2026-09-30 07:40:00'), (2, 'BAGERST', 70, 80, '2026-09-30 07:40:00'),
  (3, 'FORREST', 50, 30, '2026-09-30 07:40:00'), (3, 'MIDTEN', 60, 50, '2026-09-30 07:40:00'), (3, 'BAGERST', 64, 60, '2026-09-30 07:40:00'),
  (4, 'FORREST', 55, 35, '2026-09-30 07:40:00'), (4, 'MIDTEN', 57, 40, '2026-09-30 07:40:00'), (4, 'BAGERST', 45, 15, '2026-09-30 07:40:00'),
  (5, 'FORREST', 66, 70, '2026-09-30 07:40:00'), (5, 'MIDTEN', 68, 75, '2026-09-30 07:40:00'), (5, 'BAGERST', 52, 30, '2026-09-30 07:40:00'),
  (6, 'FORREST', 74, 90, '2026-09-30 07:40:00'), (6, 'MIDTEN', 78, 100, '2026-09-30 07:40:00'), (6, 'BAGERST', 73, 85, '2026-09-30 07:40:00'),
  (7, 'FORREST', 61, 50, '2026-09-30 07:40:00'), (7, 'MIDTEN', 63, 60, '2026-09-30 07:40:00'), (7, 'BAGERST', 60, 45, '2026-09-30 07:40:00'),
  (8, 'FORREST', 47, 20, '2026-09-30 07:40:00'), (8, 'MIDTEN', 55, 35, '2026-09-30 07:40:00'), (8, 'BAGERST', 58, 40, '2026-09-30 07:40:00'),
  (9, 'FORREST', 69, 75, '2026-09-30 07:40:00'), (9, 'MIDTEN', 71, 80, '2026-09-30 07:40:00'), (9, 'BAGERST', 67, 70, '2026-09-30 07:40:00');

INSERT INTO passenger (name, school, sunflower_enabled, notify_stops_before) VALUES
  ('Emil (17)', 'Lyngby Tekniske Gymnasium', 1, 1),
  ('Sara (19)', 'KEA Nørrebro', 1, 2),
  ('Noah (16)', 'Ballerup HF', 0, 1);

INSERT INTO trip (passenger_id, departure_id, from_stop_id, to_stop_id, status, current_seq, created_at, boarded_at, finished_at) VALUES
  (1, 12, 1, 4, 'AFSLUTTET', 4, '2026-09-29 07:45:00', '2026-09-29 07:50:00', '2026-09-29 08:12:00'),
  (2, 208, 8, 11, 'AFSLUTTET', 4, '2026-09-29 08:05:00', '2026-09-29 08:10:00', '2026-09-29 08:32:00');

INSERT INTO sunflower_signal (trip_id, bus_id, token, stop_name, status, sent_at, acknowledged_at) VALUES
  (1, 3, 'SOL-4F2A', 'Lyngby St.', 'AFSLUTTET', '2026-09-29 07:50:00', '2026-09-29 07:50:20'),
  (2, 8, 'SOL-9C71', 'Ballerup St.', 'AFSLUTTET', '2026-09-29 08:10:00', '2026-09-29 08:10:40');

INSERT INTO feedback (trip_id, calm_rating, felt_safe, comment, created_at) VALUES
  (1, 4, 1, 'Rolig zone bagerst var fin.', '2026-09-29 08:13:00'),
  (2, 3, 1, 'Lidt larm ved Herlev Hospital.', '2026-09-29 08:33:00');
