"""Clever – forbedret ladeapp. Flask API (logiklag).

Kravgrundlag: ../Readme.MD (FR-1 – FR-16)
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5208

Brugeren vælges i frontenden og sendes i headeren X-User-Id (simuleret login).
Opladningen simuleres: ét sekund i virkeligheden svarer til ét minut ved standeren.
"""
import json
import math
import os
import random
import secrets
from datetime import datetime, timedelta

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5208))
app = create_app(__name__, "Clever")

SIM_MINUTES_PER_SECOND = 1          # simuleret ladetid
PRICE_WARNING_FACTOR = 1.25         # FR-11: advarsel ved > 25 % over brugerens gennemsnit
POWER_DROP_LIMIT = 0.7              # FR-7: forklaring ved fald > 30 %
PLACES = {                          # FR-13: byer og vejpunkter til ruteplanen (DK, SE, NO, DE)
    "Greve": (55.5886, 12.2990), "København": (55.6761, 12.5683), "Ringsted": (55.4426, 11.7902),
    "Odense": (55.4038, 10.4024), "Fredericia": (55.5657, 9.7527), "Kolding": (55.4904, 9.4722),
    "Aarhus": (56.1629, 10.2039), "Padborg": (54.8260, 9.3600), "Hamburg": (53.5511, 9.9937),
    "Malmö": (55.6050, 13.0038), "Helsingborg": (56.0465, 12.6945), "Göteborg": (57.7089, 11.9746),
    "Svinesund": (59.1000, 11.2700), "Oslo": (59.9139, 10.7522),
}
ORIGINS = ["Greve", "København"]
CORRIDORS = {                       # vejforløb fra Sjælland – ruten følger vejene, ikke luftlinjen over vandet
    "Odense": ["Ringsted", "Odense"],
    "Aarhus": ["Ringsted", "Odense", "Fredericia", "Aarhus"],
    "Padborg": ["Ringsted", "Odense", "Kolding", "Padborg"],
    "Hamburg": ["Ringsted", "Odense", "Kolding", "Padborg", "Hamburg"],
    "Malmö": ["København", "Malmö"],
    "Göteborg": ["København", "Malmö", "Helsingborg", "Göteborg"],
    "Oslo": ["København", "Malmö", "Helsingborg", "Göteborg", "Svinesund", "Oslo"],
}
ROAD_FACTOR = 1.15                  # vejen er lidt længere end de rette linjer mellem vejpunkterne

CONNECTOR_SQL = """SELECT cn.*, ch.code, ch.model, ch.max_power_kw, ch.location_id, l.name AS location_name,
                          l.price_area, l.country, o.name AS operator, o.is_clever,
                          t.price_per_kwh, t.start_fee, t.minute_price
                   FROM connector cn JOIN charger ch ON ch.id = cn.charger_id JOIN location l ON l.id = ch.location_id
                   JOIN operator o ON o.id = l.operator_id JOIN tariff t ON t.id = cn.tariff_id"""


# ---------------------------------------------------------------- Hjælpere
def dk(number, decimals=2):
    """Tal i dansk format (§16 CU-3): 3,49"""
    return f"{number:.{decimals}f}".replace(".", ",")


def current_user():
    user_id = request.headers.get("X-User-Id")
    user = query_one("SELECT * FROM app_user WHERE id = ?", (user_id,)) if user_id and user_id.isdigit() else None
    if user is None:
        raise ApiError("Log ind i appen (header X-User-Id mangler eller er ugyldig)", 401)
    return user


