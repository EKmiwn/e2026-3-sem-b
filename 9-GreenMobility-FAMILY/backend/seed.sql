-- Fiktive testdata
INSERT INTO plan (name, monthly_price, included_hours, discount_pct, max_members, description) VALUES
  ('Family Basis', 299, 4, 10, 4, '4 timer inkluderet og 10 % rabat på ekstra minutter'),
  ('Family Plus', 549, 10, 20, 5, '10 timer inkluderet, 20 % rabat og prioritet på familiebiler'),
  ('Family Weekend', 399, 8, 15, 4, '8 timer – ideel til weekendture med børn');

INSERT INTO zone (name) VALUES ('Nørrebro'), ('Østerbro'), ('Vesterbro'), ('Amager'), ('Valby'), ('Frederiksberg');

INSERT INTO car_type (name, seats, child_seat, price_per_min) VALUES
  ('Lille bybil', 4, 0, 3.5), ('Familiebil med barnestol', 5, 1, 4.5), ('7-sæder', 7, 1, 5.5);

INSERT INTO car (plate, car_type_id, zone_id, battery_pct, status) VALUES
  ('GM 10 001', 1, 1, 85, 'KLAR'), ('GM 10 002', 1, 2, 64, 'KLAR'), ('GM 10 003', 1, 3, 92, 'KLAR'), ('GM 10 004', 1, 6, 40, 'KLAR'),
  ('GM 20 001', 2, 1, 78, 'KLAR'), ('GM 20 002', 2, 2, 88, 'KLAR'), ('GM 20 003', 2, 4, 55, 'KLAR'), ('GM 20 004', 2, 5, 71, 'SERVICE'),
  ('GM 20 005', 2, 3, 95, 'KLAR'),
  ('GM 30 001', 3, 4, 83, 'KLAR'), ('GM 30 002', 3, 6, 67, 'KLAR');

INSERT INTO family (name, plan_id, status, card_last4, payment_ref, home_zone_id, created_at) VALUES
  ('Familien Hansen', 2, 'AKTIV', '4242', 'PAY-FAM-001', 1, '2026-06-01 10:00:00'),
  ('Familien Ali', 1, 'AKTIV', '1881', 'PAY-FAM-002', 4, '2026-07-15 18:30:00'),
  ('Familien Berg', 3, 'AKTIV', '5100', 'PAY-FAM-003', 2, '2026-08-02 09:10:00'),
  ('Familien Nielsen', 1, 'AKTIV', '7777', 'PAY-FAM-004', 5, '2026-08-20 20:00:00');

INSERT INTO member (family_id, name, email, is_driver) VALUES
  (1, 'Louise Hansen', 'louise@test.dk', 1), (1, 'Anders Hansen', 'anders@test.dk', 1), (1, 'Ida (8 år)', NULL, 0),
  (2, 'Sara Ali', 'sara@test.dk', 1), (2, 'Yusuf (5 år)', NULL, 0),
  (3, 'Kristian Berg', 'kristian@test.dk', 1), (3, 'Maja Berg', 'maja@test.dk', 1),
  (4, 'Peter Nielsen', 'peter@test.dk', 1);

-- 8 ugers turhistorik: hverdage mest bybiler om morgenen, weekender mest familiebiler til Amager og Østerbro
INSERT INTO trip (family_id, car_type_id, zone_id, end_zone_id, started_at, minutes, km, included_min, price)
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 420),
t AS (SELECT i, date('now', 'localtime', '-' || (1 + i % 56) || ' days') AS d FROM n)
SELECT 1 + i % 4,
       CASE WHEN strftime('%w', d) IN ('0', '6') THEN 2 + (i % 3 = 0) ELSE 1 + (i % 4 = 0) END,
       CASE WHEN strftime('%w', d) IN ('0', '6') THEN (CASE i % 3 WHEN 0 THEN 4 WHEN 1 THEN 2 ELSE 1 + i % 6 END)
            ELSE 1 + (i * 7) % 6 END,
       1 + (i * 5) % 6,
       d || ' ' || printf('%02d', CASE WHEN strftime('%w', d) IN ('0', '6') THEN 9 + i % 8 ELSE 7 + (i * 3) % 12 END) || ':' || printf('%02d', (i * 13) % 60) || ':00',
       20 + (i * 17) % 160, round(5 + (i * 11) % 60 + 0.5, 1), 0, round((20 + (i * 17) % 160) * 3.5 * 0.9, 2)
FROM t;

INSERT INTO partner (name, category, benefit, credits_per_activity) VALUES
  ('Zoologisk Have', 'Oplevelse', '10 % rabat på familiebilletter', 5),
  ('Den Blå Planet', 'Oplevelse', 'Gratis entré for ét barn', 5),
  ('Experimentarium', 'Oplevelse', '15 % rabat på årskort', 4),
  ('Coop 365', 'Indkøb', '5 % rabat ved indkøb over 300 kr.', 2);

INSERT INTO credit_transaction (family_id, partner_id, amount, description, created_at) VALUES
  (1, 1, 5, 'Besøg i Zoologisk Have', '2026-09-06 11:00:00'),
  (1, 4, 2, 'Indkøb i Coop 365', '2026-09-12 17:30:00'),
  (2, 2, 5, 'Besøg i Den Blå Planet', '2026-09-20 10:15:00');

-- Kommende reservation for Familien Hansen
INSERT INTO reservation (family_id, member_id, car_id, start_at, end_at, status, created_at) VALUES
  (1, 1, 5, datetime('now', 'localtime', '+1 day', 'start of day', '+10 hours'), datetime('now', 'localtime', '+1 day', 'start of day', '+14 hours'),
   'BEKRÆFTET', datetime('now', 'localtime', '-1 hours'));
