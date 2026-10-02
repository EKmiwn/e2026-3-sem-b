"""Hovedstadens Letbane – rejseassistent (PendlerKids). Flask API (logiklag).

Kravgrundlag: ../kravspec.md – navne og typer følger data dictionary i afsnit 5, endepunkterne afsnit 9.2.
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5211

Alle id'er er strings (afsnit 5.7), så projektet bruger egne endepunkter i stedet for register_crud() fra core.py.
Driftsdata er simulerede (C-5): afgange for driftsdøgnet oprettes ud fra køreplanen, og forsinkelser simuleres.
Billetkøb, point og belønninger samt live-positioner er tilføjet efter ønske fra gruppen. Betalingen er simuleret.
"""
import math
import os
import secrets
import uuid
import zlib
from datetime import date, datetime, time, timedelta

from flask import jsonify, request

from core import ApiError, create_app, json_body, require, run
from database import init_db, query_all, query_one, transaction

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Copenhagen")                        # BR-6
except Exception:                                             # fx Windows uden tzdata
    TZ = datetime.now().astimezone().tzinfo

PORT = int(os.environ.get("PORT", 5211))
app = create_app(__name__, "Hovedstadens Letbane")

DELAY_LIMIT_MIN = 2                  # BR-2 (antagelse A-2)
FIRST, LAST = time(5, 0), time(23, 55)
PEAK = (time(6, 0), time(19, 0))     # hvert 5. minut i dagtimerne, ellers hvert 10.
BOOL_FIELDS = {"er_skiftestation", "har_elevator", "cykelparkering", "stor_tekst", "notifikationer_til"}
PRIS_PR_ZONE_KR = 12                 # fiktiv takst: voksen 12 kr. pr. zone, mindst 2 zoner – barn halv pris
POINT_PR_REJSE = 10


# ---------------------------------------------------------------- Tid (BR-6: ISO 8601 med tidszone)
def cph_now():
    return datetime.now(TZ)


def iso(dt):
    return dt.isoformat(timespec="seconds")


def parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(TZ)


def as_json(row):
    """Booleans som true/false (data dictionary 5.3)."""
    return {k: bool(v) if k in BOOL_FIELDS and v is not None else v for k, v in row.items()}


def staff():
    """S-2: oprettelse af driftsmeddelelser kræver personale-adgang (header X-Personale-Id)."""
    pid = request.headers.get("X-Personale-Id")
    person = query_one("SELECT personale_id, rolle FROM personale WHERE personale_id = ?", (pid,)) if pid else None
    if person is None:
        raise ApiError("Kræver personale-adgang (header X-Personale-Id)", 401)
    return person


# ---------------------------------------------------------------- Køreplan → afgange og stoptider for et driftsdøgn
def ensure_day(day):
    """Opretter dagens afgange og stoptider ud fra rute og rutestop (én gang pr. driftsdøgn)."""
    if query_one("SELECT 1 FROM afgang WHERE dato = ? LIMIT 1", (day.isoformat(),)):
        return
    afgange, stoptider, vehicle = [], [], 0
    for rute in query_all("SELECT * FROM rute ORDER BY rute_id"):
        stops = query_all("SELECT * FROM rutestop WHERE rute_id = ? ORDER BY raekkefoelge", (rute["rute_id"],))
        t = datetime.combine(day, FIRST, TZ)
        while t.time() <= LAST and t.date() == day:
            afgang_id = f"A-{day:%Y%m%d}-{rute['retning'][0]}-{t:%H%M}"
            vehicle = vehicle % 12 + 1
            afgange.append((afgang_id, rute["rute_id"], f"LT-{vehicle:02d}", day.isoformat(), iso(t)))
            offset = 0
            for i, stop in enumerate(stops):
                offset += stop["koeretid_fra_forrige_sek"] + (stops[i - 1]["holdetid_sek"] if i else 0)
                stoptider.append((afgang_id, stop["station_id"], stop["raekkefoelge"], iso(t + timedelta(seconds=offset))))
            t += timedelta(minutes=rute["frekvens_min"] if PEAK[0] <= t.time() < PEAK[1] else 10)
    with transaction() as db:
        db.executemany("INSERT INTO afgang (afgang_id, rute_id, koeretoej_id, dato, planlagt_afgang) VALUES (?, ?, ?, ?, ?)", afgange)
        db.executemany("INSERT INTO stoptid (afgang_id, station_id, raekkefoelge, planlagt_ankomst) VALUES (?, ?, ?, ?)", stoptider)
    recompute(day)


