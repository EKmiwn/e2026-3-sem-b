"""Movia – Den Forudsigelige Rejse. Flask API (logiklag).

Rejseguiden (POST /api/assistant) er en stemmeassistent: browseren omsætter tale til tekst og læser svaret højt.

Kravgrundlag: ../Kravspecifikation.md
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5201
"""
import os
import random
import re
import secrets
from datetime import datetime

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5201))
app = create_app(__name__, "Movia – Den Forudsigelige Rejse")

AREAS = ["FORREST", "MIDTEN", "BAGERST"]
CALM_LIMIT = 65      # score ≥ 65 = rolig
BUSY_LIMIT = 40      # score < 40 = travl


# ---------------------------------------------------------------- Tid
def to_minutes(hhmm):
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def to_hhmm(minutes):
    minutes %= 24 * 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ---------------------------------------------------------------- Rolighed ud fra sensordata (P2)
def area_score(reading):
    """0–100, hvor 100 er helt roligt. Støj (40–80 dB) og trængsel (0–100 %) vægter lige meget."""
    noise_pct = min(100, max(0, (reading["noise_db"] - 40) / 40 * 100))
    return round(100 - (noise_pct + reading["crowding_pct"]) / 2)


def calm_level(score):
    if score >= CALM_LIMIT:
        return "ROLIG"
    return "MIDDEL" if score >= BUSY_LIMIT else "TRAVL"


def bus_calm(bus):
    """Sensorisk varmekort for én bus: seneste måling pr. område + samlet vurdering (FR2)."""
    readings = query_all("""SELECT r.* FROM sensor_reading r
                            WHERE r.bus_id = ? AND r.id = (SELECT MAX(id) FROM sensor_reading
                                                            WHERE bus_id = r.bus_id AND area = r.area)""",
                         (bus["id"],))
    areas = []
    for area in AREAS:
        reading = next((r for r in readings if r["area"] == area), None)
        if reading:
            score = area_score(reading)
            areas.append({"area": area, "noise_db": reading["noise_db"], "crowding_pct": reading["crowding_pct"],
                          "score": score, "level": calm_level(score), "measured_at": reading["measured_at"],
                          "quiet_zone": bus["quiet_zone"] == area})
    average = round(sum(a["score"] for a in areas) / len(areas)) if areas else 0
    zone = next((a for a in areas if a["quiet_zone"]), None)
    # Har bussen en rolig zone, er det dér, passageren sidder – så zonen tæller i vurderingen
    expected = zone["score"] if zone else average
    return {"bus_id": bus["id"], "bus_number": bus["number"], "quiet_zone": bus["quiet_zone"],
            "average_score": average, "expected_score": expected, "level": calm_level(expected),
            "updated_at": max((a["measured_at"] for a in areas), default=None), "areas": areas}


# ---------------------------------------------------------------- CRUD
register_crud(app, "stops", "stop", fields=["name"], required=["name"], order_by="name")
register_crud(app, "lines", "line", fields=["name", "description"], read_only=True, order_by="name")
register_crud(app, "buses", "bus", fields=["number", "line_id", "quiet_zone"], required=["number", "line_id"],
              update_fields=["quiet_zone"])
register_crud(app, "passengers", "passenger",
              fields=["name", "school", "sunflower_enabled", "voice_guide", "notify_stops_before"],
              required=["name"])
register_crud(app, "sensor-readings", "sensor_reading", fields=["bus_id", "area", "noise_db", "crowding_pct"],
              required=["bus_id", "area", "noise_db", "crowding_pct"], defaults={"measured_at": now},
              order_by="id DESC")


