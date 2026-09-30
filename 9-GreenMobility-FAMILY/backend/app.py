"""GreenMobility FAMILY – familieabonnement, booking, datadrevet flådestyring og partnerfordele. Flask API (logiklag).

Kravgrundlag: ../Kravspecifikation.md (Business Use Case 1 og 2 og User Journey Map)
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5209
"""
import os
import secrets
from datetime import datetime, timedelta

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5209))
app = create_app(__name__, "GreenMobility FAMILY")

HISTORY_WEEKS = 8           # forecast bygger på de seneste 8 ugers ture
BLOCKS = [(6, 10, "Morgen 6–10"), (10, 14, "Formiddag 10–14"), (14, 18, "Eftermiddag 14–18"), (18, 23, "Aften 18–23")]
WEEKDAYS = ["søndag", "mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag"]     # som SQLite strftime('%w')
CREDIT_VALUE_KR = 1         # 1 GreenCredit = 1 kr. på næste tur (antagelse)
MAX_HOURS = 12


def parse_time(value, field):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ApiError(f"{field} skal være et tidspunkt som 2026-10-01T10:00")


def iso(dt):
    return dt.isoformat(sep=" ", timespec="seconds")


def luhn_ok(number):
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 12:
        return False
    total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(reversed(digits)))
    return total % 10 == 0


def credits_balance(family_id):
    return query_one("SELECT COALESCE(SUM(amount), 0) AS n FROM credit_transaction WHERE family_id = ?", (family_id,))["n"]


def minutes_used_this_month(family_id):
    return query_one("""SELECT COALESCE(SUM(included_min), 0) AS n FROM trip
                        WHERE family_id = ? AND started_at >= date('now', 'localtime', 'start of month')""", (family_id,))["n"]


def block_of(hour):
    return next((b for b in BLOCKS if b[0] <= hour < b[1]), BLOCKS[-1])


# ---------------------------------------------------------------- CRUD
register_crud(app, "plans", "plan", fields=["name", "monthly_price", "included_hours", "discount_pct", "max_members", "description"],
              required=["name", "monthly_price", "included_hours", "description"], order_by="monthly_price")
register_crud(app, "zones", "zone", fields=["name"], required=["name"], order_by="name")
register_crud(app, "car-types", "car_type", fields=["name", "seats", "child_seat", "price_per_min"],
              required=["name", "seats", "price_per_min"])
register_crud(app, "cars", "car", fields=["plate", "car_type_id", "zone_id", "battery_pct", "status"],
              required=["plate", "car_type_id", "zone_id"], order_by="plate")
register_crud(app, "partners", "partner", fields=["name", "category", "benefit", "credits_per_activity"],
              required=["name", "category", "benefit", "credits_per_activity"])
register_crud(app, "families", "family", fields=["name", "plan_id", "status", "home_zone_id"], read_only=True)


# ---------------------------------------------------------------- Opdager og tilmeld (BUC 1)
@app.get("/api/offer")
def offer():
    """Opdager-fasen: abonnementer med pris og fordele samt partnerfordele."""
    return jsonify(plans=query_all("SELECT * FROM plan ORDER BY monthly_price"),
                   partners=query_all("SELECT * FROM partner ORDER BY name"),
                   car_types=query_all("SELECT * FROM car_type ORDER BY price_per_min"))


