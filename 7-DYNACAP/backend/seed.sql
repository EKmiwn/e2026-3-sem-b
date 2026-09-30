-- Fiktive testdata. Varigheder er prototype-estimater (afsnit 6)
INSERT INTO office (name, country) VALUES ('København', 'DK'), ('Aarhus', 'DK'), ('Oslo', 'NO');

INSERT INTO person (name, email, role, office_id, language, mentor_id, start_date) VALUES
  ('Anne (HR)', 'anne@dynacap.test', 'HR', 1, 'da', NULL, NULL),
  ('Lars (ledelse)', 'lars@dynacap.test', 'LEDELSE', 1, 'da', NULL, NULL),
  ('Peter (vejleder)', 'peter@dynacap.test', 'VEJLEDER', 1, 'da', NULL, NULL),
  ('Ingrid (veileder)', 'ingrid@dynacap.test', 'VEJLEDER', 3, 'en', NULL, NULL),
  ('Emma', 'emma@dynacap.test', 'KONSULENT', 1, 'da', 3, '2026-06-01'),
  ('Noah', 'noah@dynacap.test', 'KONSULENT', 2, 'da', 3, '2026-09-01'),
  ('Sigrid', 'sigrid@dynacap.test', 'KONSULENT', 3, 'en', 4, '2026-04-01'),
  ('Magnus', 'magnus@dynacap.test', 'KONSULENT', 3, 'en', 4, '2026-08-15');

INSERT INTO level (number, title_da, title_en, goal_da, goal_en, learning_form, estimate_weeks_min, estimate_weeks_max, requires_certification) VALUES
  (1, 'Virksomheden', 'The company', 'Kan forklare DYNACAP''s ydelser og egen rolle og bruge de interne værktøjer',
      'Can explain DYNACAP''s services and own role and use the internal tools', 'Introforløb, fælles for DK og NO', 1, 2, NULL),
  (2, 'Salesforce-grundlag', 'Salesforce foundations', 'Kan navigere i Salesforce og lave simple opsætninger i et testmiljø',
      'Can navigate Salesforce and make simple configurations in a sandbox', 'Trailhead + intern øvelse', 3, 4, NULL),
  (3, 'DYNACAP-metoden', 'The DYNACAP method', 'Kan dokumentere krav og løsninger efter DYNACAP''s standard',
      'Can document requirements and solutions to DYNACAP''s standard', 'Intern case', 3, 4, NULL),
  (4, 'Projekt under supervision', 'Supervised project', 'Kan løse afgrænsede opgaver, som en vejleder gennemgår',
      'Can solve well-defined tasks that a mentor reviews', 'Projektorienteret', 6, 8, NULL),
  (5, 'Selvstændige opgaver', 'Independent tasks', 'Kan løse opgaver selvstændigt og har bestået Salesforce Administrator-certificeringen',
      'Can solve tasks independently and has passed the Salesforce Administrator certification', 'Projektorienteret + certificering', 8, 10, 'Salesforce Administrator'),
  (6, 'Fuldt oplært', 'Fully trained', 'Kan tage ansvar for et delområde og vejlede nye konsulenter på niveau 1–2',
      'Can take responsibility for an area and mentor new consultants on levels 1–2', 'Projektorienteret', 4, 6, NULL);