# ---------------------------------------------------------------- P1 Planlæg rolig rejse (FR1, FR8)
def find_journeys(from_id, to_id, wanted=None):
    """De næste afgange mellem to stop. Den roligste (sensordata) er markeret med is_calmest."""
    if not from_id or not to_id or from_id == to_id:
        raise ApiError("Vælg to forskellige stoppesteder")
    from_stop, to_stop = get_or_404("stop", from_id, "Stoppested"), get_or_404("stop", to_id, "Stoppested")
    wanted = wanted or datetime.now().strftime("%H:%M")
    try:
        to_minutes(wanted)
    except ValueError:
        raise ApiError("Tidspunkt skal skrives som TT:MM, fx 07:45")

    lines = query_all("""SELECT l.id, l.name, a.seq AS from_seq, a.minutes_from_start AS from_min,
                                b.seq AS to_seq, b.minutes_from_start AS to_min
                         FROM line l JOIN line_stop a ON a.line_id = l.id AND a.stop_id = ?
                                     JOIN line_stop b ON b.line_id = l.id AND b.stop_id = ?
                         WHERE a.seq < b.seq""", (from_id, to_id))
    if not lines:
        raise ApiError(f"Ingen bus kører direkte fra {from_stop['name']} til {to_stop['name']}", 404)

    options = []
    for day_offset in (0, 1):        # efter sidste afgang vises morgendagens første afgange
        for line in lines:
            rows = query_all("""SELECT d.*, b.number, b.quiet_zone FROM departure d JOIN bus b ON b.id = d.bus_id
                                WHERE d.line_id = ? ORDER BY d.departs_at""", (line["id"],))
            upcoming = [r for r in rows
                        if to_minutes(r["departs_at"]) + line["from_min"] + day_offset * 1440 >= to_minutes(wanted)]
            for dep in upcoming[:3]:
                leave = to_minutes(dep["departs_at"]) + line["from_min"]
                options.append({"departure_id": dep["id"], "line": line["name"], "day": "i morgen" if day_offset else "i dag",
                                "leaves_at": to_hhmm(leave), "arrives_at": to_hhmm(leave + line["to_min"] - line["from_min"]),
                                "travel_min": line["to_min"] - line["from_min"],
                                "stops": line["to_seq"] - line["from_seq"],
                                "wait_min": leave + day_offset * 1440 - to_minutes(wanted),
                                "has_quiet_zone": dep["quiet_zone"] != "INGEN",
                                "calm": bus_calm({"id": dep["bus_id"], "number": dep["number"], "quiet_zone": dep["quiet_zone"]})})
        if options:
            break

    options = sorted(options, key=lambda o: o["wait_min"])[:6]
    calmest = max(options, key=lambda o: (o["calm"]["expected_score"], -o["wait_min"]))
    for option in options:
        option["is_calmest"] = option is calmest
    return dict(from_stop_id=from_id, to_stop_id=to_id, from_stop=from_stop["name"], to_stop=to_stop["name"], time=wanted,
                recommendation=f"Roligste rejse: {calmest['line']} kl. {calmest['leaves_at']}"
                               + (" – med rolig zone" if calmest["has_quiet_zone"] else ""),
                options=options)


@app.get("/api/journeys")
def search_journeys():
    """Søg afgange mellem to stop og foreslå den roligste (sensordata) blandt de næste afgange."""
    return jsonify(find_journeys(request.args.get("from_stop_id", type=int), request.args.get("to_stop_id", type=int),
                                 request.args.get("time")))


@app.get("/api/lines/<int:line_id>/stops")
def line_stops(line_id):
    """Linjens stoppesteder i rækkefølge med køretid fra første stop."""
    get_or_404("line", line_id, "Linje")
    return jsonify(query_all("""SELECT ls.seq, ls.minutes_from_start, s.id AS stop_id, s.name FROM line_stop ls
                                JOIN stop s ON s.id = ls.stop_id WHERE ls.line_id = ? ORDER BY ls.seq""", (line_id,)))


@app.get("/api/departures/<int:departure_id>/heatmap")
def heatmap(departure_id):
    """Sensorisk varmekort for én afgang: støj og trængsel forrest, i midten og bagerst (FR2, FR8)."""
    dep = get_or_404("departure", departure_id, "Afgang")
    bus = get_or_404("bus", dep["bus_id"], "Bus")
    line = get_or_404("line", dep["line_id"], "Linje")
    return jsonify(departure_id=dep["id"], line=line["name"], departs_at=dep["departs_at"], **bus_calm(bus))


