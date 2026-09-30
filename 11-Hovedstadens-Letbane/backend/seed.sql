-- Fiktive testdata (antagelse A-3: stationskoder, koordinater, køretider og kapacitet er ikke verificeret)
-- Afgange og stoptider for dagen oprettes af backenden ud fra rute og rutestop (D-5: køreplanen kan udskiftes her)

INSERT INTO station (station_id, navn, kommune, latitude, longitude, er_skiftestation, har_elevator, cykelparkering) VALUES
  ('LYN', 'Lyngby St.', 'Lyngby-Taarbæk', 55.768100, 12.503400, 1, 1, 1),
  ('DTU', 'DTU', 'Lyngby-Taarbæk', 55.785600, 12.521400, 0, 1, 1),
  ('AKA', 'Akademivej', 'Lyngby-Taarbæk', 55.781200, 12.515800, 0, 1, 0),
  ('GLT', 'Gladsaxe Trafikplads', 'Gladsaxe', 55.745300, 12.476500, 1, 1, 1),
  ('BUD', 'Buddinge St.', 'Gladsaxe', 55.746800, 12.493500, 1, 1, 1),
  ('GLR', 'Gladsaxe Rådhus', 'Gladsaxe', 55.733700, 12.487900, 0, 0, 1),
  ('HER', 'Herlev St.', 'Herlev', 55.719000, 12.443000, 1, 1, 1),
  ('HHO', 'Herlev Hospital', 'Herlev', 55.730600, 12.405000, 1, 1, 0),
  ('GLO', 'Glostrup St.', 'Glostrup', 55.665900, 12.402200, 1, 1, 1),
  ('ALB', 'Albertslund St.', 'Albertslund', 55.656800, 12.353300, 1, 1, 1),
  ('VAL', 'Vallensbæk St.', 'Vallensbæk', 55.623300, 12.384500, 1, 0, 1),
  ('ISH', 'Ishøj St.', 'Ishøj', 55.613100, 12.358300, 1, 1, 1);

INSERT INTO rute (rute_id, navn, retning, start_station_id, slut_station_id, frekvens_min, samlet_rejsetid_min) VALUES
  ('L-SYD', 'Lyngby → Ishøj', 'SYD', 'LYN', 'ISH', 5, 55),
  ('L-NORD', 'Ishøj → Lyngby', 'NORD', 'ISH', 'LYN', 5, 55);

-- Køretid fra forrige station (sek.) – samme strækning i begge retninger
INSERT INTO rutestop (rute_id, station_id, raekkefoelge, holdetid_sek, koeretid_fra_forrige_sek) VALUES
  ('L-SYD', 'LYN', 1, 0, 0), ('L-SYD', 'DTU', 2, 20, 180), ('L-SYD', 'AKA', 3, 20, 120), ('L-SYD', 'GLT', 4, 20, 420),
  ('L-SYD', 'BUD', 5, 30, 180), ('L-SYD', 'GLR', 6, 20, 180), ('L-SYD', 'HER', 7, 30, 300), ('L-SYD', 'HHO', 8, 20, 240),
  ('L-SYD', 'GLO', 9, 30, 480), ('L-SYD', 'ALB', 10, 20, 300), ('L-SYD', 'VAL', 11, 20, 300), ('L-SYD', 'ISH', 12, 0, 240),
  ('L-NORD', 'ISH', 1, 0, 0), ('L-NORD', 'VAL', 2, 20, 240), ('L-NORD', 'ALB', 3, 20, 300), ('L-NORD', 'GLO', 4, 30, 300),
  ('L-NORD', 'HHO', 5, 20, 480), ('L-NORD', 'HER', 6, 30, 240), ('L-NORD', 'GLR', 7, 20, 300), ('L-NORD', 'BUD', 8, 30, 180),
  ('L-NORD', 'GLT', 9, 20, 180), ('L-NORD', 'AKA', 10, 20, 420), ('L-NORD', 'DTU', 11, 20, 120), ('L-NORD', 'LYN', 12, 0, 180);

INSERT INTO skinnestraekning (straekning_id, fra_station_id, til_station_id, laengde_m, planlagt_koeretid_sek, status)
SELECT a.station_id || '-' || b.station_id, a.station_id, b.station_id, b.koeretid_fra_forrige_sek * 9, b.koeretid_fra_forrige_sek,
       CASE WHEN a.station_id = 'GLT' THEN 'SPORARBEJDE' ELSE 'AABEN' END
FROM rutestop a JOIN rutestop b ON b.rute_id = a.rute_id AND b.raekkefoelge = a.raekkefoelge + 1
WHERE a.rute_id = 'L-SYD';

INSERT INTO koeretoej (koeretoej_id, kapacitet, cykelpladser) VALUES
  ('LT-01', 210, 4), ('LT-02', 210, 4), ('LT-03', 210, 4), ('LT-04', 210, 4), ('LT-05', 210, 4), ('LT-06', 210, 4),
  ('LT-07', 210, 4), ('LT-08', 210, 4), ('LT-09', 210, 4), ('LT-10', 210, 4), ('LT-11', 210, 4), ('LT-12', 210, 4);

INSERT INTO transportmiddel (transportmiddel_id, type, linje, operatoer) VALUES
  ('STOG-A', 'S_TOG', 'A', 'DSB'), ('STOG-B', 'S_TOG', 'B', 'DSB'), ('STOG-C', 'S_TOG', 'C', 'DSB'), ('STOG-E', 'S_TOG', 'E', 'DSB'),
  ('BUS-300S', 'BUS', '300S', 'Movia'), ('BUS-400S', 'BUS', '400S', 'Movia'), ('BUS-150S', 'BUS', '150S', 'Movia'),
  ('RE-KB', 'REGIONALTOG', 'RE', 'DSB');

