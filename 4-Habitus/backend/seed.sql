-- Fiktive testdata – ingen rigtige beboere eller medarbejdere
INSERT INTO department (name, site) VALUES ('Afdeling Egen', 'Habitus Bosted Nord'), ('Afdeling Birk', 'Habitus Bosted Nord');

INSERT INTO staff (name, role, department_id) VALUES
  ('Mette (pædagog)', 'PÆDAGOG', 1), ('Ali (medhjælper)', 'MEDHJÆLPER', 1),
  ('Jonas (pædagog)', 'PÆDAGOG', 2), ('Birgit (leder)', 'LEDER', 1);

INSERT INTO resident (name, nickname, room, department_id) VALUES
  ('Kasper Holm', 'Kasper', 'Værelse 3', 1),
  ('Lone Friis', 'Lone', 'Værelse 5', 1),
  ('Morten Dahl', 'Mo', 'Værelse 7', 1),
  ('Signe Bak', 'Signe', 'Værelse 2', 2);

INSERT INTO medication (resident_id, name, dose, is_pn) VALUES
  (1, 'Melatonin', '3 mg til natten', 0), (1, 'Panodil', '500 mg efter behov', 1),
  (2, 'Sertralin', '50 mg morgen', 0),
  (3, 'Risperidon', '1 mg morgen og aften', 0), (3, 'Atarax', '10 mg efter behov', 1),
  (4, 'Levaxin', '50 mikrogram morgen', 0);

INSERT INTO recording (staff_id, resident_id, suggested_resident_id, transcript, final_text, category, category_confidence,
                       transcript_confidence, contains_medication, handover, uncertain, requires_approval, status,
                       audio_stored, duration_sec, recorded_at, approved_at, approved_by) VALUES
  (1, 1, 1, 'Kasper var glad efter frokost og spiste det hele.', 'Kasper var glad efter frokost og spiste det hele.',
   'OBSERVATION', 1.0, 0.95, 0, 0, '[]', 0, 'GODKENDT', 0, 12, '2026-09-29 13:10:00', '2026-09-29 13:10:05', 1),
  (2, 3, 3, 'Mo fik 10 mg Atarax klokken 15 fordi han var meget urolig.', 'Mo fik 10 mg Atarax kl. 15, fordi han var meget urolig.',
   'MEDICIN', 1.0, 0.9, 1, 0, '[]', 1, 'GODKENDT', 0, 9, '2026-09-29 15:05:00', '2026-09-29 15:07:00', 2),
  (1, 2, 2, 'Lone lærte selv at tage bussen til dagtilbuddet i dag, næste vagt skal huske at rose hende.',
   'Lone lærte selv at tage bussen til dagtilbuddet i dag. Næste vagt: husk at rose hende.',
   'UDVIKLING', 1.0, 0.92, 0, 1, '[]', 0, 'GODKENDT', 0, 14, '2026-09-30 08:40:00', '2026-09-30 08:40:03', 1);

INSERT INTO journal_entry (recording_id, resident_id, staff_id, target_system, target_field, category, text, created_at) VALUES
  (1, 1, 1, 'SOFUS', 'Døgnrapport – observationer', 'OBSERVATION', 'Kasper var glad efter frokost og spiste det hele.', '2026-09-29 13:10:05'),
  (2, 3, 2, 'SOFUS', 'Medicinmodul – PN-registrering', 'MEDICIN', 'Mo fik 10 mg Atarax kl. 15, fordi han var meget urolig.', '2026-09-29 15:07:00'),
  (3, 2, 1, 'SOFUS', 'Handleplan – udviklingsmål', 'UDVIKLING', 'Lone lærte selv at tage bussen til dagtilbuddet i dag. Næste vagt: husk at rose hende.', '2026-09-30 08:40:03'),
  (3, 2, 1, 'OUTLOOK', 'Vagtoverlevering til næste vagt', 'UDVIKLING', 'Lone lærte selv at tage bussen til dagtilbuddet i dag. Næste vagt: husk at rose hende.', '2026-09-30 08:40:03');