def distance_km(lat1, lng1, lat2, lng2):
    """Afstand i luftlinje (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def green_status(price_area, hour=None):
    """FR-8: andel vedvarende energi og g CO₂/kWh med kildeangivelse – kun dokumenterede data (CO-3)."""
    if not price_area:
        return None
    hour = datetime.now().hour if hour is None else hour
    return query_one("SELECT renewable_pct, gco2_per_kwh, source, price_area FROM energy_mix WHERE hour = ? AND price_area = ?",
                     (hour, price_area))


def user_average_price(user_id):
    """Brugerens gennemsnitlige pris pr. kWh de seneste 30 dage (FR-11)."""
    since = (datetime.now() - timedelta(days=30)).isoformat(sep=" ", timespec="seconds")
    row = query_one("""SELECT SUM(price_total) / SUM(kwh) AS avg FROM session
                       WHERE user_id = ? AND status = 'AFSLUTTET' AND started_at >= ? AND kwh > 0""", (user_id, since))
    return round(row["avg"], 2) if row and row["avg"] else None


def location_summary(loc):
    connectors = query_all(CONNECTOR_SQL + " WHERE ch.location_id = ? ORDER BY ch.code, cn.id", (loc["id"],))
    return {**loc,
            "free": sum(c["status"] == "LEDIG" for c in connectors),                     # FR-2
            "total": len(connectors),
            "out_of_order": sum(c["status"] == "UDE_AF_DRIFT" for c in connectors),
            "max_power_kw": max((c["max_power_kw"] for c in connectors), default=0),
            "min_price": min((c["price_per_kwh"] for c in connectors), default=None),
            "plugs": sorted({c["plug_type"] for c in connectors}),
            "updated_at": max((c["updated_at"] for c in connectors), default=None),
            "green": green_status(loc["price_area"]),
            "connectors": [{k: c[k] for k in ("id", "charger_id", "code", "plug_type", "status", "max_power_kw", "price_per_kwh",
                                               "start_fee", "minute_price", "updated_at")} for c in connectors]}


# ---------------------------------------------------------------- CRUD (drift og data)
register_crud(app, "operators", "operator", fields=["name", "is_clever"], required=["name"])
register_crud(app, "tariffs", "tariff", fields=["name", "price_per_kwh", "start_fee", "minute_price", "valid_from"],
              required=["name", "price_per_kwh", "valid_from"])
register_crud(app, "users", "app_user", fields=["name", "email", "language", "notify_faults", "notify_prices"],
              required=["name", "email"])
register_crud(app, "cars", "car", fields=["user_id", "model", "plug_type", "max_power_kw", "battery_kwh", "range_km"],
              required=["user_id", "model", "plug_type", "max_power_kw", "battery_kwh", "range_km"])
register_crud(app, "energy-mix", "energy_mix", fields=["hour", "price_area", "renewable_pct", "gco2_per_kwh", "source"],
              read_only=True, order_by="price_area, hour")


# ---------------------------------------------------------------- UC-1 Find ledig stander (FR-1, FR-2, FR-16)
@app.get("/api/locations")
def locations():
    """Lokationer med realtidsstatus, antal ledige udtag, effekt, pris og grøn status.
    Filtre: ?min_power=&plug=&max_price=&operator_id=&only_free=1&lat=&lng= (afstand)."""
    args = request.args
    lat, lng = args.get("lat", type=float), args.get("lng", type=float)
    result = []
    for loc in query_all("SELECT l.*, o.name AS operator, o.is_clever FROM location l JOIN operator o ON o.id = l.operator_id"):
        s = location_summary(loc)
        conns = s["connectors"]
        if args.get("plug"):
            conns = [c for c in conns if c["plug_type"] == args["plug"]]
        if args.get("min_power", type=float):
            conns = [c for c in conns if c["max_power_kw"] >= args.get("min_power", type=float)]
        if args.get("max_price", type=float):
            conns = [c for c in conns if c["price_per_kwh"] <= args.get("max_price", type=float)]
        if args.get("operator_id", type=int) and loc["operator_id"] != args.get("operator_id", type=int):
            continue
        if not conns or (args.get("only_free") == "1" and not any(c["status"] == "LEDIG" for c in conns)):
            continue
        s["distance_km"] = round(distance_km(lat, lng, loc["lat"], loc["lng"]), 1) if lat is not None and lng is not None else None
        result.append(s)
    result.sort(key=lambda s: (s["distance_km"] if s["distance_km"] is not None else 0, -s["free"], s["name"]))
    return jsonify(result)


@app.get("/api/locations/<int:location_id>/detail")
def location_detail(location_id):
    """Én lokation med alle standere og udtag."""
    loc = query_one("SELECT l.*, o.name AS operator, o.is_clever FROM location l JOIN operator o ON o.id = l.operator_id WHERE l.id = ?",
                    (location_id,))
    if loc is None:
        raise ApiError(f"Lokation med id {location_id} findes ikke", 404)
    return jsonify(location_summary(loc))


@app.put("/api/users/<int:user_id>/filters")
def save_filters(user_id):
    """Filtre bevares mellem sessioner (FR-16)."""
    get_or_404("app_user", user_id, "Bruger")
    with transaction() as db:
        db.execute("UPDATE app_user SET filters = ? WHERE id = ?", (json.dumps(json_body()), user_id))
    return jsonify(json.loads(get_or_404("app_user", user_id)["filters"]))


# ---------------------------------------------------------------- UC-2 Start opladning (FR-3, FR-4, FR-11)
def find_connector(data, user, car):
    """Standeren findes via placering (AUTO), QR-kode eller stander-ID. Et ledigt udtag med bilens stik vælges."""
    method = data.get("method", "ID")
    if method not in ("AUTO", "QR", "ID"):
        raise ApiError("Start med automatisk genkendelse, QR-kode eller stander-ID")
    if data.get("connector_id"):
        connector = query_one(CONNECTOR_SQL + " WHERE cn.id = ?", (data["connector_id"],))
    elif method == "AUTO":
        require(data, "lat", "lng")
        # Automatisk genkendelse: nærmeste stander inden for 150 m med et ledigt udtag til bilen
        candidates = [c for c in query_all(CONNECTOR_SQL + " WHERE cn.status = 'LEDIG' AND cn.plug_type = ?", (car["plug_type"],))]
        for c in candidates:
            loc = get_or_404("location", c["location_id"])
            c["distance_m"] = distance_km(data["lat"], data["lng"], loc["lat"], loc["lng"]) * 1000
        candidates = sorted((c for c in candidates if c["distance_m"] <= 150), key=lambda c: c["distance_m"])
        if not candidates:
            raise ApiError("Vi kunne ikke finde en ledig stander, hvor du står. Scan QR-koden eller skriv stander-ID'et.", 404)
        connector = candidates[0]
    else:
        require(data, "code")
        code = str(data["code"]).strip().upper()
        connectors = query_all(CONNECTOR_SQL + " WHERE ch.code = ? ORDER BY cn.status = 'LEDIG' DESC, cn.id", (code,))
        if not connectors:
            raise ApiError(f"Standeren {code} findes ikke. Tjek ID'et på standerens skilt.", 404)
        connector = next((c for c in connectors if c["plug_type"] == car["plug_type"] and c["status"] == "LEDIG"), connectors[0])
    if connector is None:
        raise ApiError("Udtaget findes ikke", 404)
    return connector


@app.post("/api/quote")
def quote():
    """Pris før start (FR-3), prisadvarsel i forhold til brugerens normale pris (FR-11) og grøn status nu (FR-8)."""
    user = current_user()
    data = json_body()
    car = query_one("SELECT * FROM car WHERE user_id = ?", (user["id"],))
    connector = find_connector(data, user, car)
    problems = []
    if connector["status"] != "LEDIG":
        problems.append("Udtaget er ude af drift. Vælg et andet udtag." if connector["status"] == "UDE_AF_DRIFT"
                        else "Udtaget er optaget.")
    if connector["plug_type"] != car["plug_type"]:
        problems.append(f"Udtaget har stikket {connector['plug_type']}, men din {car['model']} bruger {car['plug_type']}.")
    avg = user_average_price(user["id"])
    warning = None
    if avg and connector["price_per_kwh"] > avg * PRICE_WARNING_FACTOR:
        warning = (f"Prisen er {dk(connector['price_per_kwh'])} kr./kWh – {round(100 * (connector['price_per_kwh'] / avg - 1))} % "
                   f"over din normale pris på {dk(avg)} kr./kWh.")
    level = "GRØN" if not avg or connector["price_per_kwh"] <= avg else "GUL" if not warning else "RØD"
    return jsonify(connector={k: connector[k] for k in ("id", "code", "plug_type", "status", "max_power_kw", "location_name",
                                                         "operator", "is_clever")},
                   price_per_kwh=connector["price_per_kwh"], start_fee=connector["start_fee"],
                   minute_price=connector["minute_price"], your_average=avg, price_level=level, price_warning=warning,
                   green=green_status(connector["price_area"]), can_start=not problems, problems=problems,
                   expected_power_kw=min(car["max_power_kw"], connector["max_power_kw"]))


@app.post("/api/sessions")
def start_session():
    """Start opladning. Kræver, at prisen er vist og bekræftet (FR-3, AFIR). Pris og strømmix låses ved start."""
    user = current_user()
    data = json_body()
    if not data.get("price_confirmed"):
        raise ApiError("Bekræft prisen, før opladningen kan starte")
    if query_one("SELECT id FROM session WHERE user_id = ? AND status = 'AKTIV'", (user["id"],)):
        raise ApiError("Du har allerede en opladning i gang", 409)
    car = query_one("SELECT * FROM car WHERE user_id = ?", (user["id"],))
    connector = find_connector(data, user, car)
    if connector["status"] != "LEDIG":
        raise ApiError("Udtaget er ikke ledigt. Vælg et andet udtag.", 409)
    if connector["plug_type"] != car["plug_type"]:
        raise ApiError(f"Udtaget passer ikke til din bils stik ({car['plug_type']})")
    if data.get("quoted_price") is not None and abs(float(data["quoted_price"]) - connector["price_per_kwh"]) > 0.001:
        raise ApiError("Prisen er ændret, siden den blev vist. Se den nye pris og bekræft igen.", 409)
    green = green_status(connector["price_area"])
    with transaction() as db:
        session_id = db.execute(
            """INSERT INTO session (user_id, connector_id, car_id, start_method, price_per_kwh, start_fee, minute_price,
                                    battery_start_pct, renewable_pct, gco2_per_kwh, started_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], connector["id"], car["id"], data.get("method", "ID"), connector["price_per_kwh"],
             connector["start_fee"], connector["minute_price"], random.randint(15, 45),
             green["renewable_pct"] if green else None, green["gco2_per_kwh"] if green else None, now())).lastrowid
        db.execute("UPDATE connector SET status = 'OPTAGET', updated_at = ? WHERE id = ?", (now(), connector["id"]))
    return jsonify(live(session_id)), 201