INSERT INTO activity (level_id, title_da, title_en, type, link, sort) VALUES
  (1, 'Velkomstdag og introduktion til DYNACAP', 'Welcome day and introduction to DYNACAP', 'INTRO', NULL, 1),
  (1, 'Gennemgå DYNACAP''s ydelser og kunder', 'Review DYNACAP''s services and customers', 'INTRO', NULL, 2),
  (1, 'Opsæt interne værktøjer (tid, Slack, Jira)', 'Set up internal tools (time, Slack, Jira)', 'ØVELSE', NULL, 3),
  (2, 'Trailhead: Admin Beginner', 'Trailhead: Admin Beginner', 'TRAILHEAD', 'https://trailhead.salesforce.com', 1),
  (2, 'Trailhead: Data Modeling', 'Trailhead: Data Modeling', 'TRAILHEAD', 'https://trailhead.salesforce.com', 2),
  (2, 'Intern øvelse: opsæt et objekt med felter og layout', 'Internal exercise: set up an object with fields and layout', 'ØVELSE', NULL, 3),
  (3, 'Læs DYNACAP''s projektmetode', 'Read the DYNACAP project method', 'INTRO', NULL, 1),
  (3, 'Intern case: skriv user stories og acceptkriterier', 'Internal case: write user stories and acceptance criteria', 'CASE', NULL, 2),
  (3, 'Dokumentér en løsning efter standarden', 'Document a solution to the standard', 'CASE', NULL, 3),
  (4, 'Første kundeopgave med gennemgang', 'First customer task with review', 'PROJEKT', NULL, 1),
  (4, 'Tre afgrænsede opgaver godkendt af vejleder', 'Three well-defined tasks approved by mentor', 'PROJEKT', NULL, 2),
  (5, 'Trailhead: Prepare for Admin Certification', 'Trailhead: Prepare for Admin Certification', 'TRAILHEAD', 'https://trailhead.salesforce.com', 1),
  (5, 'Selvstændig leverance til kunde', 'Independent customer delivery', 'PROJEKT', NULL, 2),
  (6, 'Ansvar for et delområde på et projekt', 'Responsibility for an area on a project', 'PROJEKT', NULL, 1),
  (6, 'Vejled en ny konsulent på niveau 1–2', 'Mentor a new consultant on levels 1–2', 'PROJEKT', NULL, 2),
  (6, 'Statussamtale', 'Status meeting', 'SAMTALE', NULL, 3);

INSERT INTO programme (consultant_id, created_by, created_at) VALUES
  (5, 1, '2026-06-01 09:00:00'), (6, 1, '2026-09-01 09:00:00'), (7, 1, '2026-04-01 09:00:00'), (8, 1, '2026-08-15 09:00:00');

-- Emma: niveau 1–2 godkendt, i gang med niveau 3
INSERT INTO activity_completion (consultant_id, activity_id, completed_at) VALUES
  (5, 1, '2026-06-01 15:00:00'), (5, 2, '2026-06-03 12:00:00'), (5, 3, '2026-06-04 10:00:00'),
  (5, 4, '2026-06-20 16:00:00'), (5, 5, '2026-07-01 11:00:00'), (5, 6, '2026-07-08 14:00:00'),
  (5, 7, '2026-07-15 10:00:00'),
-- Noah: to af tre aktiviteter på niveau 1
  (6, 1, '2026-09-01 15:00:00'), (6, 2, '2026-09-02 12:00:00'),
-- Sigrid: niveau 1–4 godkendt, alt på niveau 5 færdigt – mangler certificering
  (7, 1, '2026-04-01 15:00:00'), (7, 2, '2026-04-02 12:00:00'), (7, 3, '2026-04-03 10:00:00'),
  (7, 4, '2026-04-20 10:00:00'), (7, 5, '2026-04-28 10:00:00'), (7, 6, '2026-05-05 10:00:00'),
  (7, 7, '2026-05-12 10:00:00'), (7, 8, '2026-05-20 10:00:00'), (7, 9, '2026-05-28 10:00:00'),
  (7, 10, '2026-06-20 10:00:00'), (7, 11, '2026-07-25 10:00:00'),
  (7, 12, '2026-09-01 10:00:00'), (7, 13, '2026-09-20 10:00:00'),
-- Magnus: niveau 1 færdigt og afventer godkendelse
  (8, 1, '2026-08-15 15:00:00'), (8, 2, '2026-08-17 12:00:00'), (8, 3, '2026-08-18 10:00:00');

INSERT INTO level_review (consultant_id, level_id, mentor_id, decision, comment, reviewed_at) VALUES
  (5, 1, 3, 'GODKENDT', 'God start – kender vores ydelser.', '2026-06-10 10:00:00'),
  (5, 2, 3, 'AFVIST', 'Mangler page layouts i øvelsen.', '2026-07-09 10:00:00'),
  (5, 2, 3, 'GODKENDT', 'Nu er øvelsen på plads.', '2026-07-14 10:00:00'),
  (7, 1, 4, 'GODKENDT', 'Well done.', '2026-04-10 10:00:00'),
  (7, 2, 4, 'GODKENDT', 'Solid Trailhead work.', '2026-05-06 10:00:00'),
  (7, 3, 4, 'GODKENDT', 'Clear documentation.', '2026-06-01 10:00:00'),
  (7, 4, 4, 'GODKENDT', 'Ready for independent tasks.', '2026-07-28 10:00:00');