INSERT INTO skifteforbindelse (skifte_id, station_id, transportmiddel_id, gangtid_min, beskrivelse) VALUES
  ('SK-LYN-B', 'LYN', 'STOG-B', 3, 'Følg skilte mod S-tog, spor 1'),
  ('SK-LYN-300S', 'LYN', 'BUS-300S', 2, 'Busterminalen ved stationspladsen'),
  ('SK-GLT-150S', 'GLT', 'BUS-150S', 2, 'Stoppested på Motorring 3-broen'),
  ('SK-BUD-A', 'BUD', 'STOG-A', 4, 'Gå under broen til S-togsperronen'),
  ('SK-HER-C', 'HER', 'STOG-C', 3, 'Følg skilte mod S-tog, spor 1'),
  ('SK-HHO-400S', 'HHO', 'BUS-400S', 1, 'Stoppested foran hovedindgangen'),
  ('SK-GLO-B', 'GLO', 'STOG-B', 3, 'Rulletrappe op til S-tog'),
  ('SK-GLO-400S', 'GLO', 'BUS-400S', 2, 'Busterminal nord'),
  ('SK-ALB-B', 'ALB', 'STOG-B', 3, 'Elevator ved perronens nordende'),
  ('SK-VAL-A', 'VAL', 'STOG-A', 4, 'Gangbro over Køge Bugt Motorvejen'),
  ('SK-ISH-A', 'ISH', 'STOG-A', 3, 'Samme stationsbygning'),
  ('SK-ISH-E', 'ISH', 'STOG-E', 3, 'Samme stationsbygning'),
  ('SK-ISH-RE', 'ISH', 'RE-KB', 5, 'Regionaltog mod Køge, spor 3');

INSERT INTO personale (personale_id, rolle, navn) VALUES
  ('P-012', 'TOGFOERER', 'Kim Lund'), ('P-044', 'TRAFIKLEDER', 'Sanne Holm'), ('P-101', 'KUNDESERVICE', 'Omar Said');

INSERT INTO vagt (vagt_id, personale_id, afgang_id, start_tid, slut_tid) VALUES
  ('V-0001', 'P-044', NULL, strftime('%Y-%m-%dT05:00:00Z', 'now'), strftime('%Y-%m-%dT13:00:00Z', 'now'));

-- Driftsmeddelelser relativt til nu (UTC-tid med "Z" er ISO 8601 med tidszone, jf. D-2)
INSERT INTO driftsmeddelelse (meddelelse_id, type, alvorlighed, titel_da, tekst_da, titel_en, tekst_en, start_tid,
                              forventet_slut_tid, alternativ_rejse, oprettet_af) VALUES
  ('M-8812', 'AFLYSNING', 'KRITISK', 'Aflysninger Herlev–Glostrup',
   'På grund af en teknisk fejl på sporet kører letbanen ikke mellem Herlev St. og Glostrup St.',
   'Cancellations Herlev–Glostrup', 'Due to a technical fault on the track, the light rail is not running between Herlev St. and Glostrup St.',
   strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-20 minutes'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '+90 minutes'),
   'Tag bus 400S fra Herlev Hospital til Glostrup St. eller S-tog linje C fra Herlev St.', 'P-044'),
  ('M-8790', 'SPORARBEJDE', 'INFO', 'Sporarbejde ved Gladsaxe Trafikplads',
   'Nedsat hastighed mellem Gladsaxe Trafikplads og Buddinge St. Forvent op til 3 minutters forsinkelse.',
   'Track work at Gladsaxe Trafikplads', 'Reduced speed between Gladsaxe Trafikplads and Buddinge St. Expect up to 3 minutes delay.',
   strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-2 days'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '+5 days'), NULL, 'P-044'),
  ('M-8701', 'FORSINKELSE', 'ADVARSEL', 'Forsinkelser i morges', 'Signalfejl ved DTU gav forsinkelser. Fejlen er rettet.',
   'Delays this morning', 'A signal fault at DTU caused delays. The fault has been fixed.',
   strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-1 days'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-1 days', '+2 hours'), NULL, 'P-044');

INSERT INTO driftsmeddelelse_station (meddelelse_id, station_id) VALUES
  ('M-8812', 'HER'), ('M-8812', 'HHO'), ('M-8812', 'GLO'), ('M-8790', 'GLT'), ('M-8790', 'BUD'), ('M-8701', 'DTU');

INSERT INTO bruger (bruger_id, sprog, stor_tekst, notifikationer_til, oprettet) VALUES
  ('3f6c2a1e-demo-4b8e-9d11-joan00000001', 'da', 1, 1, strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-30 days'));

INSERT INTO favoritrejse (favorit_id, bruger_id, fra_station_id, til_station_id, navn, saedvanlig_tid) VALUES
  ('F-0001', '3f6c2a1e-demo-4b8e-9d11-joan00000001', 'LYN', 'GLO', 'Til arbejde', '07:10');

INSERT INTO feedback (feedback_id, bruger_id, afgang_id, vurdering, kategori, kommentar, tidspunkt) VALUES
  ('FB-0001', NULL, NULL, 2, 'PUNKTLIGHED', 'Toget var 6 minutter forsinket', strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-3 days')),
  ('FB-0002', NULL, NULL, 4, 'SKIFT', 'Nemt skift til S-tog i Herlev', strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-2 days')),
  ('FB-0003', NULL, NULL, 1, 'INFORMATION', 'Ingen besked om aflysningen på perronen', strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-1 days')),
  ('FB-0004', NULL, NULL, 5, 'PLADS', 'God plads til min cykel', strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-1 days')),
  ('FB-0005', NULL, NULL, 3, 'INFORMATION', NULL, strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-5 hours'));