# ---------------------------------------------------------------- UC-3 Følg opladning (FR-6, FR-7, FR-8)
def simulate(session, until=None):
    """Simulerer ladekurven minut for minut: fuld effekt til 80 %, derefter falder den. Delt effekt, hvis nabo-udtaget lader."""
    car = get_or_404("car", session["car_id"])
    connector = query_one(CONNECTOR_SQL + " WHERE cn.id = ?", (session["connector_id"],))
    started = datetime.fromisoformat(session["started_at"])
    end = datetime.fromisoformat(until) if until else datetime.now()
    minutes = min(600, int((end - started).total_seconds() * SIM_MINUTES_PER_SECOND))
    shared = query_one("""SELECT COUNT(*) AS n FROM connector WHERE charger_id = ? AND id != ? AND status = 'OPTAGET'""",
                       (connector["charger_id"], connector["id"]))["n"] > 0
    peak = min(car["max_power_kw"], connector["max_power_kw"])
    base = peak / 2 if shared else peak
    soc, kwh, power, curve = float(session["battery_start_pct"]), 0.0, base, []
    for minute in range(minutes):
        if soc >= 100:
            power = 0
            break
        power = base if soc < 80 else base * max(0.15, (100 - soc) / 20)
        added = power / 60
        kwh += added
        soc = min(100, soc + added / car["battery_kwh"] * 100)
        if minute % 5 == 0:
            curve.append({"minute": minute, "power_kw": round(power, 1)})
    reasons = []
    if shared:
        reasons.append("Standeren deler effekten med en anden bil på nabo-udtaget.")
    if soc >= 80:
        reasons.append("Batteriet er over 80 %. Bilen sænker effekten for at skåne batteriet.")
    if car["max_power_kw"] < connector["max_power_kw"]:
        reasons.append(f"Din {car['model']} kan højst lade med {car['max_power_kw']:g} kW.")
    price = kwh * session["price_per_kwh"] + session["start_fee"] + minutes * session["minute_price"]
    return {"minutes": minutes, "kwh": round(kwh, 2), "battery_pct": round(soc), "power_kw": round(power, 1),
            "peak_kw": peak, "price": round(price, 2), "curve": curve,
            "power_drop": power < connector["max_power_kw"] * POWER_DROP_LIMIT and minutes > 0,
            "explanation": reasons if power < connector["max_power_kw"] * POWER_DROP_LIMIT else [],
            "avg_power_kw": round(kwh / (minutes / 60), 1) if minutes else 0}