@app.post("/api/families")
def sign_up():
    """Tilmeld: opret profil, vælg plan og valider betaling. Medlemskabet er aktivt, når betalingen er godkendt."""
    data = json_body()
    require(data, "name", "plan_id", "members", "card_number", "card_expiry")
    plan = get_or_404("plan", data["plan_id"], "Abonnement")
    members = [m for m in data["members"] if (m.get("name") or "").strip()]
    if not members:
        raise ApiError("Tilføj mindst ét familiemedlem")
    if len(members) > plan["max_members"]:
        raise ApiError(f"{plan['name']} giver plads til højst {plan['max_members']} medlemmer")
    if not any(m.get("is_driver") for m in members):
        raise ApiError("Mindst ét medlem skal være voksen med kørekort")
    # Betalingsservicen validerer kortet (simuleret: Luhn-kontrol og udløbsdato)
    if not luhn_ok(data["card_number"]):
        raise ApiError("Kortnummeret er ugyldigt", 402)
    try:
        month, year = (int(x) for x in data["card_expiry"].split("/"))
        if (2000 + year, month) < (datetime.now().year, datetime.now().month):
            raise ApiError("Kortet er udløbet", 402)
    except ValueError:
        raise ApiError("Udløbsdato skal skrives som MM/ÅÅ")
    digits = "".join(d for d in data["card_number"] if d.isdigit())
    with transaction() as db:
        family_id = db.execute("""INSERT INTO family (name, plan_id, status, card_last4, payment_ref, home_zone_id, created_at)
                                  VALUES (?, ?, 'AKTIV', ?, ?, ?, ?)""",
                               (data["name"], plan["id"], digits[-4:], f"PAY-FAM-{secrets.token_hex(3).upper()}",
                                data.get("home_zone_id"), now())).lastrowid
        for m in members:
            db.execute("INSERT INTO member (family_id, name, email, is_driver) VALUES (?, ?, ?, ?)",
                       (family_id, m["name"].strip(), m.get("email"), 1 if m.get("is_driver") else 0))
    return jsonify(dashboard_data(family_id)), 201


# ---------------------------------------------------------------- Familiens overblik og "Book igen" (personlige forslag)
def dashboard_data(family_id):
    family = query_one("""SELECT f.*, p.name AS plan_name, p.monthly_price, p.included_hours, p.discount_pct
                          FROM family f JOIN plan p ON p.id = f.plan_id WHERE f.id = ?""", (family_id,))
    if family is None:
        raise ApiError(f"Familie med id {family_id} findes ikke", 404)
    used = minutes_used_this_month(family_id)
    trips = query_all("""SELECT t.*, ct.name AS car_type, z.name AS zone, ez.name AS end_zone FROM trip t
                         JOIN car_type ct ON ct.id = t.car_type_id JOIN zone z ON z.id = t.zone_id JOIN zone ez ON ez.id = t.end_zone_id
                         WHERE t.family_id = ? ORDER BY t.started_at DESC LIMIT 10""", (family_id,))
    reservations = query_all("""SELECT r.*, c.plate, ct.name AS car_type, z.name AS zone, m.name AS member FROM reservation r
                                JOIN car c ON c.id = r.car_id JOIN car_type ct ON ct.id = c.car_type_id
                                JOIN zone z ON z.id = c.zone_id JOIN member m ON m.id = r.member_id
                                WHERE r.family_id = ? AND r.status = 'BEKRÆFTET' ORDER BY r.start_at""", (family_id,))
    # Book igen: familiens mest brugte kombination af zone, biltype, ugedag og tidsrum
    favourite = query_one("""SELECT t.zone_id, z.name AS zone, t.car_type_id, ct.name AS car_type,
                                    strftime('%w', t.started_at) AS weekday,
                                    CAST(strftime('%H', t.started_at) AS INTEGER) AS hour, COUNT(*) AS n
                             FROM trip t JOIN zone z ON z.id = t.zone_id JOIN car_type ct ON ct.id = t.car_type_id
                             WHERE t.family_id = ? GROUP BY t.zone_id, t.car_type_id, weekday
                             ORDER BY n DESC LIMIT 1""", (family_id,))
    suggestion = None
    if favourite:
        target = datetime.now().replace(minute=0, second=0, microsecond=0)
        while target.strftime("%w") != favourite["weekday"] or target <= datetime.now():
            target += timedelta(days=1)
        target = target.replace(hour=favourite["hour"])
        suggestion = {"zone_id": favourite["zone_id"], "zone": favourite["zone"], "car_type_id": favourite["car_type_id"],
                      "car_type": favourite["car_type"], "start_at": target.isoformat(timespec="minutes"),
                      "text": f"I kører tit med {favourite['car_type'].lower()} fra {favourite['zone']} om {WEEKDAYS[int(favourite['weekday'])]}en. "
                              f"Skal vi finde en bil {WEEKDAYS[int(favourite['weekday'])]} kl. {favourite['hour']:02d}?"}
    return {**family, "members": query_all("SELECT * FROM member WHERE family_id = ?", (family_id,)),
            "included_minutes": family["included_hours"] * 60, "used_minutes": used,
            "remaining_minutes": max(0, family["included_hours"] * 60 - used),
            "credits": credits_balance(family_id), "reservations": reservations, "trips": trips,
            "credit_history": query_all("""SELECT c.*, p.name AS partner FROM credit_transaction c
                                           LEFT JOIN partner p ON p.id = c.partner_id WHERE c.family_id = ?
                                           ORDER BY c.id DESC LIMIT 10""", (family_id,)),
            "suggestion": suggestion}