# ---------------------------------------------------------------- Rejser (P3 solsikkesignal, P4 guid rejsen)
def trip_view(trip_id):
    trip = get_or_404("trip", trip_id, "Rejse")
    dep = query_one("""SELECT d.*, l.name AS line_name, b.number AS bus_number, b.quiet_zone
                       FROM departure d JOIN line l ON l.id = d.line_id JOIN bus b ON b.id = d.bus_id
                       WHERE d.id = ?""", (trip["departure_id"],))
    stops = query_all("""SELECT ls.seq, ls.minutes_from_start, s.id AS stop_id, s.name FROM line_stop ls
                         JOIN stop s ON s.id = ls.stop_id WHERE ls.line_id = ? ORDER BY ls.seq""", (dep["line_id"],))
    from_seq = next(s["seq"] for s in stops if s["stop_id"] == trip["from_stop_id"])
    to_seq = next(s["seq"] for s in stops if s["stop_id"] == trip["to_stop_id"])
    current = trip["current_seq"]
    timeline = []
    for s in stops:
        if from_seq <= s["seq"] <= to_seq:
            if current is None:
                state = "KOMMENDE"
            elif s["seq"] < current:
                state = "PASSERET"
            elif s["seq"] == current:
                state = "HER"
            else:
                state = "KOMMENDE"
            timeline.append({"seq": s["seq"], "name": s["name"], "state": state,
                             "time": to_hhmm(to_minutes(dep["departs_at"]) + s["minutes_from_start"]),
                             "is_destination": s["seq"] == to_seq})
    signal = query_one("SELECT token, stop_name, status, sent_at, acknowledged_at FROM sunflower_signal WHERE trip_id = ?",
                       (trip_id,))
    return {**trip, "line": dep["line_name"], "bus_number": dep["bus_number"], "quiet_zone": dep["quiet_zone"],
            "stops_left": to_seq - (current if current is not None else from_seq),
            "timeline": timeline, "signal": signal,
            "notifications": query_all("SELECT * FROM notification WHERE trip_id = ? ORDER BY id DESC", (trip_id,)),
            "feedback": query_one("SELECT * FROM feedback WHERE trip_id = ?", (trip_id,))}


def notify(db, trip_id, type_, message):
    db.execute("INSERT INTO notification (trip_id, type, message, created_at) VALUES (?, ?, ?, ?)",
               (trip_id, type_, message, now()))


@app.get("/api/passengers/<int:passenger_id>/trips")
def passenger_trips(passenger_id):
    """Passagerens rejser, nyeste først."""
    get_or_404("passenger", passenger_id, "Passager")
    return jsonify(query_all("""SELECT t.id, t.status, t.created_at, l.name AS line, d.departs_at,
                                       f.name AS from_stop, s.name AS to_stop
                                FROM trip t JOIN departure d ON d.id = t.departure_id JOIN line l ON l.id = d.line_id
                                JOIN stop f ON f.id = t.from_stop_id JOIN stop s ON s.id = t.to_stop_id
                                WHERE t.passenger_id = ? ORDER BY t.id DESC""", (passenger_id,)))


def make_trip(passenger_id, departure_id, from_stop_id, to_stop_id):
    get_or_404("passenger", passenger_id, "Passager")
    dep = get_or_404("departure", departure_id, "Afgang")
    seqs = {r["stop_id"]: r["seq"] for r in query_all("SELECT stop_id, seq FROM line_stop WHERE line_id = ?",
                                                        (dep["line_id"],))}
    if seqs.get(from_stop_id, 99) >= seqs.get(to_stop_id, 0):
        raise ApiError("Afgangen kører ikke mellem de valgte stoppesteder i den retning")
    with transaction() as db:
        trip_id = db.execute("""INSERT INTO trip (passenger_id, departure_id, from_stop_id, to_stop_id, created_at)
                                VALUES (?, ?, ?, ?, ?)""",
                             (passenger_id, dep["id"], from_stop_id, to_stop_id, now())).lastrowid
        notify(db, trip_id, "ROLIG_RUTE", f"Din rejse er gemt. Bussen kører kl. {dep['departs_at']} fra første stop.")
    return trip_id