def live(session_id):
    session = get_or_404("session", session_id, "Opladning")
    connector = query_one(CONNECTOR_SQL + " WHERE cn.id = ?", (session["connector_id"],))
    data = {**session, "code": connector["code"], "location_name": connector["location_name"], "operator": connector["operator"],
            "green": ({"renewable_pct": session["renewable_pct"], "gco2_per_kwh": session["gco2_per_kwh"],
                       "source": "Energinet Energi Data Service (simuleret)"} if session["renewable_pct"] is not None else None)}
    if session["status"] == "AKTIV":
        data["live"] = simulate(session)
    data["payment"] = query_one("SELECT * FROM payment WHERE session_id = ?", (session_id,))
    return data


@app.get("/api/sessions/<int:session_id>")
def get_session(session_id):
    """Live effekt, kWh, løbende pris og grøn status – og forklaring, hvis effekten falder (FR-6 – FR-8)."""
    user = current_user()
    session = get_or_404("session", session_id, "Opladning")
    if session["user_id"] != user["id"]:
        raise ApiError("Du kan kun se dine egne opladninger", 403)
    return jsonify(live(session_id))


@app.get("/api/my/active-session")
def active_session():
    """Brugerens igangværende opladning – eller null."""
    user = current_user()
    row = query_one("SELECT id FROM session WHERE user_id = ? AND status = 'AKTIV'", (user["id"],))
    return jsonify(live(row["id"]) if row else None)


