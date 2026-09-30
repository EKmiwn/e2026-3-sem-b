-- Fiktive testdata (indstillingernes beskrivelser er på engelsk, fordi de vises i brugerfladen)
INSERT INTO setting (key, value, description) VALUES
  ('financial_weight', 0.5, 'Share of the match score from financial compatibility (the rest is lifestyle)'),
  ('min_match_score', 55, 'Buyers below this score are not shown as matches'),
  ('max_group_size', 4, 'Maximum number of buyers in a group (assumption)'),
  ('extra_area_per_member', 15, 'm² added to the largest minimum area for each extra group member (assumption)');

INSERT INTO agent (name, office) VALUES ('Camilla Holt', '&LIVING Copenhagen'), ('Rasmus Lind', '&LIVING Aarhus');

INSERT INTO buyer (name, email, phone, age, budget, preapproved_loan, down_payment, preferred_location, property_type,
                   min_area, max_transport_min, pets, smoker, has_children, social_level, share_contact, consent_at) VALUES
  ('Freja', 'freja@test.dk', '+45 20 11 22 33', 27, 2400000, 2000000, 150000, 'Copenhagen NV', 'APARTMENT', 60, 25, 0, 0, 0, 3, 1, '2026-09-20 10:00:00'),
  ('Jonas', 'jonas@test.dk', '+45 30 44 55 66', 29, 2600000, 2200000, 200000, 'Copenhagen NV', 'APARTMENT', 55, 30, 0, 0, 0, 4, 0, '2026-09-21 12:00:00'),
  ('Aisha', 'aisha@test.dk', NULL, 31, 2300000, 1900000, 180000, 'Valby', 'APARTMENT', 65, 30, 1, 0, 0, 2, 0, '2026-09-22 09:00:00'),
  ('Mikkel', 'mikkel@test.dk', NULL, 26, 1500000, 1200000, 60000, 'Nørrebro', 'APARTMENT', 45, 20, 0, 1, 0, 5, 0, '2026-09-23 18:00:00'),
  ('Sofie', 'sofie@test.dk', NULL, 34, 3200000, 2700000, 400000, 'Aarhus N', 'TOWNHOUSE', 90, 25, 1, 0, 1, 2, 0, '2026-09-24 08:00:00'),
  ('Oliver', 'oliver@test.dk', NULL, 33, 3000000, 2600000, 350000, 'Aarhus N', 'TOWNHOUSE', 85, 30, 0, 0, 1, 3, 0, '2026-09-24 20:00:00'),
  ('Laura', 'laura@test.dk', NULL, 25, 2500000, 2100000, 120000, 'Copenhagen NV', 'APARTMENT', 50, 25, 0, 0, 0, 3, 0, NULL);

INSERT INTO buyer_group (name, agent_id, created_at) VALUES ('Freja & Jonas', 1, '2026-09-25 19:00:00');
INSERT INTO group_member (group_id, buyer_id, joined_at) VALUES (1, 1, '2026-09-25 19:00:00'), (1, 2, '2026-09-25 19:05:00');

INSERT INTO property (address, location, property_type, price, area, rooms, transport_min, monthly_cost, off_market, agent_id) VALUES
  ('Frederikssundsvej 88, 3. tv', 'Copenhagen NV', 'APARTMENT', 3950000, 82, 3, 15, 4200, 0, 1),
  ('Bispebjerg Parkallé 12, 2. th', 'Copenhagen NV', 'APARTMENT', 4400000, 95, 4, 18, 4800, 1, 1),
  ('Hulgårdsvej 40, st.', 'Copenhagen NV', 'APARTMENT', 3400000, 68, 3, 20, 3900, 0, 1),
  ('Toftegårds Allé 7, 4. tv', 'Valby', 'APARTMENT', 3700000, 75, 3, 12, 4100, 0, 1),
  ('Jagtvej 150, 1. th', 'Nørrebro', 'APARTMENT', 2900000, 55, 2, 8, 3300, 0, 1),
  ('Tingvej 9', 'Aarhus N', 'TOWNHOUSE', 5600000, 120, 5, 20, 6200, 0, 2),
  ('Randersvej 210', 'Aarhus N', 'HOUSE', 6200000, 140, 5, 25, 7000, 1, 2),
  ('Amager Strandvej 30, 5. tv', 'Amager', 'APARTMENT', 5200000, 88, 3, 14, 4600, 0, 1);

INSERT INTO message (group_id, sender_id, text, created_at) VALUES
  (1, 1, 'Hej Jonas! Jeg kan godt lide, at vi begge vil bo i NV.', '2026-09-25 19:10:00'),
  (1, 2, 'Ja! Skal vi kigge på Frederikssundsvej sammen?', '2026-09-25 19:14:00');

INSERT INTO shortlist_item (group_id, property_id, added_by, added_at) VALUES (1, 1, 1, '2026-09-26 08:00:00');
INSERT INTO vote (shortlist_item_id, buyer_id, value, comment, created_at) VALUES
  (1, 1, 1, 'Great light and close to the metro.', '2026-09-26 08:01:00');
