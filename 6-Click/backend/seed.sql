-- Fiktive testdata. Formater følger Fujifilm Frontier DL600 (89 × 127 mm til 305 × 1.219 mm)
INSERT INTO setting (key, value, description) VALUES
  ('dpi_threshold', 150, 'Advarsel under denne effektive DPI (§6.2.4)'),
  ('retention_days', 30, 'Dage billedfiler gemmes efter afhentning (§17 – åbent punkt 6)'),
  ('cart_retention_days', 1, 'Dage en ubetalt kurv med billeder og kontaktoplysninger gemmes (§17)'),
  ('shipping_price', 49, 'Fragt i kr. ved forsendelse'),
  ('production_days', 2, 'Hverdage fra modtagelse til ønsket færdig');

-- Formater × overflade × kvalitet. Højkvalitet koster 50 % mere
INSERT INTO product (label, width_mm, height_mm, roll_width_mm, surface, quality, price)
WITH sizes(label, w, h, roll, price) AS (VALUES
  ('9 × 13 cm', 89, 127, 127, 3.5), ('10 × 15 cm', 102, 152, 102, 4), ('13 × 18 cm', 127, 178, 127, 7),
  ('15 × 20 cm', 152, 203, 152, 12), ('20 × 25 cm', 203, 254, 203, 29), ('20 × 30 cm', 203, 305, 203, 39),
  ('25 × 30 cm', 254, 305, 254, 59), ('30 × 40 cm', 305, 406, 305, 89), ('30 × 45 cm', 305, 457, 305, 99),
  ('30 × 122 cm panorama', 305, 1219, 305, 249)),
surfaces(s) AS (VALUES ('BLANK'), ('SILKE')),
qualities(q, factor) AS (VALUES ('STANDARD', 1.0), ('HØJ', 1.5))
SELECT sizes.label, w, h, roll, s, q, round(price * factor, 1) FROM sizes, surfaces, qualities
ORDER BY w, h, s, q DESC;

INSERT INTO operator (name, pin) VALUES ('Martin (indehaver)', '1234'), ('Deltidsansat', '0000');

INSERT INTO customer (name, email, phone, created_at) VALUES
  ('Grethe Hansen', 'grethe@test.dk', '+45 20304050', '2026-09-28 10:00:00'),
  ('Ali Yilmaz', 'ali@test.dk', '+45 31415926', '2026-09-29 19:30:00');

UPDATE customer SET address = 'Fjordvej 7, 9000 Aalborg' WHERE id = 2;

INSERT INTO photo_order (access_key, customer_id, status, delivery, payment_status, payment_ref, consent_at, total,
                         created_at, received_at, desired_ready) VALUES
  ('DEMO-GRETHE', 1, 'MODTAGET', 'AFHENTNING', 'BETALT', 'PAY-10001', '2026-09-28 10:05:00', 44,
   '2026-09-28 10:00:00', '2026-09-28 10:06:00', '2026-09-30'),
  ('DEMO-ALI', 2, 'I_PRODUKTION', 'FORSENDELSE', 'BETALT', 'PAY-10002', '2026-09-29 19:35:00', 265,
   '2026-09-29 19:30:00', '2026-09-29 19:36:00', '2026-10-01');

INSERT INTO image (order_id, filename, file_type, px_width, px_height, file_size, orientation, uploaded_at) VALUES
  (1, 'barnebarn.jpg', 'JPEG', 4032, 3024, 3100000, 'LIGGENDE', '2026-09-28 10:01:00'),
  (1, 'have.jpg', 'JPEG', 1600, 1200, 450000, 'LIGGENDE', '2026-09-28 10:02:00'),
  (2, 'bjerge.tif', 'TIFF', 6000, 4000, 72000000, 'LIGGENDE', '2026-09-29 19:31:00');

-- Produkt-id: 10 × 15 blank standard = 5, 20 × 30 silke høj = 24, 30 × 45 blank standard = 33
INSERT INTO order_line (order_id, image_id, product_id, quantity, crop, rotation, effective_dpi, dpi_warning, line_price) VALUES
  (1, 1, 5, 6, 'FYLD', 0, 674, 0, 24),
  (1, 2, 5, 5, 'FYLD', 0, 267, 0, 20),
  (2, 3, 24, 2, 'HELT_TIL_KANT', 0, 500, 0, 117),
  (2, 3, 33, 1, 'FYLD', 0, 333, 0, 99);

INSERT INTO print_job (order_id, operator_id, payload, created_at) VALUES
  (2, 1, '{"format": "C8-JSON (antaget)", "order": 2}', '2026-09-30 08:30:00');