# ---------------------------------------------------------------- UC-4 Afslut og få kvittering (FR-5, SE-5)
@app.post("/api/sessions/<int:session_id>/stop")
def stop_session(session_id):
    """Stop opladningen. Kun brugeren, der startede den, kan stoppe den. Kvitteringen kommer med det samme."""
    user = current_user()
    session = get_or_404("session", session_id, "Opladning")
    if session["user_id"] != user["id"]:
        raise ApiError("Kun den bruger, der startede opladningen, kan stoppe den", 403)
    if session["status"] != "AKTIV":
        raise ApiError("Opladningen er allerede afsluttet", 409)
    result = simulate(session)
    subscription = query_one("SELECT * FROM subscription WHERE user_id = ?", (user["id"],))
    method = "Clever One" if subscription and subscription["type"] == "CLEVER_ONE" else "Kort"
    status = "GENNEMFØRT" if user["card_valid"] else "FEJLET"
    receipt = f"KV-{datetime.now():%y%m%d}-{secrets.token_hex(2).upper()}"
    with transaction() as db:
        db.execute("""UPDATE session SET status = 'AFSLUTTET', ended_at = ?, minutes = ?, kwh = ?, avg_power_kw = ?,
                             price_total = ? WHERE id = ?""",
                   (now(), result["minutes"], result["kwh"], result["avg_power_kw"], result["price"], session_id))
        db.execute("UPDATE connector SET status = 'LEDIG', updated_at = ? WHERE id = ?", (now(), session["connector_id"]))
        db.execute("""INSERT INTO payment (session_id, amount, method, status, receipt_no, created_at)
                      VALUES (?, ?, ?, ?, ?, ?)""", (session_id, result["price"], method, status, receipt, now()))
    data = live(session_id)
    data["receipt"] = {
        "receipt_no": receipt, "kwh": result["kwh"], "minutes": result["minutes"], "price": result["price"],
        "price_per_kwh": session["price_per_kwh"], "payment_status": status, "method": method,
        "co2_kg": round(result["kwh"] * session["gco2_per_kwh"] / 1000, 1) if session["gco2_per_kwh"] else None,
        "next_step": None if status == "GENNEMFØRT" else
        "Betalingen blev afvist, fordi dit kort er udløbet. Opdatér kortet under Profil – opladningen er registreret, og du trækkes først, når kortet er opdateret.",
    }
    return jsonify(data)


# ---------------------------------------------------------------- Favoritter og advarsler (FR-9, FR-10)
@app.get("/api/my/favorites")
def my_favorites():
    """Brugerens faste stop med status."""
    user = current_user()
    rows = query_all("""SELECT f.id AS favorite_id, f.label, l.*, o.name AS operator, o.is_clever FROM favorite f
                        JOIN location l ON l.id = f.location_id JOIN operator o ON o.id = l.operator_id
                        WHERE f.user_id = ? ORDER BY f.label""", (user["id"],))
    return jsonify([{**location_summary(r), "favorite_id": r["favorite_id"], "label": r["label"]} for r in rows])