@app.post("/api/trips")
def create_trip():
    """Passageren vælger en afgang (AfgangValgt → RejseOprettet)."""
    data = json_body()
    require(data, "passenger_id", "departure_id", "from_stop_id", "to_stop_id")
    return jsonify(trip_view(make_trip(data["passenger_id"], data["departure_id"], data["from_stop_id"], data["to_stop_id"]))), 201


@app.get("/api/trips/<int:trip_id>")
def get_trip(trip_id):
    """Visuel tidslinje, solsikkesignal og notifikationer for én rejse (FR4)."""
    return jsonify(trip_view(trip_id))


@app.post("/api/trips/<int:trip_id>/board")
def board(trip_id):
    """Passageren tjekker ind ved boarding. Er solsikkesignalet slået til, sendes det diskret til chaufføren (FR3, FR6)."""
    do_board(trip_id)
    return jsonify(trip_view(trip_id))


def do_board(trip_id):
    trip = get_or_404("trip", trip_id, "Rejse")
    if trip["status"] != "PLANLAGT":
        raise ApiError("Du er allerede steget på denne rejse", 409)
    passenger = get_or_404("passenger", trip["passenger_id"], "Passager")
    dep = get_or_404("departure", trip["departure_id"], "Afgang")
    stop = get_or_404("stop", trip["from_stop_id"], "Stoppested")
    from_seq = query_one("SELECT seq FROM line_stop WHERE line_id = ? AND stop_id = ?",
                         (dep["line_id"], trip["from_stop_id"]))["seq"]
    with transaction() as db:
        db.execute("UPDATE trip SET status = 'OMBORD', current_seq = ?, boarded_at = ? WHERE id = ?",
                   (from_seq, now(), trip_id))
        if passenger["sunflower_enabled"]:
            db.execute("""INSERT INTO sunflower_signal (trip_id, bus_id, token, stop_name, sent_at)
                          VALUES (?, ?, ?, ?, ?)""",
                       (trip_id, dep["bus_id"], f"SOL-{secrets.token_hex(2).upper()}", stop["name"], now()))
            notify(db, trip_id, "SOLSIKKE_SENDT", "Chaufføren har fået et diskret solsikkesignal. Du behøver ikke sige noget.")
    advance_notifications(trip_id)


def advance_notifications(trip_id):
    """Sender tryghedsnotifikation, når passagerens stop nærmer sig (FR5)."""
    view = trip_view(trip_id)
    passenger = get_or_404("passenger", view["passenger_id"], "Passager")
    destination = view["timeline"][-1]["name"].rstrip(".")       # "Nørreport St." efterfulgt af punktum giver ellers ".."
    left = view["stops_left"]
    already = {n["type"] for n in view["notifications"]}
    with transaction() as db:
        if 0 < left <= passenger["notify_stops_before"] and "STOP_NÆRMER_SIG" not in already:
            notify(db, trip_id, "STOP_NÆRMER_SIG",
                   f"Om {left} stop skal du af ved {destination}. Gør dig klar i god tid." if left > 1
                   else f"Næste stop er {destination}. Tryk på stopknappen nu.")
        if left == 0:
            db.execute("UPDATE trip SET status = 'AFSLUTTET', finished_at = ? WHERE id = ?", (now(), trip_id))
            db.execute("UPDATE sunflower_signal SET status = 'AFSLUTTET' WHERE trip_id = ?", (trip_id,))
            notify(db, trip_id, "STÅ_AF_NU", f"Du er ved {destination}. Stå af her.")
            notify(db, trip_id, "FEEDBACK", "Hvordan var rejsen? Giv gerne kort feedback.")


@app.post("/api/trips/<int:trip_id>/advance")
def advance(trip_id):
    """Simulerer, at bussen kører til næste stop (i virkeligheden bussens GPS)."""
    trip = get_or_404("trip", trip_id, "Rejse")
    if trip["status"] != "OMBORD":
        raise ApiError("Rejsen er ikke i gang – tryk først 'Jeg er steget på'", 409)
    with transaction() as db:
        db.execute("UPDATE trip SET current_seq = current_seq + 1 WHERE id = ?", (trip_id,))
    advance_notifications(trip_id)
    return jsonify(trip_view(trip_id))