def simulated_realtime(afgang_id):
    """Simuleret realtidssystem (BE-4): ca. 12 % af afgangene forsinkes 2–7 min fra et stop, ca. 2 % aflyses helt."""
    h = zlib.crc32(afgang_id.encode())
    r = h % 100
    return {"aflyst": r < 2, "delay": 2 + (h // 100) % 6 if 2 <= r < 14 else (1 if r < 20 else 0),
            "from_stop": (h // 1000) % 11 + 1}


def recompute(day):
    """Beregner forventet tid, forsinkelse og aflysning for dagens stoptider (BR-1, BR-2) –
    ud fra realtidssimuleringen og aktive driftsmeddelelser om aflysning."""
    messages = query_all("SELECT * FROM driftsmeddelelse WHERE type = 'AFLYSNING'")
    for m in messages:
        m["stations"] = {r["station_id"] for r in query_all(
            "SELECT station_id FROM driftsmeddelelse_station WHERE meddelelse_id = ?", (m["meddelelse_id"],))}
        m["start"] = parse(m["start_tid"])
        m["slut"] = parse(m["forventet_slut_tid"]) if m["forventet_slut_tid"] else None
    stops = query_all("""SELECT s.* FROM stoptid s JOIN afgang a ON a.afgang_id = s.afgang_id
                         WHERE a.dato = ? ORDER BY s.afgang_id, s.raekkefoelge""", (day.isoformat(),))
    updates, statuses, affected = [], {}, set()
    for s in stops:
        sim = simulated_realtime(s["afgang_id"])
        planned = parse(s["planlagt_ankomst"])
        hit = [m for m in messages if s["station_id"] in m["stations"] and m["start"] <= planned
               and (m["slut"] is None or planned <= m["slut"])]
        cancelled = sim["aflyst"] or bool(hit)
        delay = 0 if cancelled or s["raekkefoelge"] < sim["from_stop"] else sim["delay"]
        affected.update((m["meddelelse_id"], s["afgang_id"]) for m in hit)
        updates.append((None if cancelled else iso(planned + timedelta(minutes=delay)), delay, int(cancelled),
                        s["afgang_id"], s["station_id"]))
        st = statuses.setdefault(s["afgang_id"], {"n": 0, "aflyst": 0, "max_delay": 0})
        st["n"] += 1
        st["aflyst"] += cancelled
        st["max_delay"] = max(st["max_delay"], delay)
    with transaction() as db:
        db.executemany("""UPDATE stoptid SET forventet_ankomst = ?, forsinkelse_min = ?, er_aflyst = ?
                          WHERE afgang_id = ? AND station_id = ?""", updates)
        db.executemany("UPDATE afgang SET status = ? WHERE afgang_id = ?", [
            ("AFLYST" if st["aflyst"] == st["n"] else "DELVIST_AFLYST" if st["aflyst"] else
             "FORSINKET" if st["max_delay"] >= DELAY_LIMIT_MIN else "PLANLAGT", afgang_id)
            for afgang_id, st in statuses.items()])
        db.execute("DELETE FROM driftsmeddelelse_afgang WHERE afgang_id LIKE ?", (f"A-{day:%Y%m%d}-%",))
        db.executemany("INSERT INTO driftsmeddelelse_afgang (meddelelse_id, afgang_id) VALUES (?, ?)", sorted(affected))


def ensure_today():
    today = cph_now().date()
    ensure_day(today)
    ensure_day(today + timedelta(days=1))


def active_messages(now=None):
    now = now or cph_now()
    result = []
    for m in query_all("SELECT * FROM driftsmeddelelse ORDER BY start_tid DESC"):
        if parse(m["start_tid"]) <= now and (not m["forventet_slut_tid"] or now <= parse(m["forventet_slut_tid"])):
            result.append(message_json(m))
    order = {"KRITISK": 0, "ADVARSEL": 1, "INFO": 2}
    return sorted(result, key=lambda m: order[m["alvorlighed"]])


def message_json(m):
    """Driftsopdatering = meddelelse_id + type + alvorlighed + titel_da + tekst_da + {station_id} + (alternativ_rejse)."""
    afgange = [r["afgang_id"] for r in query_all(
        "SELECT afgang_id FROM driftsmeddelelse_afgang WHERE meddelelse_id = ? ORDER BY afgang_id", (m["meddelelse_id"],))]
    data = {k: v for k, v in m.items() if k != "oprettet_af"}     # D-4: intet om personale i det offentlige API
    data["beroerte_stationer"] = [r["station_id"] for r in query_all(
        "SELECT station_id FROM driftsmeddelelse_station WHERE meddelelse_id = ?", (m["meddelelse_id"],))]
    data["beroerte_afgange"] = afgange[:20]
    data["antal_beroerte_afgange"] = len(afgange)
    return data


# ---------------------------------------------------------------- F-1, F-12: stationer
@app.get("/api/stationer")
def stationer():
    """Liste af Station med tilgængelighed (elevator og cykelparkering)."""
    return jsonify([as_json(s) for s in query_all("""SELECT s.* FROM station s
                                                      JOIN rutestop r ON r.station_id = s.station_id AND r.rute_id = 'L-SYD'
                                                      ORDER BY r.raekkefoelge""")])


@app.get("/api/stationer/<station_id>")
def station(station_id):
    """Én station."""
    s = query_one("SELECT * FROM station WHERE station_id = ?", (station_id.upper(),))
    if s is None:
        raise ApiError(f"Stationen {station_id} findes ikke", 404)
    return jsonify(as_json(s))


# ---------------------------------------------------------------- F-1 – F-3: afgangstavle
@app.get("/api/stationer/<station_id>/afgange")
def afgangstavle(station_id):
    """Afgangstavle = station_id + opdateret_tid + {Afgangslinje} for de næste afgange i begge retninger."""
    station_id = station_id.upper()
    if not query_one("SELECT 1 FROM station WHERE station_id = ?", (station_id,)):
        raise ApiError(f"Stationen {station_id} findes ikke", 404)
    ensure_today()
    now = cph_now()
    limit = request.args.get("antal", default=6, type=int)
    lines = []
    for rute in query_all("SELECT r.*, s.navn AS mod FROM rute r JOIN station s ON s.station_id = r.slut_station_id ORDER BY r.retning DESC"):
        rows = query_all("""SELECT st.*, a.rute_id, a.status AS afgang_status, a.planlagt_afgang AS start_planlagt
                            FROM stoptid st JOIN afgang a ON a.afgang_id = st.afgang_id
                            WHERE st.station_id = ? AND a.rute_id = ? AND st.raekkefoelge < 12
                              AND st.planlagt_ankomst >= ? ORDER BY st.planlagt_ankomst LIMIT ?""",
                         (station_id, rute["rute_id"], iso(now - timedelta(minutes=2)), limit))
        for r in rows:
            status = ("AFLYST" if r["er_aflyst"] else "FORSINKET" if r["forsinkelse_min"] >= DELAY_LIMIT_MIN
                      else "I_DRIFT" if parse(r["start_planlagt"]) <= now else "PLANLAGT")
            lines.append({"afgang_id": r["afgang_id"], "rute_id": r["rute_id"], "retning": rute["retning"], "mod": rute["mod"],
                          "planlagt_afgang": r["planlagt_ankomst"], "forventet_afgang": r["forventet_ankomst"],
                          "forsinkelse_min": r["forsinkelse_min"], "status": status})
    beroert = [m for m in active_messages(now) if station_id in m["beroerte_stationer"]]
    return jsonify(station_id=station_id, opdateret_tid=iso(now), afgange=lines, driftsmeddelelser=beroert)


# ---------------------------------------------------------------- F-7: skifteforbindelser
@app.get("/api/stationer/<station_id>/skift")
def skift(station_id):
    """Liste af Skifteforbindelse med transportmiddel og gangtid."""
    return jsonify(connections(station_id))


def connections(station_id):
    return query_all("""SELECT sk.*, t.type, t.linje, t.operatoer FROM skifteforbindelse sk
                        JOIN transportmiddel t ON t.transportmiddel_id = sk.transportmiddel_id
                        WHERE sk.station_id = ? ORDER BY sk.gangtid_min""", (station_id.upper(),))


# ---------------------------------------------------------------- F-4, F-6, F-7: rejsesøgning
def travel_time_min(rute_id, fra_seq, til_seq):
    """BR-3: Σ køretid + Σ holdetid for mellemliggende stop."""
    stops = query_all("SELECT * FROM rutestop WHERE rute_id = ? AND raekkefoelge > ? AND raekkefoelge <= ? ORDER BY raekkefoelge",
                      (rute_id, fra_seq, til_seq))
    return round((sum(s["koeretid_fra_forrige_sek"] for s in stops) + sum(s["holdetid_sek"] for s in stops[:-1])) / 60)


@app.get("/api/rejse")
def rejse():
    """Rejseforslag = {Rejseben} + samlet_rejsetid_min + (Driftsmeddelelse). ?fra=&til=&tid= (ISO eller HH:MM)."""
    return jsonify(plan_trip((request.args.get("fra") or "").upper(), (request.args.get("til") or "").upper(),
                             request.args.get("tid")))


def plan_trip(fra, til, tid=None):
    if not fra or not til or fra == til:
        raise ApiError("Vælg to forskellige stationer (fra og til)")
    ensure_today()
    now = cph_now()
    if tid and len(tid) == 5:
        wanted = datetime.combine(now.date(), time.fromisoformat(tid), TZ)
    else:
        wanted = parse(tid) if tid else now
    rute = query_one("""SELECT r.* FROM rute r JOIN rutestop a ON a.rute_id = r.rute_id AND a.station_id = ?
                        JOIN rutestop b ON b.rute_id = r.rute_id AND b.station_id = ? WHERE a.raekkefoelge < b.raekkefoelge""",
                     (fra, til))
    if rute is None:
        raise ApiError("Stationen findes ikke på letbanen", 404)
    seq = {r["station_id"]: r["raekkefoelge"] for r in query_all("SELECT * FROM rutestop WHERE rute_id = ?", (rute["rute_id"],))}
    candidates = query_all("""SELECT a.afgang_id, a.status, f.planlagt_ankomst AS fra_planlagt, f.forventet_ankomst AS fra_forventet,
                                     f.forsinkelse_min, f.er_aflyst AS fra_aflyst,
                                     t.planlagt_ankomst AS til_planlagt, t.forventet_ankomst AS til_forventet, t.er_aflyst AS til_aflyst
                              FROM afgang a JOIN stoptid f ON f.afgang_id = a.afgang_id AND f.station_id = ?
                              JOIN stoptid t ON t.afgang_id = a.afgang_id AND t.station_id = ?
                              WHERE a.rute_id = ? AND f.planlagt_ankomst >= ? ORDER BY f.planlagt_ankomst LIMIT 12""",
                           (fra, til, rute["rute_id"], iso(wanted)))
    cancelled, chosen = [], None
    for c in candidates:
        # Aflyst ved fra, til eller et mellemliggende stop?
        between = query_one("""SELECT MAX(er_aflyst) AS aflyst FROM stoptid WHERE afgang_id = ?
                               AND raekkefoelge BETWEEN ? AND ?""", (c["afgang_id"], seq[fra], seq[til]))["aflyst"]
        if between:
            cancelled.append({"afgang_id": c["afgang_id"], "planlagt_afgang": c["fra_planlagt"], "status": "AFLYST"})
            continue
        chosen = c
        break
    stations = {s["station_id"]: s["navn"] for s in query_all("SELECT station_id, navn FROM station")}
    rute_stations = [s for s, n in sorted(seq.items(), key=lambda x: x[1]) if seq[fra] <= n <= seq[til]]
    messages = [m for m in active_messages(now) if set(m["beroerte_stationer"]) & set(rute_stations)]
    alternativ = next((m["alternativ_rejse"] for m in messages if m["alternativ_rejse"]), None)
    rejseben = []
    if chosen:
        rejseben.append({"type": "LETBANE", "afgang_id": chosen["afgang_id"], "rute_id": rute["rute_id"], "retning": rute["retning"],
                         "fra_station_id": fra, "til_station_id": til,
                         "planlagt_afgang": chosen["fra_planlagt"], "forventet_afgang": chosen["fra_forventet"],
                         "forsinkelse_min": chosen["forsinkelse_min"],
                         "status": "FORSINKET" if chosen["forsinkelse_min"] >= DELAY_LIMIT_MIN else "PLANLAGT",
                         "planlagt_ankomst": chosen["til_planlagt"], "forventet_ankomst": chosen["til_forventet"]})
        for sk in connections(til):
            rejseben.append({"type": "SKIFT", "station_id": til, "transportmiddel_id": sk["transportmiddel_id"],
                             "linje": sk["linje"], "transporttype": sk["type"], "gangtid_min": sk["gangtid_min"],
                             "beskrivelse": sk["beskrivelse"]})
    samlet = (round((parse(chosen["til_forventet"]) - parse(chosen["fra_forventet"])).total_seconds() / 60)
              if chosen else travel_time_min(rute["rute_id"], seq[fra], seq[til]))
    return dict(fra_station_id=fra, til_station_id=til, fra_navn=stations[fra], til_navn=stations[til],
                oensket_tidspunkt=iso(wanted), rejseben=rejseben, samlet_rejsetid_min=samlet,
                ventetid_min=round((parse(chosen["fra_forventet"]) - now).total_seconds() / 60) if chosen else None,
                aflyste_afgange=cancelled, alternativ_rejse=alternativ if (cancelled or not chosen) else None,
                driftsmeddelelser=messages, kan_gennemfoeres=chosen is not None)


# ---------------------------------------------------------------- F-5, F-6, F-11: driftsmeddelelser
@app.get("/api/driftsmeddelelser")
def driftsmeddelelser():
    """Liste af Driftsmeddelelse. ?aktive=true giver kun de aktive – KRITISK først."""
    if request.args.get("aktive") == "true":
        return jsonify(active_messages())
    return jsonify([message_json(m) for m in query_all("SELECT * FROM driftsmeddelelse ORDER BY start_tid DESC")])


@app.post("/api/driftsmeddelelser")
def opret_driftsmeddelelse():
    """Personale opretter en driftsmeddelelse (S-2). AFLYSNING markerer berørte afgange som aflyst.
    KRITISK udløser notifikation til brugere med berørte favoritrejser (BR-5)."""
    person = staff()
    if person["rolle"] not in ("TRAFIKLEDER", "KUNDESERVICE"):
        raise ApiError("Kun trafikledelse og kundeservice kan udsende driftsmeddelelser", 403)
    data = json_body()
    require(data, "type", "alvorlighed", "titel_da", "tekst_da")
    if data["type"] not in ("FORSINKELSE", "AFLYSNING", "SPORARBEJDE", "TEKNISK_FEJL", "ANDET"):
        raise ApiError("Ukendt type")
    if data["alvorlighed"] not in ("INFO", "ADVARSEL", "KRITISK"):
        raise ApiError("Ukendt alvorlighed")
    if len(data["titel_da"]) > 80 or len(data["tekst_da"]) > 500 or len(data.get("alternativ_rejse") or "") > 300:
        raise ApiError("Teksten er for lang (titel 80, tekst 500, alternativ rejse 300 tegn)")
    stations = [s.upper() for s in data.get("beroerte_stationer") or []]
    known = {r["station_id"] for r in query_all("SELECT station_id FROM station")}
    if set(stations) - known:
        raise ApiError("Ukendt station: " + ", ".join(sorted(set(stations) - known)))
    start = parse(data["start_tid"]) if data.get("start_tid") else cph_now()
    slut = parse(data["forventet_slut_tid"]) if data.get("forventet_slut_tid") else None
    if slut and slut <= start:
        raise ApiError("Forventet sluttid skal ligge efter starttid")
    number = query_one("SELECT COUNT(*) + 8813 AS n FROM driftsmeddelelse")["n"]
    meddelelse_id = f"M-{number}"
    with transaction() as db:
        db.execute("""INSERT INTO driftsmeddelelse (meddelelse_id, type, alvorlighed, titel_da, tekst_da, titel_en, tekst_en,
                                                    start_tid, forventet_slut_tid, alternativ_rejse, oprettet_af)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (meddelelse_id, data["type"], data["alvorlighed"], data["titel_da"].strip(), data["tekst_da"].strip(),
                    data.get("titel_en"), data.get("tekst_en"), iso(start), iso(slut) if slut else None,
                    data.get("alternativ_rejse"), person["personale_id"]))
        db.executemany("INSERT INTO driftsmeddelelse_station (meddelelse_id, station_id) VALUES (?, ?)",
                       [(meddelelse_id, s) for s in stations])
    ensure_today()
    recompute(cph_now().date())
    message = message_json(query_one("SELECT * FROM driftsmeddelelse WHERE meddelelse_id = ?", (meddelelse_id,)))
    notified = [b for b in query_all("SELECT bruger_id FROM bruger WHERE notifikationer_til = 1")
                if data["alvorlighed"] == "KRITISK" and favorites_hit(b["bruger_id"], message)]
    return jsonify(driftsmeddelelse=message, notificerede_brugere=len(notified)), 201


@app.put("/api/driftsmeddelelser/<meddelelse_id>/afslut")
def afslut(meddelelse_id):
    """Personale afslutter en driftsmeddelelse nu. Aflysninger for resten af dagen ophæves."""
    staff()
    m = query_one("SELECT * FROM driftsmeddelelse WHERE meddelelse_id = ?", (meddelelse_id,))
    if m is None:
        raise ApiError(f"Driftsmeddelelse {meddelelse_id} findes ikke", 404)
    with transaction() as db:
        db.execute("UPDATE driftsmeddelelse SET forventet_slut_tid = ? WHERE meddelelse_id = ?", (iso(cph_now()), meddelelse_id))
    recompute(cph_now().date())
    return jsonify(message_json(query_one("SELECT * FROM driftsmeddelelse WHERE meddelelse_id = ?", (meddelelse_id,))))


@app.get("/api/personale")
def personale():
    """Personale til det simulerede personale-login – kun id og rolle, aldrig navn (D-4)."""
    return jsonify(query_all("SELECT personale_id, rolle FROM personale ORDER BY personale_id"))


# ---------------------------------------------------------------- Bruger, favoritter og notifikationer (F-8, F-9, F-13)
@app.post("/api/brugere")
def opret_bruger():
    """Opretter en anonym bruger. bruger_id genereres som UUID – ingen navn eller e-mail (D-3)."""
    data = request.get_json(silent=True) or {}
    bruger_id = str(uuid.uuid4())
    with transaction() as db:
        db.execute("INSERT INTO bruger (bruger_id, sprog, stor_tekst, notifikationer_til, oprettet) VALUES (?, ?, ?, ?, ?)",
                   (bruger_id, data.get("sprog", "da"), int(bool(data.get("stor_tekst"))),
                    int(bool(data.get("notifikationer_til"))), iso(cph_now())))
    return jsonify(as_json(get_bruger(bruger_id))), 201


def get_bruger(bruger_id):
    b = query_one("SELECT * FROM bruger WHERE bruger_id = ?", (bruger_id,))
    if b is None:
        raise ApiError("Brugeren findes ikke", 404)
    return b


@app.get("/api/brugere/<bruger_id>")
def hent_bruger(bruger_id):
    """Brugerens indstillinger."""
    return jsonify(as_json(get_bruger(bruger_id)))


@app.put("/api/brugere/<bruger_id>")
def opdater_bruger(bruger_id):
    """Sprog (da/en), stor tekst og samtykke til notifikationer."""
    b = get_bruger(bruger_id)
    data = json_body()
    sprog = data.get("sprog", b["sprog"])
    if sprog not in ("da", "en"):
        raise ApiError("Sprog skal være da eller en")
    with transaction() as db:
        db.execute("UPDATE bruger SET sprog = ?, stor_tekst = ?, notifikationer_til = ? WHERE bruger_id = ?",
                   (sprog, int(bool(data.get("stor_tekst", b["stor_tekst"]))),
                    int(bool(data.get("notifikationer_til", b["notifikationer_til"]))), bruger_id))
    return jsonify(as_json(get_bruger(bruger_id)))


@app.get("/api/brugere/<bruger_id>/data")
def mine_data(bruger_id):
    """S-4: brugeren kan se, hvilke data der gemmes, og hvorfor."""
    b = get_bruger(bruger_id)
    return jsonify(bruger=as_json(b),
                   favoritter=query_all("SELECT * FROM favoritrejse WHERE bruger_id = ?", (bruger_id,)),
                   feedback=query_all("SELECT * FROM feedback WHERE bruger_id = ?", (bruger_id,)),
                   billetter=query_all("SELECT * FROM billet WHERE bruger_id = ?", (bruger_id,)),
                   point=point_status(bruger_id)["point"],
                   formaal={"billetter": "Dine købte billetter, så de kan vises ved billetkontrol",
                            "point": "Point for dine rejser, så du kan indløse belønninger",
                            "bruger_id": "Tilfældigt id, så dine favoritter og indstillinger kan huskes – uden navn eller e-mail",
                            "favoritter": "Viser status på dine faste rejser og giver besked ved forstyrrelser",
                            "feedback": "Bruges anonymt til at forbedre letbanen"})


@app.delete("/api/brugere/<bruger_id>")
def slet_bruger(bruger_id):
    """Slet brugeren og alle tilknyttede data (GDPR)."""
    get_bruger(bruger_id)
    with transaction() as db:
        db.execute("DELETE FROM bruger WHERE bruger_id = ?", (bruger_id,))
    return "", 204


@app.post("/api/favoritter")
def opret_favorit():
    """Gem en favoritrejse uden at oprette konto (F-8)."""
    data = json_body()
    require(data, "bruger_id", "fra_station_id", "til_station_id")
    get_bruger(data["bruger_id"])
    fra, til = data["fra_station_id"].upper(), data["til_station_id"].upper()
    if fra == til or not all(query_one("SELECT 1 FROM station WHERE station_id = ?", (s,)) for s in (fra, til)):
        raise ApiError("Vælg to forskellige stationer")
    navn = (data.get("navn") or "").strip()[:30] or None
    favorit_id = f"F-{uuid.uuid4().hex[:8]}"
    with transaction() as db:
        db.execute("""INSERT INTO favoritrejse (favorit_id, bruger_id, fra_station_id, til_station_id, navn, saedvanlig_tid)
                      VALUES (?, ?, ?, ?, ?, ?)""", (favorit_id, data["bruger_id"], fra, til, navn, data.get("saedvanlig_tid")))
    return jsonify(query_one("SELECT * FROM favoritrejse WHERE favorit_id = ?", (favorit_id,))), 201


@app.delete("/api/favoritter/<favorit_id>")
def slet_favorit(favorit_id):
    """Slet en favoritrejse."""
    with transaction() as db:
        db.execute("DELETE FROM favoritrejse WHERE favorit_id = ?", (favorit_id,))
    return "", 204


def stations_between(fra, til):
    rute = query_one("""SELECT a.rute_id, a.raekkefoelge AS f, b.raekkefoelge AS t FROM rutestop a
                        JOIN rutestop b ON b.rute_id = a.rute_id AND b.station_id = ?
                        WHERE a.station_id = ? AND a.raekkefoelge < b.raekkefoelge""", (til, fra))
    return {r["station_id"] for r in query_all("SELECT station_id FROM rutestop WHERE rute_id = ? AND raekkefoelge BETWEEN ? AND ?",
                                               (rute["rute_id"], rute["f"], rute["t"]))} if rute else set()


def favorites_hit(bruger_id, message):
    return [f for f in query_all("SELECT * FROM favoritrejse WHERE bruger_id = ?", (bruger_id,))
            if stations_between(f["fra_station_id"], f["til_station_id"]) & set(message["beroerte_stationer"])]


@app.get("/api/brugere/<bruger_id>/favoritter")
def favoritter(bruger_id):
    """Favoritrejser med næste afgang og status – status på favoritrejse på højst 2 tryk (G-1, U-2)."""
    get_bruger(bruger_id)
    result = []
    for f in query_all("""SELECT f.*, a.navn AS fra_navn, b.navn AS til_navn FROM favoritrejse f
                          JOIN station a ON a.station_id = f.fra_station_id JOIN station b ON b.station_id = f.til_station_id
                          WHERE f.bruger_id = ?""", (bruger_id,)):
        result.append({**f, "naeste": plan_trip(f["fra_station_id"], f["til_station_id"])})
    return jsonify(result)


@app.get("/api/brugere/<bruger_id>/notifikationer")
def notifikationer(bruger_id):
    """Notifikation = bruger_id + meddelelse_id + titel_da + (favorit_id) for KRITISKE meddelelser på favoritrejser (BR-5)."""
    b = get_bruger(bruger_id)
    if not b["notifikationer_til"]:
        return jsonify([])
    result = []
    for m in active_messages():
        if m["alvorlighed"] != "KRITISK":
            continue
        for f in favorites_hit(bruger_id, m):
            result.append({"bruger_id": bruger_id, "meddelelse_id": m["meddelelse_id"], "titel_da": m["titel_da"],
                           "titel_en": m["titel_en"], "favorit_id": f["favorit_id"], "favorit_navn": f["navn"],
                           "alternativ_rejse": m["alternativ_rejse"]})
    return jsonify(result)


# ---------------------------------------------------------------- Live tracker: hvor er letbanetogene lige nu?
@app.get("/api/live")
def live():
    """Positionen for alle letbanetog i drift lige nu, beregnet mellem forrige og næste stop ud fra forventet ankomst."""
    ensure_today()
    now = cph_now()
    rows = query_all("""SELECT st.afgang_id, st.station_id, st.forventet_ankomst, st.forsinkelse_min, a.rute_id, a.koeretoej_id,
                               r.retning, e.navn AS mod, s.navn, s.latitude, s.longitude
                        FROM stoptid st JOIN afgang a ON a.afgang_id = st.afgang_id JOIN rute r ON r.rute_id = a.rute_id
                        JOIN station e ON e.station_id = r.slut_station_id JOIN station s ON s.station_id = st.station_id
                        WHERE a.planlagt_afgang BETWEEN ? AND ? ORDER BY st.afgang_id, st.raekkefoelge""",
                     (iso(now - timedelta(minutes=80)), iso(now)))
    vehicles = []
    for prev, nxt in zip(rows, rows[1:]):
        if prev["afgang_id"] != nxt["afgang_id"] or not prev["forventet_ankomst"] or not nxt["forventet_ankomst"]:
            continue                                         # aflyste stop har ingen forventet tid
        start, end = parse(prev["forventet_ankomst"]), parse(nxt["forventet_ankomst"])
        if not start <= now < end:
            continue
        part = (now - start) / (end - start)
        vehicles.append({"afgang_id": nxt["afgang_id"], "koeretoej_id": nxt["koeretoej_id"], "rute_id": nxt["rute_id"],
                         "retning": nxt["retning"], "mod": nxt["mod"],
                         "latitude": round(prev["latitude"] + (nxt["latitude"] - prev["latitude"]) * part, 6),
                         "longitude": round(prev["longitude"] + (nxt["longitude"] - prev["longitude"]) * part, 6),
                         "forrige_station_id": prev["station_id"], "naeste_station_id": nxt["station_id"],
                         "naeste_station_navn": nxt["navn"], "forventet_ankomst": nxt["forventet_ankomst"],
                         "forsinkelse_min": nxt["forsinkelse_min"],
                         "status": "FORSINKET" if nxt["forsinkelse_min"] >= DELAY_LIMIT_MIN else "I_DRIFT"})
    return jsonify(opdateret_tid=iso(now), koeretoejer=vehicles)


# ---------------------------------------------------------------- Billetkøb i appen (betalingen er simuleret)
def ticket_price(fra, til):
    """Zoner og pris ud fra antal stop: 2 zoner for de første 3 stop, derefter én zone pr. 3 stop."""
    stops = len(stations_between(fra, til)) - 1
    if fra == til or stops < 1:
        raise ApiError("Vælg to forskellige stationer på letbanen")
    zoner = 1 + math.ceil(stops / 3)
    return {"zoner": zoner, "gyldighed_min": 60 + 15 * zoner,
            "priser": {"VOKSEN": zoner * PRIS_PR_ZONE_KR, "BARN": zoner * PRIS_PR_ZONE_KR // 2}}


TICKET_SQL = """SELECT b.*, f.navn AS fra_navn, t.navn AS til_navn FROM billet b
                JOIN station f ON f.station_id = b.fra_station_id JOIN station t ON t.station_id = b.til_station_id"""


def ticket_json(b):
    b["status"] = "BRUGT" if b["brugt_tid"] else "UDLOEBET" if parse(b["gyldig_til"]) < cph_now() else "GYLDIG"
    return b


@app.get("/api/billetpris")
def billetpris():
    """Zoner, gyldighed og pris pr. billettype for en rejse. ?fra=&til="""
    return jsonify(ticket_price((request.args.get("fra") or "").upper(), (request.args.get("til") or "").upper()))


@app.post("/api/billetter")
def koeb_billet():
    """Køb billet til en planlagt rejse. Betales med kort, MobilePay, rejsekredit eller en gratis billet fra belønningerne."""
    data = json_body()
    require(data, "bruger_id", "fra_station_id", "til_station_id")
    bruger = get_bruger(data["bruger_id"])
    fra, til = data["fra_station_id"].upper(), data["til_station_id"].upper()
    price = ticket_price(fra, til)
    billettype, antal, metode = data.get("billettype", "VOKSEN"), data.get("antal", 1), data.get("betalingsmetode", "KORT")
    if billettype not in price["priser"]:
        raise ApiError("Billettypen skal være VOKSEN eller BARN")
    if isinstance(antal, bool) or not isinstance(antal, int) or not 1 <= antal <= 9:
        raise ApiError("Antal skal være 1–9")
    if metode not in ("KORT", "MOBILEPAY", "REJSEKREDIT", "GRATIS_BILLET"):
        raise ApiError("Ukendt betalingsmetode")
    pris = price["priser"][billettype] * antal
    if metode == "GRATIS_BILLET":
        if bruger["gratis_billetter"] < 1:
            raise ApiError("Du har ingen gratis billetter. Indløs en under Belønninger", 409)
        if antal != 1:
            raise ApiError("En gratis billet gælder for én person")
        pris = 0
    if metode == "REJSEKREDIT" and bruger["rejsekredit_kr"] < pris:
        raise ApiError(f"Du har kun {bruger['rejsekredit_kr']} kr. i rejsekredit – billetten koster {pris} kr.", 409)
    now = cph_now()
    billet_id = f"BL-{uuid.uuid4().hex[:8]}"
    with transaction() as db:
        db.execute("""INSERT INTO billet (billet_id, bruger_id, fra_station_id, til_station_id, afgang_id, billettype, antal, zoner,
                                          pris_kr, betalingsmetode, kontrolkode, koebt_tid, gyldig_til)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (billet_id, bruger["bruger_id"], fra, til, data.get("afgang_id"), billettype, antal, price["zoner"], pris,
                    metode, secrets.token_hex(3).upper(), iso(now), iso(now + timedelta(minutes=price["gyldighed_min"]))))
        if metode == "GRATIS_BILLET":
            db.execute("UPDATE bruger SET gratis_billetter = gratis_billetter - 1 WHERE bruger_id = ?", (bruger["bruger_id"],))
        if metode == "REJSEKREDIT":
            db.execute("UPDATE bruger SET rejsekredit_kr = rejsekredit_kr - ? WHERE bruger_id = ?", (pris, bruger["bruger_id"]))
    return jsonify(ticket_json(query_one(TICKET_SQL + " WHERE b.billet_id = ?", (billet_id,)))), 201


@app.get("/api/brugere/<bruger_id>/billetter")
def billetter(bruger_id):
    """Brugerens billetter – nyeste først. status er GYLDIG, BRUGT eller UDLOEBET."""
    get_bruger(bruger_id)
    return jsonify([ticket_json(b) for b in query_all(TICKET_SQL + " WHERE b.bruger_id = ? ORDER BY b.koebt_tid DESC", (bruger_id,))])


@app.post("/api/billetter/<billet_id>/afslut")
def afslut_rejse(billet_id):
    """Afslut rejsen på en gyldig billet. Billetten bliver brugt, og brugeren optjener 10 point."""
    billet = query_one(TICKET_SQL + " WHERE b.billet_id = ?", (billet_id,))
    if billet is None:
        raise ApiError(f"Billetten {billet_id} findes ikke", 404)
    if ticket_json(billet)["status"] != "GYLDIG":
        raise ApiError("Billetten er allerede brugt eller udløbet", 409)
    before = point_status(billet["bruger_id"])["point"]
    with transaction() as db:
        db.execute("UPDATE billet SET brugt_tid = ? WHERE billet_id = ?", (iso(cph_now()), billet_id))
        db.execute("INSERT INTO point_transaktion (transaktion_id, bruger_id, point, type, billet_id, tidspunkt) VALUES (?, ?, ?, 'REJSE', ?, ?)",
                   (f"PT-{uuid.uuid4().hex[:8]}", billet["bruger_id"], POINT_PR_REJSE, billet_id, iso(cph_now())))
    status = point_status(billet["bruger_id"])
    unlocked = query_one("SELECT * FROM beloenning WHERE pris_point > ? AND pris_point <= ? ORDER BY pris_point DESC",
                         (before, status["point"]))
    return jsonify(billet=ticket_json(query_one(TICKET_SQL + " WHERE b.billet_id = ?", (billet_id,))),
                   optjent_point=POINT_PR_REJSE, besked_da=f"+{POINT_PR_REJSE} point – godt gået!",
                   besked_en=f"+{POINT_PR_REJSE} points – well done!", ny_beloenning=unlocked, point=status)


# ---------------------------------------------------------------- Point og belønninger
def point_status(bruger_id):
    """Saldo og fremskridt mod næste belønning (den billigste, brugeren endnu ikke har point nok til)."""
    bruger = get_bruger(bruger_id)
    totals = query_one("""SELECT COALESCE(SUM(point), 0) AS point, COALESCE(SUM(CASE WHEN point > 0 THEN point END), 0) AS optjent,
                                 COALESCE(SUM(type = 'REJSE'), 0) AS rejser FROM point_transaktion WHERE bruger_id = ?""", (bruger_id,))
    rewards = query_all("SELECT * FROM beloenning ORDER BY pris_point")
    upcoming = next((r for r in rewards if r["pris_point"] > totals["point"]), None)
    return {"bruger_id": bruger_id, "point": totals["point"], "optjent_i_alt": totals["optjent"], "antal_rejser": totals["rejser"],
            "point_pr_rejse": POINT_PR_REJSE, "naeste_beloenning": upcoming,
            "mangler_point": upcoming["pris_point"] - totals["point"] if upcoming else 0,
            "fremskridt_pct": min(100, round(100 * totals["point"] / upcoming["pris_point"])) if upcoming else 100,
            "kan_indloeses": [r["beloenning_id"] for r in rewards if r["pris_point"] <= totals["point"]],
            "rejsekredit_kr": bruger["rejsekredit_kr"], "gratis_billetter": bruger["gratis_billetter"]}


@app.get("/api/beloenninger")
def beloenninger():
    """De belønninger, point kan bruges på – billigste først."""
    return jsonify(query_all("SELECT * FROM beloenning ORDER BY pris_point"))


@app.get("/api/brugere/<bruger_id>/point")
def point(bruger_id):
    """Brugerens point, fremskridt mod næste belønning, indløste belønninger og de seneste 20 bevægelser."""
    return jsonify(**point_status(bruger_id),
                   indloesninger=query_all("""SELECT i.*, b.type, b.navn_da, b.navn_en FROM indloesning i
                                              JOIN beloenning b ON b.beloenning_id = i.beloenning_id
                                              WHERE i.bruger_id = ? ORDER BY i.tidspunkt DESC""", (bruger_id,)),
                   historik=query_all("""SELECT p.transaktion_id, p.point, p.type, p.tidspunkt, f.navn AS fra_navn, t.navn AS til_navn,
                                                b.navn_da, b.navn_en
                                         FROM point_transaktion p LEFT JOIN billet bl ON bl.billet_id = p.billet_id
                                         LEFT JOIN station f ON f.station_id = bl.fra_station_id
                                         LEFT JOIN station t ON t.station_id = bl.til_station_id
                                         LEFT JOIN indloesning i ON i.indloesning_id = p.indloesning_id
                                         LEFT JOIN beloenning b ON b.beloenning_id = i.beloenning_id
                                         WHERE p.bruger_id = ? ORDER BY p.tidspunkt DESC LIMIT 20""", (bruger_id,)))


@app.post("/api/brugere/<bruger_id>/indloesninger")
def indloes(bruger_id):
    """Brug point på en belønning: gratis billet, rejsekredit eller en større belønning med kode."""
    status = point_status(bruger_id)
    reward = query_one("SELECT * FROM beloenning WHERE beloenning_id = ?", (json_body().get("beloenning_id"),))
    if reward is None:
        raise ApiError("Belønningen findes ikke", 404)
    if status["point"] < reward["pris_point"]:
        raise ApiError(f"Du mangler {reward['pris_point'] - status['point']} point til denne belønning", 409)
    indloesning_id = f"IL-{uuid.uuid4().hex[:8]}"
    with transaction() as db:
        db.execute("INSERT INTO indloesning (indloesning_id, bruger_id, beloenning_id, kode, tidspunkt) VALUES (?, ?, ?, ?, ?)",
                   (indloesning_id, bruger_id, reward["beloenning_id"],
                    f"HL-{secrets.token_hex(3).upper()}" if reward["type"] == "STOR" else None, iso(cph_now())))
        db.execute("INSERT INTO point_transaktion (transaktion_id, bruger_id, point, type, indloesning_id, tidspunkt) VALUES (?, ?, ?, 'INDLOESNING', ?, ?)",
                   (f"PT-{uuid.uuid4().hex[:8]}", bruger_id, -reward["pris_point"], indloesning_id, iso(cph_now())))
        if reward["type"] == "GRATIS_BILLET":
            db.execute("UPDATE bruger SET gratis_billetter = gratis_billetter + 1 WHERE bruger_id = ?", (bruger_id,))
        if reward["type"] == "REJSEKREDIT":
            db.execute("UPDATE bruger SET rejsekredit_kr = rejsekredit_kr + ? WHERE bruger_id = ?", (reward["vaerdi_kr"], bruger_id))
    return jsonify(indloesning=query_one("SELECT * FROM indloesning WHERE indloesning_id = ?", (indloesning_id,)),
                   beloenning=reward, point=point_status(bruger_id)), 201


# ---------------------------------------------------------------- F-10: feedback og feedbackrapport (BE-7, BE-8)
@app.post("/api/feedback")
def opret_feedback():
    """Feedbackindsendelse = (bruger_id) + (afgang_id) + vurdering + kategori + (kommentar)."""
    data = json_body()
    require(data, "vurdering", "kategori")
    if not 1 <= int(data["vurdering"]) <= 5:
        raise ApiError("Vurdering skal være 1–5")
    if data["kategori"] not in ("PUNKTLIGHED", "INFORMATION", "PLADS", "SKIFT", "ANDET"):
        raise ApiError("Ukendt kategori")
    if len(data.get("kommentar") or "") > 300:
        raise ApiError("Kommentaren må højst være 300 tegn")
    if data.get("bruger_id"):
        get_bruger(data["bruger_id"])
    feedback_id = f"FB-{uuid.uuid4().hex[:8]}"
    with transaction() as db:
        db.execute("""INSERT INTO feedback (feedback_id, bruger_id, afgang_id, vurdering, kategori, kommentar, tidspunkt)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (feedback_id, data.get("bruger_id"), data.get("afgang_id"), int(data["vurdering"]), data["kategori"],
                    (data.get("kommentar") or "").strip() or None, iso(cph_now())))
    return jsonify(query_one("SELECT * FROM feedback WHERE feedback_id = ?", (feedback_id,))), 201


@app.get("/api/feedback/rapport")
def feedbackrapport():
    """Ugentlig feedbackrapport til personalet (BE-8): antal og gennemsnit pr. kategori de seneste 7 dage."""
    staff()
    since = cph_now() - timedelta(days=7)
    rows = [f for f in query_all("SELECT * FROM feedback ORDER BY tidspunkt DESC") if parse(f["tidspunkt"]) >= since]
    categories = {}
    for f in rows:
        c = categories.setdefault(f["kategori"], {"kategori": f["kategori"], "antal": 0, "sum": 0})
        c["antal"] += 1
        c["sum"] += f["vurdering"]
    return jsonify(periode_fra=iso(since), antal=len(rows),
                   gennemsnit=round(sum(f["vurdering"] for f in rows) / len(rows), 1) if rows else None,
                   kategorier=[{"kategori": c["kategori"], "antal": c["antal"], "gennemsnit": round(c["sum"] / c["antal"], 1)}
                               for c in sorted(categories.values(), key=lambda c: -c["antal"])],
                   kommentarer=[{"kategori": f["kategori"], "vurdering": f["vurdering"], "kommentar": f["kommentar"],
                                 "tidspunkt": f["tidspunkt"]} for f in rows if f["kommentar"]])


@app.get("/api/status")
def driftsstatus():
    """Punktlighed i dag indtil nu: andel afgange ≤ 2 min forsinket ved endestation (definition 5.1, antagelse A-2)."""
    ensure_today()
    now = cph_now()
    rows = query_all("""SELECT a.afgang_id, a.status, s.forsinkelse_min, s.planlagt_ankomst FROM afgang a
                        JOIN stoptid s ON s.afgang_id = a.afgang_id AND s.raekkefoelge = 12 WHERE a.dato = ?""",
                     (now.date().isoformat(),))
    done = [r for r in rows if parse(r["planlagt_ankomst"]) <= now]
    on_time = [r for r in done if r["status"] != "AFLYST" and r["forsinkelse_min"] <= DELAY_LIMIT_MIN]
    return jsonify(dato=now.date().isoformat(), afgange_i_dag=len(rows), gennemfoert=len(done),
                   punktlighed_pct=round(100 * len(on_time) / len(done)) if done else None,
                   aflyste=sum(r["status"] == "AFLYST" for r in rows),
                   delvist_aflyste=sum(r["status"] == "DELVIST_AFLYST" for r in rows),
                   forsinkede=sum(r["status"] == "FORSINKET" for r in rows),
                   aktive_meddelelser=len(active_messages(now)))


if __name__ == "__main__":
    init_db()
    run(app, PORT)