@app.post("/api/my/favorites")
def add_favorite():
    """Gem en lokation som fast stop med et navn, fx "Hallen" (maks. 2 tryk)."""
    user = current_user()
    data = json_body()
    require(data, "location_id")
    loc = get_or_404("location", data["location_id"], "Lokation")
    with transaction() as db:
        db.execute("INSERT INTO favorite (user_id, location_id, label) VALUES (?, ?, ?)",
                   (user["id"], loc["id"], data.get("label") or loc["name"]))
    return jsonify(ok=True), 201


@app.delete("/api/my/favorites/<int:favorite_id>")
def delete_favorite(favorite_id):
    """Fjern et fast stop."""
    user = current_user()
    with transaction() as db:
        db.execute("DELETE FROM favorite WHERE id = ? AND user_id = ?", (favorite_id, user["id"]))
    return "", 204


@app.get("/api/my/alerts")
def my_alerts():
    """Push-advarsler til brugeren (nyeste først)."""
    user = current_user()
    return jsonify(query_all("SELECT * FROM alert WHERE user_id = ? ORDER BY id DESC LIMIT 20", (user["id"],)))


@app.put("/api/chargers/<int:charger_id>/status")
def set_charger_status(charger_id):
    """Drift (OCPP): standerens status ændres. Går den ude af drift, advares brugere med den som favorit (FR-10)."""
    charger = get_or_404("charger", charger_id, "Stander")
    data = json_body()
    require(data, "status")
    if data["status"] not in ("LEDIG", "UDE_AF_DRIFT"):
        raise ApiError("Status skal være LEDIG eller UDE_AF_DRIFT")
    loc = get_or_404("location", charger["location_id"])
    alerted = 0
    with transaction() as db:
        db.execute("UPDATE connector SET status = ?, updated_at = ? WHERE charger_id = ? AND status != 'OPTAGET'",
                   (data["status"], now(), charger_id))
        if data["status"] == "UDE_AF_DRIFT":
            alternative = nearest_free(loc, exclude_location=None, exclude_charger=charger_id)
            tail = f" – nærmeste ledige: {alternative['name']} ({dk(alternative['distance_km'], 1)} km)" if alternative else ""
            for fav in query_all("""SELECT f.user_id, f.label FROM favorite f JOIN app_user u ON u.id = f.user_id
                                    WHERE f.location_id = ? AND u.notify_faults = 1""", (loc["id"],)):
                db.execute("INSERT INTO alert (user_id, type, message, created_at) VALUES (?, 'FAVORIT_UDE_AF_DRIFT', ?, ?)",
                           (fav["user_id"], f"Standeren {charger['code']} ved {fav['label']} er ude af drift{tail}", now()))
                alerted += 1
    return jsonify(charger=charger["code"], status=data["status"], users_alerted=alerted)


def nearest_free(loc, exclude_location=None, exclude_charger=None):
    best = None
    for other in query_all("SELECT * FROM location"):
        if other["id"] == exclude_location:
            continue
        free = query_one("""SELECT COUNT(*) AS n FROM connector cn JOIN charger ch ON ch.id = cn.charger_id
                            WHERE ch.location_id = ? AND cn.status = 'LEDIG' AND ch.id != ?""",
                         (other["id"], exclude_charger or 0))["n"]
        if free:
            d = distance_km(loc["lat"], loc["lng"], other["lat"], other["lng"])
            if best is None or d < best["distance_km"]:
                best = {"id": other["id"], "name": other["name"], "distance_km": d}
    return best


# ---------------------------------------------------------------- UC-5 Rapportér fejl (FR-12)
@app.post("/api/fault-reports")
def report_fault():
    """Fejlrapport via guiden med kategori, beskrivelse og evt. foto – sendes til drift med stander-ID og placering."""
    user = current_user()
    data = json_body()
    require(data, "charger_code", "category")
    charger = query_one("SELECT * FROM charger WHERE code = ?", (str(data["charger_code"]).strip().upper(),))
    if charger is None:
        raise ApiError(f"Standeren {data['charger_code']} findes ikke. Tjek ID'et på skiltet.", 404)
    with transaction() as db:
        report_id = db.execute("""INSERT INTO fault_report (user_id, charger_id, category, description, photo, created_at)
                                  VALUES (?, ?, ?, ?, ?, ?)""",
                               (user["id"], charger["id"], data["category"], data.get("description"), data.get("photo"),
                                now())).lastrowid
    return jsonify(get_or_404("fault_report", report_id)), 201


