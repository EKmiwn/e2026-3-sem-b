-- Fiktive testdata. Runderne dateres i forhold til i dag, så der altid er én åben runde og to afsluttede
INSERT INTO school (name, city) VALUES ('Nordskolen', 'Roskilde'), ('Søndre Skole', 'Køge');

INSERT INTO class (school_id, name, grade) VALUES (1, '7.A', 7), (1, '7.B', 7), (2, '8.A', 8);

INSERT INTO app_user (name, username, role, class_id, school_id) VALUES
  ('Læringsrum 2.0 (administrator)', 'admin', 'ADMINISTRATOR', NULL, NULL),
  ('Hanne (lærer 7.A)', 'hanne', 'LÆRER', 1, 1),
  ('Jens (lærer 7.B)', 'jens', 'LÆRER', 2, 1),
  ('Birgit (lærer 8.A)', 'birgit', 'LÆRER', 3, 2),
  ('Asta', 'asta', 'ELEV', 1, 1), ('Bilal', 'bilal', 'ELEV', 1, 1), ('Clara', 'clara', 'ELEV', 1, 1),
  ('Dennis', 'dennis', 'ELEV', 1, 1), ('Emilie', 'emilie', 'ELEV', 1, 1), ('Frederik', 'frederik', 'ELEV', 1, 1),
  ('Gustav', 'gustav', 'ELEV', 2, 1), ('Hiba', 'hiba', 'ELEV', 2, 1), ('Ida', 'ida', 'ELEV', 2, 1), ('Jonas', 'jonas', 'ELEV', 2, 1),
  ('Karla', 'karla', 'ELEV', 3, 2), ('Lukas', 'lukas', 'ELEV', 3, 2), ('Mira', 'mira', 'ELEV', 3, 2);

INSERT INTO question (text, category, emoji, sort) VALUES
  ('Jeg er glad for at gå i min klasse', 'TRIVSEL', '😊', 1),
  ('Jeg har nogen at være sammen med i frikvartererne', 'TRIVSEL', '🤝', 2),
  ('Jeg føler mig tryg i klassen', 'TRIVSEL', '🛡️', 3),
  ('Jeg kan koncentrere mig i timerne', 'LÆRING', '🎯', 4),
  ('Jeg kan følge med i undervisningen', 'LÆRING', '📚', 5),
  ('Jeg får hjælp, når jeg har brug for det', 'LÆRING', '🙋', 6),
  ('Min stol og mit bord er gode at sidde ved', 'MØBLER', '🪑', 7),
  ('Der er et sted i klassen, hvor jeg kan arbejde i ro', 'MØBLER', '🛋️', 8),
  ('Der er ro i klassen, når vi arbejder', 'MILJØ', '🔇', 9),
  ('Klasselokalet er et rart sted at være', 'MILJØ', '🌿', 10);

INSERT INTO survey_round (name, opens_on, closes_on) VALUES
  ('Måling 1 – før nye møbler', date('now', 'localtime', '-60 days'), date('now', 'localtime', '-46 days')),
  ('Måling 2 – efter nye møbler', date('now', 'localtime', '-30 days'), date('now', 'localtime', '-16 days')),
  ('Måling 3', date('now', 'localtime', '-2 days'), date('now', 'localtime', '+12 days'));

-- Alle elever har svaret i måling 1 og 2. I måling 3 har kun nogle svaret (8.A har for få svar til at blive vist)
INSERT INTO response (student_id, round_id, comment, submitted_at)
SELECT u.id, r.id,
       CASE WHEN u.id = 6 AND r.id = 1 THEN 'Der er meget larm, når vi har gruppearbejde.'
            WHEN u.id = 9 AND r.id = 2 THEN 'De nye stole er meget bedre!' END,
       r.opens_on || ' 10:00:00'
FROM app_user u, survey_round r
WHERE u.role = 'ELEV' AND (r.id IN (1, 2) OR u.id IN (5, 6, 7, 8, 11, 12, 13, 15, 16));

-- Svarene er fiktive: møbler og miljø bliver bedre fra måling til måling, trivsel og læring er nogenlunde stabile
INSERT INTO answer (response_id, question_id, value)
SELECT resp.id, q.id,
       MAX(1, MIN(5, 2 + (resp.student_id + q.id * 2) % 3 +
           CASE WHEN q.category IN ('MILJØ', 'MØBLER') THEN resp.round_id - 2 ELSE resp.student_id % 2 END))
FROM response resp, question q;

INSERT INTO follow_up (class_id, teacher_id, category, text, created_at) VALUES
  (1, 2, 'MILJØ', 'Vi har indført et stille hjørne og lydabsorberende plader i klassen.', date('now', 'localtime', '-40 days') || ' 12:00:00'),
  (1, 2, 'MØBLER', 'Nye hæve-sænkeborde og stole er på plads.', date('now', 'localtime', '-35 days') || ' 12:00:00');