@app.post("/api/trips/<int:trip_id>/feedback")
def give_feedback(trip_id):
    """Feedback efter endt rejse (FR7)."""
    trip = get_or_404("trip", trip_id, "Rejse")
    if trip["status"] != "AFSLUTTET":
        raise ApiError("Feedback kan først gives, når rejsen er afsluttet", 409)
    data = json_body()
    require(data, "calm_rating")
    if not 1 <= int(data["calm_rating"]) <= 5:
        raise ApiError("Vurderingen skal være mellem 1 og 5")
    with transaction() as db:
        db.execute("""INSERT INTO feedback (trip_id, calm_rating, felt_safe, comment, created_at)
                      VALUES (?, ?, ?, ?, ?)""",
                   (trip_id, int(data["calm_rating"]), 1 if data.get("felt_safe") else 0, data.get("comment"), now()))
    return jsonify(trip_view(trip_id)), 201


# ---------------------------------------------------------------- Rejseguide: stemmeassistent, der guider rejsen og appen
# Prototypen genkender hensigten med nøgleord og svarer ud fra rejsens data. I et rigtigt produkt ville en sprogmodel
# forstå talen – svarene skal stadig bygge på de samme data, så guiden aldrig gætter på tider og stop.
STOP_ALIASES = {"hovedbanegården": "Københavns Hovedbanegård", "hovedbanen": "Københavns Hovedbanegård",
                "lufthavnen": "Københavns Lufthavn", "kastrup": "Københavns Lufthavn", "dragør": "Dragør Stationsplads",
                "gammel holte": "Gl. Holte", "rådhuspladsen": "Rådhuspladsen"}
SCREEN_HELP = {
    "plan": "Du er på Planlæg. Vælg hvor du rejser fra og til, og tryk på Find rolig rejse. Jeg viser den roligste bus øverst.",
    "trip": "Du er på Min rejse. Her ser du stoppene på din rejse. Tryk på Jeg er steget på, når du er i bussen. Så siger jeg til, før du skal af.",
    "profile": "Du er på Profil. Her vælger du, om chaufføren skal have et solsikkesignal, om jeg skal læse højt, og hvornår du vil have besked.",
}
QUIET_TEXT = {"FORREST": "forrest", "MIDTEN": "i midten", "BAGERST": "bagerst"}


def said(text, *words):
    return any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words)


def stops_in_text(text):
    """Stoppesteder nævnt i teksten, i den rækkefølge de bliver sagt. "st." og "københavns" kan udelades.
    prep er ordet lige før stoppet ("fra" eller "til"), så "til Nørreport fra Husum" også forstås rigtigt."""
    found = {}
    for stop in query_all("SELECT * FROM stop"):
        name = stop["name"].lower()
        names = {name, name.replace(" st.", ""), name.replace("københavns ", "")}
        names |= {alias for alias, target in STOP_ALIASES.items() if target == stop["name"]}
        positions = [m.start() for n in names for m in re.finditer(rf"(?<!\w){re.escape(n)}(?!\w)", text)]
        if positions:
            found[stop["id"]] = (min(positions), stop)
    return [{**stop, "prep": (text[:pos].split() or [""])[-1]} for pos, stop in sorted(found.values(), key=lambda x: x[0])]


def trip_summary(trip):
    """Kort status på rejsen i klart sprog."""
    destination = trip["timeline"][-1]
    zone = (f" Der er en rolig zone {QUIET_TEXT[trip['quiet_zone']]} i bussen." if trip["quiet_zone"] != "INGEN" else "")
    if trip["status"] == "PLANLAGT":
        first = trip["timeline"][0]
        return (f"Din bus er linje {trip['line']}. Den kører fra {first['name']} klokken {first['time']}.{zone} "
                "Sig til mig, når du er steget på.")
    if trip["status"] == "OMBORD":
        here = next((s["name"] for s in trip["timeline"] if s["state"] == "HER"), None)
        left = trip["stops_left"]
        return (f"Du er ved {here}. Der er {left} stop tilbage. Du skal af ved {destination['name']} klokken {destination['time']}. "
                + ("Næste stop er dit. Tryk på stopknappen nu." if left == 1 else "Du kan sidde roligt. Jeg siger til i god tid."))
    return f"Din rejse er slut. Du stod af ved {destination['name']}. Godt klaret."