@app.get("/api/fault-reports")
def fault_reports():
    """Fejlrapporter. Med X-User-Id kun brugerens egne (sagsstatus i appen) – uden: alle (drift)."""
    user_id = request.headers.get("X-User-Id")
    sql = """SELECT f.id, f.category, f.description, f.status, f.created_at, f.updated_at, f.photo IS NOT NULL AS has_photo,
                    ch.code, ch.id AS charger_id, l.name AS location_name, l.lat, l.lng, u.name AS user_name
             FROM fault_report f JOIN charger ch ON ch.id = f.charger_id JOIN location l ON l.id = ch.location_id
             JOIN app_user u ON u.id = f.user_id"""
    if user_id:
        return jsonify(query_all(sql + " WHERE f.user_id = ? ORDER BY f.id DESC", (current_user()["id"],)))
    return jsonify(query_all(sql + " ORDER BY f.status = 'LØST', f.id DESC"))


@app.put("/api/fault-reports/<int:report_id>")
def update_fault(report_id):
    """Drift opdaterer sagens status. Brugeren får besked."""
    report = get_or_404("fault_report", report_id, "Fejlrapport")
    data = json_body()
    require(data, "status")
    if data["status"] not in ("MODTAGET", "UNDER_BEHANDLING", "LØST"):
        raise ApiError("Ugyldig status")
    charger = get_or_404("charger", report["charger_id"])
    with transaction() as db:
        db.execute("UPDATE fault_report SET status = ?, updated_at = ? WHERE id = ?", (data["status"], now(), report_id))
        db.execute("INSERT INTO alert (user_id, type, message, created_at) VALUES (?, 'SAG_OPDATERET', ?, ?)",
                   (report["user_id"], f"Din fejlrapport om {charger['code']} er nu: {data['status'].replace('_', ' ').lower()}", now()))
    return jsonify(get_or_404("fault_report", report_id))


# ---------------------------------------------------------------- UC-7 Planlæg tur med ladestop (FR-13, FR-14)
def corridor_position(path, lat, lng):
    """Projicerer et punkt på ruten: (km langs ruten, afstand fra ruten i km). Flad jord-tilnærmelse pr. strækning."""
    best, along = None, 0.0
    for (lat1, lng1), (lat2, lng2) in zip(path, path[1:]):
        kx = 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
        ax, ay, bx, by, px, py = lng1 * kx, lat1 * 110.57, lng2 * kx, lat2 * 110.57, lng * kx, lat * 110.57
        seg = math.hypot(bx - ax, by - ay)
        u = max(0, min(1, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / (seg * seg))) if seg else 0
        off = math.hypot(ax + u * (bx - ax) - px, ay + u * (by - ay) - py)
        if best is None or off < best[1]:
            best = ((along + u * seg) * ROAD_FACTOR, off)
        along += seg
    return best[0], best[1], along * ROAD_FACTOR


