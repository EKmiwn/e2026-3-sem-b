"""&LIVING Buyer Matchmaking – købere slår købekraften sammen. Flask API (logiklag).

Kravgrundlag: ../Requirement_Specifications.md
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5205

Den indloggede køber vælges i frontenden og sendes i headeren X-User-Id (simuleret login).
Brugerfladen og fejlbeskederne er på engelsk som kravspecifikationen.
"""
import os

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5205))
app = create_app(__name__, "&LIVING Buyer Matchmaking")

PUBLIC_FIELDS = ["id", "name", "age", "preferred_location", "property_type", "min_area", "max_transport_min",
                 "pets", "smoker", "has_children", "social_level"]


def setting(key):
    row = query_one("SELECT value FROM setting WHERE key = ?", (key,))
    if row is None:
        raise ApiError(f"Setting {key} is missing", 500)
    return row["value"]


def current_buyer():
    user_id = request.headers.get("X-User-Id")
    buyer = query_one("SELECT * FROM buyer WHERE id = ?", (user_id,)) if user_id and user_id.isdigit() else None
    if buyer is None:
        raise ApiError("Choose a buyer (header X-User-Id is missing or invalid)", 401)
    return buyer


def public_profile(buyer, show_contact=False):
    """Det, andre købere må se: ingen e-mail eller telefon, medmindre køberen selv har valgt at dele dem (sikkerhed)."""
    profile = {k: buyer[k] for k in PUBLIC_FIELDS}
    profile["budget_band"] = f"{buyer['budget'] // 250000 * 0.25:.2f}–{(buyer['budget'] // 250000 + 1) * 0.25:.2f} m DKK"
    if show_contact and buyer["share_contact"]:
        profile["email"], profile["phone"] = buyer["email"], buyer["phone"]
    return profile


# ---------------------------------------------------------------- Købermatch: økonomisk kompatibilitet + livsstil
def match_score(a, b):
    """Score 0–100 med begrundelser. Vægten mellem økonomi og livsstil er en indstilling."""
    budget_sim = min(a["budget"], b["budget"]) / max(a["budget"], b["budget"])
    ratio_a, ratio_b = a["down_payment"] / a["budget"], b["down_payment"] / b["budget"]
    down_sim = 1 - min(1, abs(ratio_a - ratio_b) / 0.2)
    financial = round(100 * (0.6 * budget_sim + 0.4 * down_sim))
    if not (a["preapproved_loan"] and b["preapproved_loan"]):
        financial = round(financial * 0.7)

    points, reasons = 0, []

    def add(condition, value, reason, partial=0):
        nonlocal points
        points += value if condition else partial
        if condition:
            reasons.append(reason)

    add(a["preferred_location"] == b["preferred_location"], 25, f"Both want to live in {a['preferred_location']}")
    add(a["property_type"] == b["property_type"], 20, f"Both look for a {a['property_type'].lower()}")
    add(abs(a["max_transport_min"] - b["max_transport_min"]) <= 10, 10, "Similar commute tolerance", 5)
    add(a["smoker"] == b["smoker"], 15, "Same smoking habits")
    add(a["pets"] == b["pets"], 10, "Agree on pets", 5)
    add(a["has_children"] == b["has_children"], 10, "Same family situation")
    social = max(0, 10 - 2.5 * abs(a["social_level"] - b["social_level"]))
    points += social
    if social >= 7.5:
        reasons.append("Similar social rhythm")
    lifestyle = round(points)

    weight = setting("financial_weight")
    total = round(weight * financial + (1 - weight) * lifestyle)
    if budget_sim >= 0.85:
        reasons.insert(0, "Similar budgets")
    return {"score": total, "financial": financial, "lifestyle": lifestyle, "reasons": reasons}


def active_group_id(buyer_id):
    row = query_one("SELECT group_id FROM group_member WHERE buyer_id = ? AND left_at IS NULL", (buyer_id,))
    return row["group_id"] if row else None


def members(group_id):
    return query_all("""SELECT b.*, m.joined_at FROM group_member m JOIN buyer b ON b.id = m.buyer_id
                        WHERE m.group_id = ? AND m.left_at IS NULL ORDER BY m.joined_at""", (group_id,))


def require_member(buyer, group_id):
    get_or_404("buyer_group", group_id, "Group")
    if active_group_id(buyer["id"]) != group_id:
        raise ApiError("Only members of the group can do this", 403)


