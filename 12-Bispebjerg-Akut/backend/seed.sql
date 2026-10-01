-- Fiktive testdata – ingen rigtige patienter eller medarbejdere.
-- Tidspunkterne regnes ud fra "nu", så ventetiderne giver mening, uanset hvornår databasen oprettes.
INSERT INTO department (name) VALUES ('Røntgenafdelingen'), ('Laboratoriet'), ('CT-scanning');

INSERT INTO staff (name, role, department_id) VALUES
  ('Sanne (sygeplejerske)', 'SYGEPLEJERSKE', NULL), ('Karim (sygeplejerske)', 'SYGEPLEJERSKE', NULL),
  ('Lise (læge)', 'LÆGE', NULL),
  ('Per (Røntgenafdelingen)', 'AFDELING', 1), ('Ida (Laboratoriet)', 'AFDELING', 2);

INSERT INTO exam_type (name, department_id) VALUES ('Røntgen', 1), ('Blodprøver', 2), ('CT-scanning', 3);

INSERT INTO registration (reg_number, name, birth_date, language, symptoms, injury_type, pain_level, medication, allergies,
                          registered_from, fill_seconds, status, triage_level, triage_note, triaged_by, triaged_at,
                          created_at, arrived_at, closed_at) VALUES
  ('BBH-1001', 'Anders Testesen', '1958-03-14', 'da', 'Faldt på cyklen og har ondt i højre håndled, som er hævet.', 'FALD', 6,
   'Blodfortyndende (Eliquis)', 'Penicillin', 'HJEMMEFRA', 190, 'UNDERSØGELSE_BESTILT', 'GUL', 'Mistanke om brud på håndled.', 1,
   datetime('now', 'localtime', '-50 minutes'), datetime('now', 'localtime', '-95 minutes'), datetime('now', 'localtime', '-70 minutes'), NULL),
  ('BBH-1002', 'Fatima Prøve', '1991-11-02', 'da', 'Stærke mavesmerter siden i morges og kvalme.', 'SYGDOM', 8,
   '', '', 'VED_ANKOMST', 240, 'VENTER_PÅ_LÆGE', 'ORANGE', 'Øm i nederste højre del af maven.', 2,
   datetime('now', 'localtime', '-40 minutes'), datetime('now', 'localtime', '-60 minutes'), datetime('now', 'localtime', '-60 minutes'), NULL),
  ('BBH-1003', 'John Sample', '1975-06-21', 'en', 'Cut my finger with a kitchen knife, still bleeding a little.', 'SÅR', 3,
   '', 'Latex', 'VED_ANKOMST', 150, 'VENTER_PÅ_SYGEPLEJERSKE', NULL, NULL, NULL, NULL,
   datetime('now', 'localtime', '-25 minutes'), datetime('now', 'localtime', '-25 minutes'), NULL),
  ('BBH-1004', 'Maja Eksempel', '2003-01-30', 'da', 'Vrikkede om på anklen til håndbold. Kan ikke støtte på foden.', 'FORSTUVNING', 5,
   'P-piller', '', 'HJEMMEFRA', 130, 'REGISTRERET', NULL, NULL, NULL, NULL,
   datetime('now', 'localtime', '-10 minutes'), NULL, NULL),
  ('BBH-0907', 'Anders Testesen', '1958-03-14', 'da', 'Slog hovedet mod en skabslåge, kortvarig svimmelhed.', 'HOVEDSKADE', 4,
   'Blodfortyndende (Eliquis)', 'Penicillin', 'VED_ANKOMST', 210, 'AFSLUTTET', 'GUL', 'CT uden fund. Hjem med vejledning.', 1,
   '2026-08-12 10:20:00', '2026-08-12 10:05:00', '2026-08-12 10:05:00', '2026-08-12 12:40:00');

INSERT INTO status_event (registration_id, status, staff_id, created_at) VALUES
  (1, 'REGISTRERET', NULL, datetime('now', 'localtime', '-95 minutes')),
  (1, 'VENTER_PÅ_SYGEPLEJERSKE', NULL, datetime('now', 'localtime', '-70 minutes')),
  (1, 'UNDERSØGELSE_BESTILT', 1, datetime('now', 'localtime', '-50 minutes')),
  (2, 'REGISTRERET', NULL, datetime('now', 'localtime', '-60 minutes')),
  (2, 'VENTER_PÅ_SYGEPLEJERSKE', NULL, datetime('now', 'localtime', '-60 minutes')),
  (2, 'UNDERSØGELSE_BESTILT', 2, datetime('now', 'localtime', '-40 minutes')),
  (2, 'VENTER_PÅ_LÆGE', 5, datetime('now', 'localtime', '-15 minutes')),
  (3, 'REGISTRERET', NULL, datetime('now', 'localtime', '-25 minutes')),
  (3, 'VENTER_PÅ_SYGEPLEJERSKE', NULL, datetime('now', 'localtime', '-25 minutes')),
  (4, 'REGISTRERET', NULL, datetime('now', 'localtime', '-10 minutes')),
  (5, 'REGISTRERET', NULL, '2026-08-12 10:05:00'),
  (5, 'VENTER_PÅ_SYGEPLEJERSKE', NULL, '2026-08-12 10:05:00'),
  (5, 'UNDERSØGELSE_BESTILT', 1, '2026-08-12 10:20:00'),
  (5, 'VENTER_PÅ_LÆGE', 3, '2026-08-12 11:30:00'),
  (5, 'AFSLUTTET', 3, '2026-08-12 12:40:00');

INSERT INTO examination (registration_id, exam_type_id, ordered_by, status, ordered_at, completed_by, completed_at) VALUES
  (1, 1, 1, 'BESTILT', datetime('now', 'localtime', '-50 minutes'), NULL, NULL),
  (2, 2, 2, 'UDFØRT', datetime('now', 'localtime', '-40 minutes'), 5, datetime('now', 'localtime', '-15 minutes')),
  (5, 3, 1, 'UDFØRT', '2026-08-12 10:20:00', 3, '2026-08-12 11:30:00');

INSERT INTO access_log (staff_id, registration_id, action, created_at) VALUES
  (1, 1, 'Triage sat til GUL', datetime('now', 'localtime', '-50 minutes')),
  (1, 1, 'Bestilte undersøgelse: Røntgen', datetime('now', 'localtime', '-50 minutes')),
  (2, 2, 'Triage sat til ORANGE', datetime('now', 'localtime', '-40 minutes')),
  (2, 2, 'Bestilte undersøgelse: Blodprøver', datetime('now', 'localtime', '-40 minutes')),
  (5, 2, 'Markerede Blodprøver som udført', datetime('now', 'localtime', '-15 minutes'));