@app.get("/api/families/<int:family_id>/dashboard")
def dashboard(family_id):
    """Familiens overblik: abonnement, forbrug af inkluderede timer, GreenCredits, reservationer, ture og forslag."""
    return jsonify(dashboard_data(family_id))


# ---------------------------------------------------------------- Planlæg og reserver (datadrevet availability)
def overlapping(car_id, start, end, exclude=None):
    return query_one("""SELECT id FROM reservation WHERE car_id = ? AND status = 'BEKRÆFTET' AND id != ?
                        AND start_at < ? AND end_at > ?""", (car_id, exclude or 0, iso(end), iso(start)))


def expected_demand(zone_id, car_type_id, when):
    """Forventet antal ture i zonen for biltypen på samme ugedag og tidsrum (gennemsnit over historikken)."""
    lo, hi, _ = block_of(when.hour)
    row = query_one("""SELECT COUNT(*) AS n FROM trip WHERE zone_id = ? AND car_type_id = ?
                       AND strftime('%w', started_at) = ? AND CAST(strftime('%H', started_at) AS INTEGER) BETWEEN ? AND ?
                       AND started_at >= date('now', 'localtime', ?)""",
                    (zone_id, car_type_id, when.strftime("%w"), lo, hi - 1, f"-{HISTORY_WEEKS * 7} days"))
    return round(row["n"] / HISTORY_WEEKS, 1)


@app.get("/api/availability")
def availability():
    """Tilgængelige biler i zonen for biltype og tidsrum, alternativer i andre zoner og forventet efterspørgsel."""
    zone = get_or_404("zone", request.args.get("zone_id", type=int) or 0, "Zone")
    car_type = get_or_404("car_type", request.args.get("car_type_id", type=int) or 0, "Biltype")
    start = parse_time(request.args.get("start"), "Start")
    end = parse_time(request.args.get("end"), "Slut")
    if end <= start:
        raise ApiError("Sluttidspunktet skal ligge efter starttidspunktet")
    cars = query_all("""SELECT c.*, z.name AS zone FROM car c JOIN zone z ON z.id = c.zone_id
                        WHERE c.car_type_id = ? AND c.status = 'KLAR' ORDER BY c.zone_id = ? DESC, c.battery_pct DESC""",
                     (car_type["id"], zone["id"]))
    free = [c for c in cars if not overlapping(c["id"], start, end)]
    here = [c for c in free if c["zone_id"] == zone["id"]]
    elsewhere = [c for c in free if c["zone_id"] != zone["id"]]
    demand = expected_demand(zone["id"], car_type["id"], start)
    capacity = "HØJ" if len(here) >= 2 and demand < len(here) else "LAV" if not here else "BEGRÆNSET" if demand >= len(here) else "OK"
    return jsonify(zone=zone, car_type=car_type, start=iso(start), end=iso(end), cars=here, alternatives=elsewhere,
                   expected_demand=demand, capacity=capacity,
                   message=("Der er god tilgængelighed." if capacity in ("HØJ", "OK") else
                            "Mange familier plejer at booke på dette tidspunkt – book i god tid." if capacity == "BEGRÆNSET" else
                            "Ingen ledige biler af typen i zonen – se alternativerne i nærheden."))