def group_power(group_members):
    """Samlet købekraft og pladsbehov for en dannet gruppe."""
    power = sum(m["preapproved_loan"] + m["down_payment"] for m in group_members)
    required_area = (max((m["min_area"] for m in group_members), default=0)
                     + setting("extra_area_per_member") * max(0, len(group_members) - 1))
    max_transport = min((m["max_transport_min"] for m in group_members), default=0)
    return {"purchasing_power": power, "combined_budget": sum(m["budget"] for m in group_members),
            "down_payment": sum(m["down_payment"] for m in group_members),
            "required_area": int(required_area), "max_transport_min": max_transport,
            "locations": sorted({m["preferred_location"] for m in group_members}),
            "property_types": sorted({m["property_type"] for m in group_members})}


# ---------------------------------------------------------------- CRUD
register_crud(app, "settings", "setting", fields=["key", "value", "description"], required=["key", "value"],
              update_fields=["value", "description"])
register_crud(app, "agents", "agent", fields=["name", "office"], required=["name", "office"])
register_crud(app, "properties", "property",
              fields=["address", "location", "property_type", "price", "area", "rooms", "transport_min", "monthly_cost",
                      "off_market", "agent_id"],
              required=["address", "location", "property_type", "price", "area", "rooms", "transport_min"],
              order_by="price")
BUYER_FIELDS = ["name", "email", "phone", "age", "budget", "preapproved_loan", "down_payment", "preferred_location",
                "property_type", "min_area", "max_transport_min", "pets", "smoker", "has_children", "social_level",
                "share_contact"]
register_crud(app, "buyers", "buyer", fields=BUYER_FIELDS,
              required=["name", "email", "age", "budget", "preferred_location", "property_type", "min_area",
                        "max_transport_min"])


@app.post("/api/buyers/<int:buyer_id>/consent")
def consent(buyer_id):
    """Udtrykkeligt samtykke til at bruge økonomi- og livsstilsdata til match. Trækkes det tilbage, matches køberen ikke længere."""
    get_or_404("buyer", buyer_id, "Buyer")
    given = bool(json_body().get("consent"))
    with transaction() as db:
        db.execute("UPDATE buyer SET consent_at = ? WHERE id = ?", (now() if given else None, buyer_id))
    return jsonify(get_or_404("buyer", buyer_id))


# ---------------------------------------------------------------- Match
@app.get("/api/matches")
def matches():
    """Kompatible købere for den indloggede køber, bedste først, med delscorer og begrundelser."""
    me = current_buyer()
    if not me["consent_at"]:
        raise ApiError("Give consent to matching in your profile first", 403)
    my_group = active_group_id(me["id"])
    limit = setting("min_match_score")
    result = []
    for other in query_all("SELECT * FROM buyer WHERE id != ? AND consent_at IS NOT NULL", (me["id"],)):
        other_group = active_group_id(other["id"])
        if my_group and other_group == my_group:
            continue
        score = match_score(me, other)
        if score["score"] >= limit:
            result.append({"buyer": public_profile(other), **score,
                           "in_group": other_group is not None,
                           "combined_power": me["preapproved_loan"] + me["down_payment"]
                                             + other["preapproved_loan"] + other["down_payment"]})
    result.sort(key=lambda r: -r["score"])
    return jsonify(min_score=limit, matches=result)


# ---------------------------------------------------------------- Grupper: dannes, udvides og forlades
@app.get("/api/my-group")
def my_group():
    """Den indloggede købers nuværende gruppe – eller null."""
    me = current_buyer()
    group_id = active_group_id(me["id"])
    return jsonify(group_view(group_id, me) if group_id else None)


def group_view(group_id, me):
    group = get_or_404("buyer_group", group_id, "Group")
    group_members = members(group_id)
    items = query_all("""SELECT s.*, p.address, p.location, p.price, p.area, p.rooms, p.off_market, b.name AS added_by_name,
                                COALESCE((SELECT SUM(value) FROM vote v WHERE v.shortlist_item_id = s.id), 0) AS score
                         FROM shortlist_item s JOIN property p ON p.id = s.property_id JOIN buyer b ON b.id = s.added_by
                         WHERE s.group_id = ? ORDER BY score DESC, s.id""", (group_id,))
    for item in items:
        item["votes"] = query_all("""SELECT v.value, v.comment, v.buyer_id, b.name FROM vote v
                                     JOIN buyer b ON b.id = v.buyer_id WHERE v.shortlist_item_id = ?""", (item["id"],))
    return {
        **group, **group_power(group_members),
        "members": [public_profile(m, show_contact=True) for m in group_members],
        "max_group_size": int(setting("max_group_size")),
        "messages": query_all("""SELECT m.*, b.name AS sender FROM message m JOIN buyer b ON b.id = m.sender_id
                                 WHERE m.group_id = ? ORDER BY m.id""", (group_id,)),
        "shortlist": items,
        "viewings": query_all("""SELECT v.*, p.address, b.name AS requested_by_name FROM viewing_request v
                                 JOIN property p ON p.id = v.property_id JOIN buyer b ON b.id = v.requested_by
                                 WHERE v.group_id = ? ORDER BY v.id DESC""", (group_id,)),
        "me": me["id"],
    }