@app.post("/api/assistant")
def assistant():
    """Rejseguiden: modtager det, passageren siger eller skriver, og svarer i klart sprog. Kan finde den roligste rejse,
    gemme den, tjekke passageren ind, fortælle hvor langt der er igen og forklare appen. action fortæller frontenden, hvad der skal vises."""
    data = json_body()
    require(data, "message")
    text = " ".join(str(data["message"]).lower().split()).strip(" .!?")
    passenger = get_or_404("passenger", data["passenger_id"], "Passager") if data.get("passenger_id") else None
    trip = trip_view(data["trip_id"]) if data.get("trip_id") else None
    if trip and passenger and trip["passenger_id"] != passenger["id"]:
        trip = None
    name = passenger["name"].split()[0] if passenger else ""
    stops = stops_in_text(text)

    def answer(intent, reply, **action):
        return jsonify(intent=intent, reply=reply.replace("..", "."), action=action or None)   # "Nørreport St.." → "St."

    # 1. Utryghed går forud for alt andet – ét roligt svar og det næste konkrete skridt
    if said(text, "bange", "nervøs", "stresset", "utryg", "panik", "angst", "urolig", "overvældet"):
        reply = "Det er helt okay. Træk vejret roligt. Du skal ikke gøre noget lige nu."
        if trip and trip["status"] == "OMBORD":
            reply += f" Der er {trip['stops_left']} stop tilbage, og jeg siger til, før du skal af."
            if trip["signal"]:
                reply += " Chaufføren har fået dit solsikkesignal og giver dig god tid."
        return answer("TRYGHED", reply)

    # 2. Tjek ind
    if said(text, "steget på", "stået på", "tjek ind", "er på bussen", "sidder i bussen", "ombord"):
        if not trip or trip["status"] != "PLANLAGT":
            return answer("BOARDING", "Du har ingen planlagt rejse at stige på. Sig hvor du vil hen, så finder jeg en rolig bus.")
        do_board(trip["id"])
        trip = trip_view(trip["id"])
        signal = " Chaufføren har fået et diskret solsikkesignal." if trip["signal"] else ""
        return answer("BOARDING", f"Godt. Du er tjekket ind.{signal} {trip_summary(trip)}", type="TRIP_UPDATED", trip_id=trip["id"])

    # 3. Ja tak til det foreslåede
    suggestion = data.get("suggestion") or {}
    if suggestion.get("departure_id") and said(text, "ja", "ja tak", "jo", "vælg", "gem", "den tager jeg", "okay", "ok", "fint"):
        if not passenger:
            raise ApiError("Vælg en passager først")
        trip_id = make_trip(passenger["id"], suggestion["departure_id"], suggestion["from_stop_id"], suggestion["to_stop_id"])
        return answer("VAELG_REJSE", "Rejsen er gemt. " + trip_summary(trip_view(trip_id)), type="TRIP_CREATED", trip_id=trip_id)
    if suggestion.get("departure_id") and said(text, "nej", "nej tak", "ikke"):
        return answer("AFVIS", "Okay. Jeg gemmer ikke rejsen. Du kan se de andre afgange på skærmen.")

    # 4. Planlæg en rejse
    if stops:
        if len(stops) >= 2:
            origin, target = stops[0], stops[1]
            if origin["prep"] == "til" or target["prep"] == "fra":
                origin, target = target, origin
        elif stops[0]["prep"] == "fra":
            return answer("PLANLAEG", f"Du rejser fra {stops[0]['name']}. Hvor vil du hen?")
        elif data.get("from_stop_id") and data["from_stop_id"] != stops[0]["id"]:
            origin, target = get_or_404("stop", data["from_stop_id"], "Stoppested"), stops[0]
        else:
            return answer("PLANLAEG", f"Du vil til {stops[0]['name']}. Hvor rejser du fra?")
        try:
            result = find_journeys(origin["id"], target["id"])
        except ApiError as err:
            return answer("PLANLAEG", f"{err.message}. Prøv et andet stoppested.")
        best = next(o for o in result["options"] if o["is_calmest"])
        zone = (f" Der er en rolig zone {QUIET_TEXT[best['calm']['quiet_zone']]} i bussen." if best["has_quiet_zone"]
                else " Bussen har ingen rolig zone.")
        level = {"ROLIG": "Der er roligt i bussen.", "MIDDEL": "Der er nogenlunde roligt i bussen.",
                 "TRAVL": "Der er desværre travlt i alle busser lige nu."}[best["calm"]["level"]]
        return answer("PLANLAEG",
                      f"Den roligste bus er linje {best['line']} klokken {best['leaves_at']} fra {result['from_stop']}. "
                      f"Du er fremme ved {result['to_stop']} klokken {best['arrives_at']}. {level}{zone} Skal jeg gemme rejsen?",
                      type="SHOW_JOURNEY", from_stop_id=origin["id"], to_stop_id=target["id"], departure_id=best["departure_id"])

    # 5. Hvor langt er der igen?
    if said(text, "hvornår", "hvor langt", "hvor er jeg", "hvor er vi", "stop tilbage", "næste stop", "skal af", "stå af", "status", "min rejse", "fremme"):
        if not trip:
            return answer("STATUS", "Du har ikke valgt en rejse endnu. Sig hvor du vil hen, så finder jeg en rolig bus.")
        return answer("STATUS", trip_summary(trip), type="OPEN_TAB", tab="trip")

    # 6. Ro og siddeplads
    if said(text, "rolig", "roligt", "roligst", "sidde", "larm", "støj", "plads", "fyldt", "mange mennesker"):
        if trip and trip["status"] != "AFSLUTTET":
            calm = bus_calm(query_one("SELECT b.* FROM bus b JOIN departure d ON d.bus_id = b.id WHERE d.id = ?", (trip["departure_id"],)))
            best = max(calm["areas"], key=lambda a: a["score"])
            return answer("ROLIGHED", f"Der er roligst {QUIET_TEXT[best['area']]} i bussen lige nu. Der er {best['crowding_pct']} procent fyldt."
                          + (f" Den rolige zone er {QUIET_TEXT[calm['quiet_zone']]}." if calm["quiet_zone"] != "INGEN" else ""))
        return answer("ROLIGHED", "Jeg finder altid den roligste bus til dig. Sig hvor du vil hen, så ser jeg på støj og trængsel i busserne.")

    # 7. Solsikkesignal
    if "solsikke" in text or "chauffør" in text:
        on = passenger and passenger["sunflower_enabled"]
        return answer("SOLSIKKE", "Solsikkesignalet er en diskret besked til chaufføren, når du stiger på. Chaufføren ser kun en kode, "
                      "aldrig dit navn. Så får du ekstra tid, uden at du skal sige noget. "
                      + ("Det er slået til hos dig." if on else "Det er slået fra hos dig. Du kan slå det til under Profil."))

    # 8. Linjer
    if said(text, "linje", "linjer", "busser", "hvilke", "hvor kører") or re.search(r"\b\d{1,3} ?[acs]\b", text):
        lines = query_all("SELECT * FROM line ORDER BY id")
        asked = next((l for l in lines if said(text, l["name"].lower(), f"{l['name'][:-1]} {l['name'][-1]}".lower())), None)
        if asked:
            names = [r["name"] for r in query_all("""SELECT s.name FROM line_stop ls JOIN stop s ON s.id = ls.stop_id
                                                     WHERE ls.line_id = ? ORDER BY ls.seq""", (asked["id"],))]
            return answer("LINJER", f"Linje {asked['name']} kører fra {names[0]} til {names[-1]}. Den stopper ved {', '.join(names[1:-1])}.")
        return answer("LINJER", "Jeg kender linjerne " + ", ".join(l["name"] for l in lines) + ". Sig for eksempel: Hvor kører 5C?")

    # 9. Hjælp til appen – afhænger af den skærm, passageren står på
    if said(text, "tak", "mange tak"):
        return answer("TAK", "Selv tak. Jeg er her hele vejen.")
    greeting = f"Hej {name}. " if said(text, "hej", "hejsa", "goddag", "start") else ""
    help_text = SCREEN_HELP.get(data.get("tab"), SCREEN_HELP["plan"])
    return answer("HJAELP", f"{greeting}Jeg er din rejseguide. {help_text} Du kan også bare sige, hvor du vil hen. "
                  "For eksempel: Jeg vil fra Husum Torv til Nørreport.")