@app.post("/api/reservations")
def reserve():
    """Reserver en bil. Kræver aktivt medlemskab, en fører med kørekort og at bilen er ledig i tidsrummet."""
    data = json_body()
    require(data, "family_id", "member_id", "car_id", "start_at", "end_at")
    family = get_or_404("family", data["family_id"], "Familie")
    if family["status"] != "AKTIV":
        raise ApiError("Medlemskabet er ikke aktivt", 403)
    member = get_or_404("member", data["member_id"], "Medlem")
    if member["family_id"] != family["id"] or not member["is_driver"]:
        raise ApiError("Føreren skal være et voksent familiemedlem med kørekort")
    car = get_or_404("car", data["car_id"], "Bil")
    if car["status"] != "KLAR":
        raise ApiError("Bilen er til service", 409)
    start, end = parse_time(data["start_at"], "Start"), parse_time(data["end_at"], "Slut")
    if end <= start or (end - start) > timedelta(hours=MAX_HOURS):
        raise ApiError(f"En reservation skal vare mellem 1 minut og {MAX_HOURS} timer")
    if start < datetime.now() - timedelta(minutes=15):
        raise ApiError("Starttidspunktet er passeret")
    if overlapping(car["id"], start, end):
        raise ApiError("Bilen er allerede reserveret i tidsrummet – vælg en anden bil", 409)
    with transaction() as db:
        reservation_id = db.execute("""INSERT INTO reservation (family_id, member_id, car_id, start_at, end_at, created_at)
                                       VALUES (?, ?, ?, ?, ?, ?)""",
                                    (family["id"], member["id"], car["id"], iso(start), iso(end), now())).lastrowid
    return jsonify(reservation=get_or_404("reservation", reservation_id), car=car,
                   message=f"Reservation bekræftet: {car['plate']} {start:%d.%m kl. %H:%M}–{end:%H:%M}"), 201


@app.post("/api/reservations/<int:reservation_id>/cancel")
def cancel(reservation_id):
    """Annullér en reservation, så bilen bliver ledig igen."""
    reservation = get_or_404("reservation", reservation_id, "Reservation")
    if reservation["status"] != "BEKRÆFTET":
        raise ApiError("Reservationen er ikke aktiv", 409)
    with transaction() as db:
        db.execute("UPDATE reservation SET status = 'ANNULLERET' WHERE id = ?", (reservation_id,))
    return jsonify(get_or_404("reservation", reservation_id))