@app.post("/api/groups")
def connect():
    """Forbind med et match: opretter en gruppe eller tilføjer køberen til den indloggede købers gruppe."""
    me = current_buyer()
    data = json_body()
    require(data, "buyer_id")
    other = get_or_404("buyer", data["buyer_id"], "Buyer")
    if not (me["consent_at"] and other["consent_at"]):
        raise ApiError("Both buyers must have given consent to matching", 403)
    if active_group_id(other["id"]):
        raise ApiError(f"{other['name']} is already in a buyer group", 409)
    group_id = active_group_id(me["id"])
    with transaction() as db:
        if group_id is None:
            group_id = db.execute("INSERT INTO buyer_group (name, agent_id, created_at) VALUES (?, 1, ?)",
                                  (f"{me['name']} & {other['name']}", now())).lastrowid
            db.execute("INSERT INTO group_member (group_id, buyer_id, joined_at) VALUES (?, ?, ?)",
                       (group_id, me["id"], now()))
        elif len(members(group_id)) >= setting("max_group_size"):
            raise ApiError(f"A group can have at most {int(setting('max_group_size'))} buyers")
        db.execute("INSERT INTO group_member (group_id, buyer_id, joined_at) VALUES (?, ?, ?)",
                   (group_id, other["id"], now()))
        db.execute("INSERT INTO message (group_id, sender_id, text, created_at) VALUES (?, ?, ?, ?)",
                   (group_id, me["id"], f"{me['name']} added {other['name']} to the group.", now()))
    return jsonify(group_view(group_id, me)), 201


@app.post("/api/groups/<int:group_id>/leave")
def leave(group_id):
    """Forlad gruppen. Historikken bevares, og de øvrige medlemmer beholder shortlisten."""
    me = current_buyer()
    require_member(me, group_id)
    with transaction() as db:
        db.execute("UPDATE group_member SET left_at = ? WHERE group_id = ? AND buyer_id = ? AND left_at IS NULL",
                   (now(), group_id, me["id"]))
        db.execute("INSERT INTO message (group_id, sender_id, text, created_at) VALUES (?, ?, ?, ?)",
                   (group_id, me["id"], f"{me['name']} left the group.", now()))
    return jsonify(left=True, group_id=group_id)


@app.post("/api/groups/<int:group_id>/messages")
def send_message(group_id):
    """Skriv til gruppen uden at dele personlige kontaktoplysninger."""
    me = current_buyer()
    require_member(me, group_id)
    data = json_body()
    require(data, "text")
    with transaction() as db:
        db.execute("INSERT INTO message (group_id, sender_id, text, created_at) VALUES (?, ?, ?, ?)",
                   (group_id, me["id"], data["text"].strip(), now()))
    return jsonify(group_view(group_id, me)), 201


# ---------------------------------------------------------------- Boligmatch for en dannet gruppe
@app.get("/api/groups/<int:group_id>/properties")
def group_properties(group_id):
    """Boliger inden for gruppens samlede købekraft og pladsbehov, bedste match først."""
    me = current_buyer()
    require_member(me, group_id)
    group_members = members(group_id)
    power = group_power(group_members)
    rows = query_all("SELECT * FROM property WHERE price <= ? AND area >= ? ORDER BY price",
                     (power["purchasing_power"], power["required_area"]))
    shortlisted = {r["property_id"] for r in query_all("SELECT property_id FROM shortlist_item WHERE group_id = ?",
                                                        (group_id,))}
    result = []
    for p in rows:
        fit, reasons = 50, [f"Within purchasing power ({p['price']:,} ≤ {power['purchasing_power']:,} DKK)".replace(",", ".")]
        if p["location"] in power["locations"]:
            fit += 20
            reasons.append(f"Preferred location: {p['location']}")
        if p["property_type"] in power["property_types"]:
            fit += 15
            reasons.append("Preferred property type")
        if p["transport_min"] <= power["max_transport_min"]:
            fit += 15
            reasons.append(f"{p['transport_min']} min to the centre")
        result.append({**p, "fit": fit, "reasons": reasons, "shortlisted": p["id"] in shortlisted,
                       "price_per_member": round(p["price"] / len(group_members))})
    result.sort(key=lambda p: (-p["fit"], p["price"]))
    return jsonify(power=power, properties=result)