# ---------------------------------------------------------------- Chauffør (P3)
@app.get("/api/buses/<int:bus_id>/signals")
def bus_signals(bus_id):
    """Chaufførens skærm: aktive solsikkesignaler – kun token og stop, aldrig navn (NFR2, NFR4)."""
    bus = get_or_404("bus", bus_id, "Bus")
    signals = query_all("""SELECT id, token, stop_name, status, sent_at, acknowledged_at FROM sunflower_signal
                           WHERE bus_id = ? AND status != 'AFSLUTTET' ORDER BY id DESC""", (bus_id,))
    return jsonify(bus=bus["number"], signals=signals)


@app.post("/api/signals/<int:signal_id>/ack")
def acknowledge_signal(signal_id):
    """Chaufføren bekræfter diskret, at signalet er set."""
    signal = get_or_404("sunflower_signal", signal_id, "Signal")
    if signal["status"] != "SENDT":
        raise ApiError("Signalet er allerede bekræftet eller afsluttet", 409)
    with transaction() as db:
        db.execute("UPDATE sunflower_signal SET status = 'SET_AF_CHAUFFØR', acknowledged_at = ? WHERE id = ?",
                   (now(), signal_id))
    return jsonify(get_or_404("sunflower_signal", signal_id))


# ---------------------------------------------------------------- Sensordata og drift (P2, NFR1)
@app.get("/api/fleet")
def fleet():
    """Alle busser med aktuelt varmekort."""
    buses = query_all("SELECT b.*, l.name AS line_name FROM bus b JOIN line l ON l.id = b.line_id ORDER BY b.number")
    return jsonify([{**bus_calm(b), "line": b["line_name"]} for b in buses])