@app.post("/api/reservations/<int:reservation_id>/complete")
def complete(reservation_id):
    """Kør: efter kørslen logges turdata. Inkluderede minutter bruges først, derefter rabatpris. GreenCredits kan bruges."""
    reservation = get_or_404("reservation", reservation_id, "Reservation")
    if reservation["status"] != "BEKRÆFTET":
        raise ApiError("Reservationen er ikke aktiv", 409)
    data = json_body()
    require(data, "km", "end_zone_id")
    get_or_404("zone", data["end_zone_id"], "Zone")
    car = get_or_404("car", reservation["car_id"])
    car_type = get_or_404("car_type", car["car_type_id"])
    family = dashboard_data(reservation["family_id"])
    start, end = datetime.fromisoformat(reservation["start_at"]), datetime.fromisoformat(reservation["end_at"])
    minutes = int(data.get("minutes") or (end - start).total_seconds() // 60)
    included = min(minutes, family["remaining_minutes"])
    extra_price = round((minutes - included) * car_type["price_per_min"] * (100 - family["discount_pct"]) / 100, 2)
    credits = min(family["credits"], int(extra_price / CREDIT_VALUE_KR)) if data.get("use_credits") else 0
    price = round(extra_price - credits * CREDIT_VALUE_KR, 2)
    with transaction() as db:
        trip_id = db.execute("""INSERT INTO trip (reservation_id, family_id, car_type_id, zone_id, end_zone_id, started_at,
                                                  minutes, km, included_min, price, credits_used)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (reservation_id, reservation["family_id"], car_type["id"], car["zone_id"], data["end_zone_id"],
                              reservation["start_at"], minutes, float(data["km"]), included, price, credits)).lastrowid
        db.execute("UPDATE reservation SET status = 'AFSLUTTET' WHERE id = ?", (reservation_id,))
        db.execute("UPDATE car SET zone_id = ?, battery_pct = MAX(10, battery_pct - ?) WHERE id = ?",
                   (data["end_zone_id"], int(float(data["km"]) / 3), car["id"]))
        if credits:
            db.execute("""INSERT INTO credit_transaction (family_id, trip_id, amount, description, created_at)
                          VALUES (?, ?, ?, 'Brugt på tur', ?)""", (reservation["family_id"], trip_id, -credits, now()))
    return jsonify(trip=get_or_404("trip", trip_id),
                   summary=f"{minutes} min, heraf {included} inkluderet. Pris {price:.2f} kr."
                           + (f" ({credits} GreenCredits brugt)" if credits else "")), 201


# ---------------------------------------------------------------- Belønnes: partneraktivitet → GreenCredits (BUC 2)
@app.post("/api/partner-activities")
def partner_activity():
    """Partneren registrerer en aktivitet, som udløser GreenCredits til familien."""
    data = json_body()
    require(data, "family_id", "partner_id")
    family = get_or_404("family", data["family_id"], "Familie")
    if family["status"] != "AKTIV":
        raise ApiError("Kun aktive Family-medlemmer optjener GreenCredits", 403)
    partner = get_or_404("partner", data["partner_id"], "Partner")
    with transaction() as db:
        db.execute("""INSERT INTO credit_transaction (family_id, partner_id, amount, description, created_at)
                      VALUES (?, ?, ?, ?, ?)""",
                   (family["id"], partner["id"], partner["credits_per_activity"],
                    data.get("description") or f"Aktivitet hos {partner['name']}", now()))
    return jsonify(credits_added=partner["credits_per_activity"], balance=credits_balance(family["id"]),
                   message=f"{family['name']} har fået {partner['credits_per_activity']} GreenCredits fra {partner['name']}"), 201


# ---------------------------------------------------------------- Datadrevet flådestyring (BUC 2)
@app.get("/api/forecast")
def forecast():
    """Forecast pr. zone og biltype for en ugedag og et tidsrum ud fra historiske ture, sammenholdt med biler i zonen."""
    weekday = request.args.get("weekday", default=int(datetime.now().strftime("%w")), type=int)
    block_index = request.args.get("block", default=BLOCKS.index(block_of(datetime.now().hour)), type=int)
    if not 0 <= weekday <= 6 or not 0 <= block_index < len(BLOCKS):
        raise ApiError("Ugyldig ugedag eller tidsrum")
    lo, hi, label = BLOCKS[block_index]
    demand = {(r["zone_id"], r["car_type_id"]): r["n"] / HISTORY_WEEKS for r in query_all(
        """SELECT zone_id, car_type_id, COUNT(*) AS n FROM trip
           WHERE strftime('%w', started_at) = ? AND CAST(strftime('%H', started_at) AS INTEGER) BETWEEN ? AND ?
             AND started_at >= date('now', 'localtime', ?)
           GROUP BY zone_id, car_type_id""", (str(weekday), lo, hi - 1, f"-{HISTORY_WEEKS * 7} days"))}
    supply = {(r["zone_id"], r["car_type_id"]): r["n"] for r in query_all(
        "SELECT zone_id, car_type_id, COUNT(*) AS n FROM car WHERE status = 'KLAR' GROUP BY zone_id, car_type_id")}
    rows = []
    for zone in query_all("SELECT * FROM zone ORDER BY name"):
        for car_type in query_all("SELECT * FROM car_type ORDER BY id"):
            expected = round(demand.get((zone["id"], car_type["id"]), 0), 1)
            available = supply.get((zone["id"], car_type["id"]), 0)
            rows.append({"zone_id": zone["id"], "zone": zone["name"], "car_type_id": car_type["id"], "car_type": car_type["name"],
                         "expected_trips": expected, "available_cars": available, "gap": round(expected - available, 1)})
    # Anbefal flytninger: fra zoner med overskud til zoner med størst mangel af samme biltype
    moves = []
    for need in sorted((r for r in rows if r["gap"] >= 0.5), key=lambda r: -r["gap"]):
        donor = max((r for r in rows if r["car_type_id"] == need["car_type_id"] and r["gap"] <= -1),
                    key=lambda r: -r["gap"], default=None)
        if donor:
            car = query_one("""SELECT * FROM car WHERE zone_id = ? AND car_type_id = ? AND status = 'KLAR'
                               ORDER BY battery_pct DESC LIMIT 1""", (donor["zone_id"], donor["car_type_id"]))
            if car and all(m["car_id"] != car["id"] for m in moves):
                moves.append({"car_id": car["id"], "plate": car["plate"], "car_type": need["car_type"],
                              "from_zone_id": donor["zone_id"], "from_zone": donor["zone"],
                              "to_zone_id": need["zone_id"], "to_zone": need["zone"],
                              "reason": f"Forventet {need['expected_trips']} ture mod {need['available_cars']} biler"})
                donor["gap"] += 1
                need["gap"] -= 1
    return jsonify(weekday=WEEKDAYS[weekday], block=label, history_weeks=HISTORY_WEEKS, rows=rows, recommended_moves=moves,
                   blocks=[b[2] for b in BLOCKS], weekdays=WEEKDAYS)


@app.post("/api/relocations")
def relocate():
    """Operations flytter en bil til en anden zone efter forecastet."""
    data = json_body()
    require(data, "car_id", "to_zone_id")
    car = get_or_404("car", data["car_id"], "Bil")
    get_or_404("zone", data["to_zone_id"], "Zone")
    if car["zone_id"] == data["to_zone_id"]:
        raise ApiError("Bilen står allerede i zonen")
    with transaction() as db:
        db.execute("INSERT INTO relocation (car_id, from_zone_id, to_zone_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
                   (car["id"], car["zone_id"], data["to_zone_id"], data.get("reason"), now()))
        db.execute("UPDATE car SET zone_id = ? WHERE id = ?", (data["to_zone_id"], car["id"]))
    return jsonify(get_or_404("car", car["id"])), 201


@app.get("/api/relocations")
def relocations():
    """Log over flytninger."""
    return jsonify(query_all("""SELECT r.*, c.plate, f.name AS from_zone, t.name AS to_zone FROM relocation r
                                JOIN car c ON c.id = r.car_id JOIN zone f ON f.id = r.from_zone_id JOIN zone t ON t.id = r.to_zone_id
                                ORDER BY r.id DESC LIMIT 20"""))


@app.get("/api/stats")
def stats():
    """Nøgletal: familier, ture, kørte km, GreenCredits og biltyper."""
    return jsonify(
        families=query_one("SELECT COUNT(*) AS n FROM family WHERE status = 'AKTIV'")["n"],
        members=query_one("SELECT COUNT(*) AS n FROM member")["n"],
        monthly_revenue=query_one("SELECT COALESCE(SUM(p.monthly_price), 0) AS n FROM family f JOIN plan p ON p.id = f.plan_id WHERE f.status = 'AKTIV'")["n"],
        trips_30d=query_one("SELECT COUNT(*) AS n FROM trip WHERE started_at >= date('now', 'localtime', '-30 days')")["n"],
        km_30d=query_one("SELECT ROUND(COALESCE(SUM(km), 0)) AS n FROM trip WHERE started_at >= date('now', 'localtime', '-30 days')")["n"],
        credits_issued=query_one("SELECT COALESCE(SUM(amount), 0) AS n FROM credit_transaction WHERE amount > 0")["n"],
        per_car_type=query_all("""SELECT ct.name, COUNT(t.id) AS trips, ROUND(AVG(t.minutes)) AS avg_minutes
                                  FROM car_type ct LEFT JOIN trip t ON t.car_type_id = ct.id GROUP BY ct.id"""),
    )


if __name__ == "__main__":
    init_db()
    run(app, PORT)