# ---------------------------------------------------------------- Fælles shortlist: gem, stem og diskutér
@app.post("/api/groups/<int:group_id>/shortlist")
def add_to_shortlist(group_id):
    """Gem en bolig på gruppens fælles shortlist."""
    me = current_buyer()
    require_member(me, group_id)
    data = json_body()
    require(data, "property_id")
    get_or_404("property", data["property_id"], "Property")
    with transaction() as db:
        db.execute("INSERT INTO shortlist_item (group_id, property_id, added_by, added_at) VALUES (?, ?, ?, ?)",
                   (group_id, data["property_id"], me["id"], now()))
    return jsonify(group_view(group_id, me)), 201


@app.post("/api/shortlist/<int:item_id>/vote")
def vote(item_id):
    """Stem for (+1) eller imod (−1) en bolig på shortlisten med en valgfri kommentar. En ny stemme erstatter den gamle."""
    me = current_buyer()
    item = get_or_404("shortlist_item", item_id, "Shortlist item")
    require_member(me, item["group_id"])
    data = json_body()
    require(data, "value")
    if data["value"] not in (1, -1):
        raise ApiError("A vote must be 1 or -1")
    with transaction() as db:
        db.execute("""INSERT INTO vote (shortlist_item_id, buyer_id, value, comment, created_at) VALUES (?, ?, ?, ?, ?)
                      ON CONFLICT (shortlist_item_id, buyer_id) DO UPDATE SET value = excluded.value,
                          comment = excluded.comment, created_at = excluded.created_at""",
                   (item_id, me["id"], data["value"], data.get("comment"), now()))
    return jsonify(group_view(item["group_id"], me))


# ---------------------------------------------------------------- Fremvisninger
@app.post("/api/groups/<int:group_id>/viewings")
def request_viewing(group_id):
    """Anmod om åbent hus eller privat fremvisning via gruppens fælles profil."""
    me = current_buyer()
    require_member(me, group_id)
    data = json_body()
    require(data, "property_id", "type", "preferred_date")
    if data["type"] not in ("OPEN_HOUSE", "PRIVATE"):
        raise ApiError("Type must be OPEN_HOUSE or PRIVATE")
    get_or_404("property", data["property_id"], "Property")
    if query_one("""SELECT id FROM viewing_request WHERE group_id = ? AND property_id = ? AND status != 'DECLINED'""",
                 (group_id, data["property_id"])):
        raise ApiError("The group has already requested a viewing of this property", 409)
    with transaction() as db:
        db.execute("""INSERT INTO viewing_request (group_id, property_id, requested_by, type, preferred_date, created_at)
                      VALUES (?, ?, ?, ?, ?, ?)""",
                   (group_id, data["property_id"], me["id"], data["type"], data["preferred_date"], now()))
    return jsonify(group_view(group_id, me)), 201


# ---------------------------------------------------------------- &LIVING-mæglere: kvalificerede købergrupper
@app.get("/api/agent/groups")
def agent_groups():
    """Kvalificerede købergrupper (mindst to medlemmer) med købekraft, shortlist og fremvisningsønsker."""
    result = []
    for group in query_all("SELECT g.*, a.name AS agent_name FROM buyer_group g LEFT JOIN agent a ON a.id = g.agent_id"):
        group_members = members(group["id"])
        if len(group_members) < 2:
            continue
        result.append({**group, **group_power(group_members), "members": [m["name"] for m in group_members],
                       "shortlist": query_one("SELECT COUNT(*) AS n FROM shortlist_item WHERE group_id = ?",
                                              (group["id"],))["n"]})
    viewings = query_all("""SELECT v.*, p.address, g.name AS group_name FROM viewing_request v
                            JOIN property p ON p.id = v.property_id JOIN buyer_group g ON g.id = v.group_id
                            ORDER BY v.status = 'REQUESTED' DESC, v.preferred_date""")
    return jsonify(groups=result, viewings=viewings)


@app.put("/api/viewings/<int:viewing_id>")
def answer_viewing(viewing_id):
    """Mægleren bekræfter eller afviser en fremvisning."""
    get_or_404("viewing_request", viewing_id, "Viewing request")
    data = json_body()
    require(data, "status")
    if data["status"] not in ("CONFIRMED", "DECLINED"):
        raise ApiError("Status must be CONFIRMED or DECLINED")
    with transaction() as db:
        db.execute("UPDATE viewing_request SET status = ?, agent_note = ? WHERE id = ?",
                   (data["status"], data.get("agent_note"), viewing_id))
    return jsonify(get_or_404("viewing_request", viewing_id))


if __name__ == "__main__":
    init_db()
    run(app, PORT)