@app.post("/api/sensors/simulate")
def simulate_sensors():
    """Simulerer, at alle busser sender en ny måling (i virkeligheden hvert få sekund)."""
    latest = query_all("""SELECT r.* FROM sensor_reading r
                          WHERE r.id IN (SELECT MAX(id) FROM sensor_reading GROUP BY bus_id, area)""")
    with transaction() as db:
        for r in latest:
            noise = min(90, max(40, r["noise_db"] + random.uniform(-6, 6)))
            crowd = min(100, max(0, r["crowding_pct"] + random.randint(-15, 15)))
            db.execute("""INSERT INTO sensor_reading (bus_id, area, noise_db, crowding_pct, measured_at)
                          VALUES (?, ?, ?, ?, ?)""", (r["bus_id"], r["area"], round(noise, 1), crowd, now()))
    return jsonify(readings=len(latest), measured_at=now()), 201


@app.get("/api/stats")
def stats():
    """Nøgletal for Movia: rejser, solsikkesignaler og feedback."""
    return jsonify(
        trips=query_one("SELECT COUNT(*) AS n FROM trip")["n"],
        trips_finished=query_one("SELECT COUNT(*) AS n FROM trip WHERE status = 'AFSLUTTET'")["n"],
        signals_sent=query_one("SELECT COUNT(*) AS n FROM sunflower_signal")["n"],
        signals_acknowledged=query_one("SELECT COUNT(*) AS n FROM sunflower_signal WHERE acknowledged_at IS NOT NULL")["n"],
        buses_with_quiet_zone=query_one("SELECT COUNT(*) AS n FROM bus WHERE quiet_zone != 'INGEN'")["n"],
        **query_one("""SELECT ROUND(AVG(calm_rating), 1) AS avg_calm_rating,
                              ROUND(100.0 * AVG(felt_safe)) AS felt_safe_pct FROM feedback"""),
        feedback=query_all("""SELECT f.*, l.name AS line FROM feedback f JOIN trip t ON t.id = f.trip_id
                              JOIN departure d ON d.id = t.departure_id JOIN line l ON l.id = d.line_id
                              ORDER BY f.id DESC LIMIT 20"""),
    )


if __name__ == "__main__":
    init_db()
    run(app, PORT)