@app.get("/api/route")
def route():
    """Rute med ladestop fra Sjælland til en by i DK, SE, NO eller DE (roaming). Ruten følger vejforløbet.
    Hvert stop er den lynlader længst fremme på ruten, der kan nås med mindst 15 % batteri. Der lades til 80 %."""
    user = current_user()
    origin, destination = request.args.get("from", "Greve"), request.args.get("to")
    if origin not in ORIGINS or destination not in CORRIDORS:
        raise ApiError("Vælg start (" + ", ".join(ORIGINS) + ") og mål (" + ", ".join(CORRIDORS) + ")")
    car = query_one("SELECT * FROM car WHERE user_id = ?", (user["id"],))
    start_pct = request.args.get("battery", default=80, type=int)
    rng = car["range_km"]
    names = [origin] + [n for n in CORRIDORS[destination] if n != origin]
    path = [PLACES[n] for n in names]

    chargers = []
    for loc in query_all("SELECT l.*, o.name AS operator, o.is_clever FROM location l JOIN operator o ON o.id = l.operator_id"):
        summary = location_summary(loc)
        along, off, total = corridor_position(path, loc["lat"], loc["lng"])
        # Udtag med bilens stik og mindst 50 kW – eller det, bilen kan tage imod (fx 22 kW AC)
        power = max((c["max_power_kw"] for c in summary["connectors"] if c["plug_type"] == car["plug_type"]
                     and c["max_power_kw"] >= min(50, car["max_power_kw"])), default=0)
        if power and off <= 15:
            chargers.append({**loc, "summary": summary, "along": along, "power": min(power, car["max_power_kw"])})

    position, battery_km, stops = 0.0, rng * start_pct / 100, []
    while position + battery_km - total < rng * 0.1 and len(stops) < 6:
        reachable = [c for c in chargers if position < c["along"] <= position + battery_km - rng * 0.15]
        if not reachable:
            break
        best = max(reachable, key=lambda c: c["along"])
        arrive_pct = round(100 * (battery_km - (best["along"] - position)) / rng)
        power = best["power"]
        stops.append({"location_id": best["id"], "name": best["name"], "city": best["city"], "country": best["country"],
                      "operator": best["operator"], "roaming": not best["is_clever"], "km_from_start": round(best["along"]),
                      "arrive_battery_pct": arrive_pct, "charge_to_pct": 80, "free": best["summary"]["free"],
                      "total": best["summary"]["total"], "max_power_kw": power,
                      "price_per_kwh": best["summary"]["min_price"],
                      "charge_minutes": max(0, round(car["battery_kwh"] * (80 - arrive_pct) / 100 / power * 60))})
        position, battery_km = best["along"], rng * 0.8
    arrive = round(100 * (position + battery_km - total) / rng)
    return jsonify(origin=origin, destination=destination, via=names[1:-1], distance_km=round(total), car=car["model"],
                   start_battery_pct=start_pct, arrive_battery_pct=arrive, reachable=arrive >= 10, stops=stops,
                   origins=ORIGINS, destinations=list(CORRIDORS))


@app.post("/api/route/send-to-car")
def send_to_car():
    """FR-14 (could): send ruten til bilens skærm (CarPlay / Android Auto) – simuleret."""
    current_user()
    data = json_body()
    return jsonify(sent=True, message=f"Ruten med {len(data.get('stops', []))} ladestop er sendt til bilens skærm (simuleret).")


# ---------------------------------------------------------------- UC-8 Forbrugsoverblik (FR-15)
@app.get("/api/my/overview")
def overview():
    """Forbrug, pris og CO₂ pr. måned de seneste 12 måneder og abonnement sammenlignet med forbrug."""
    user = current_user()
    months = query_all("""SELECT substr(started_at, 1, 7) AS month, COUNT(*) AS sessions, ROUND(SUM(kwh), 1) AS kwh,
                                 ROUND(SUM(price_total), 2) AS price,
                                 ROUND(SUM(kwh * COALESCE(gco2_per_kwh, 0)) / 1000, 1) AS co2_kg,
                                 ROUND(AVG(renewable_pct)) AS renewable_pct
                          FROM session WHERE user_id = ? AND status = 'AFSLUTTET'
                            AND started_at >= date('now', 'localtime', '-12 months')
                          GROUP BY month ORDER BY month DESC""", (user["id"],))
    subscription = query_one("SELECT * FROM subscription WHERE user_id = ?", (user["id"],))
    avg_month_price = round(sum(m["price"] for m in months) / len(months), 2) if months else 0
    advice = None
    if subscription and subscription["type"] != "INGEN" and months:
        advice = ("Dit abonnement kan betale sig." if subscription["monthly_price"] <= avg_month_price
                  else f"Du bruger i gennemsnit for {avg_month_price:.0f} kr. om måneden på udeopladning – mindre end "
                       f"abonnementet på {subscription['monthly_price']:.0f} kr. Tjek, om hjemmeopladningen gør det rentabelt.")
    return jsonify(months=months, subscription=subscription, avg_month_price=avg_month_price, advice=advice,
                   your_average_price=user_average_price(user["id"]))


if __name__ == "__main__":
    init_db()
    run(app, PORT)
