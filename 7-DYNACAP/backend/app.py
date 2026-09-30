"""DYNACAP Academy – oplæringsportal for nye konsulenter. Flask API (logiklag).

Kravgrundlag: ../Kravspecifikation.md (F1–F8 og afsnit 10–17)
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5207

Brugeren vælges i frontenden og sendes i headeren X-User-Id (simuleret DYNACAP-login).
Rollen styrer adgangen: konsulenten ser kun sig selv, vejlederen sine konsulenter, HR og ledelsen alle.
"""
import json
import os
from datetime import date, timedelta

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5207))
app = create_app(__name__, "DYNACAP Academy")

REPORT_INTERVAL_DAYS = 14          # F7: statusrapport hver 14. dag


# ---------------------------------------------------------------- Simuleret login og roller (afsnit 15)
def current_user():
    user_id = request.headers.get("X-User-Id")
    user = query_one("SELECT * FROM person WHERE id = ?", (user_id,)) if user_id and user_id.isdigit() else None
    if user is None:
        raise ApiError("Log ind med din DYNACAP-konto (header X-User-Id mangler eller er ugyldig)", 401)
    return user


def require_role(user, *roles):
    if user["role"] not in roles:
        raise ApiError("Din rolle giver ikke adgang til denne funktion", 403)


def can_see(user, consultant):
    """Konsulenter ser kun egne vurderinger. Vejledere ser deres egne konsulenter. HR og ledelse ser alle."""
    return (user["role"] in ("HR", "LEDELSE") or user["id"] == consultant["id"]
            or (user["role"] == "VEJLEDER" and consultant["mentor_id"] == user["id"]))


def get_consultant(consultant_id, user):
    consultant = query_one("SELECT * FROM person WHERE id = ? AND role = 'KONSULENT'", (consultant_id,))
    if consultant is None:
        raise ApiError(f"Konsulent med id {consultant_id} findes ikke", 404)
    if not can_see(user, consultant):
        raise ApiError("Du kan kun se dine egne oplysninger", 403)
    return consultant


@app.before_request
def only_hr_changes_content():
    """F14: HR ændrer indhold og krav i niveauerne – uden udvikler, men heller ikke alle andre."""
    if request.method in ("POST", "PUT", "DELETE") and request.path.startswith(("/api/levels", "/api/activities", "/api/offices")):
        require_role(current_user(), "HR")


def lang():
    return "en" if request.args.get("lang") == "en" else "da"


# ---------------------------------------------------------------- Fremdrift: aktuelt niveau og næste skridt (F2, F5)
def progress(consultant):
    """Status for alle seks niveauer. Et niveau er låst, indtil niveauet før er godkendt (F5)."""
    l = lang()
    levels = query_all("SELECT * FROM level ORDER BY number")
    done = {r["activity_id"]: r["completed_at"] for r in query_all(
        "SELECT activity_id, completed_at FROM activity_completion WHERE consultant_id = ?", (consultant["id"],))}
    reviews = query_all("""SELECT r.*, m.name AS mentor_name FROM level_review r JOIN person m ON m.id = r.mentor_id
                           WHERE r.consultant_id = ? ORDER BY r.id""", (consultant["id"],))
    certifications = query_all("SELECT * FROM certification WHERE consultant_id = ? ORDER BY passed_at",
                               (consultant["id"],))
    cert_names = {c["name"] for c in certifications}

    result, unlocked, current = [], True, None
    for level in levels:
        activities = query_all("SELECT * FROM activity WHERE level_id = ? ORDER BY sort, id", (level["id"],))
        level_reviews = [r for r in reviews if r["level_id"] == level["id"]]
        latest = level_reviews[-1] if level_reviews else None
        approved = latest is not None and latest["decision"] == "GODKENDT"
        if approved:
            status = "GODKENDT"
        elif unlocked:
            status = "AKTUEL"
            current = level
        else:
            status = "LÅST"
        items = [{"id": a["id"], "title": a[f"title_{l}"], "type": a["type"], "link": a["link"],
                  "completed_at": done.get(a["id"])} for a in activities]
        missing = [a["title"] for a in items if not a["completed_at"]]
        cert_missing = level["requires_certification"] and level["requires_certification"] not in cert_names
        result.append({
            "id": level["id"], "number": level["number"], "title": level[f"title_{l}"], "goal": level[f"goal_{l}"],
            "learning_form": level["learning_form"],
            "estimate": f"{level['estimate_weeks_min']}–{level['estimate_weeks_max']}",
            "status": status, "activities": items if status != "LÅST" else [],
            "activity_count": len(items), "completed_count": len(items) - len(missing),
            "missing": missing if status != "LÅST" else [],
            "requires_certification": level["requires_certification"], "certification_missing": bool(cert_missing),
            "ready_for_review": status == "AKTUEL" and not missing and not cert_missing,
            "latest_review": latest, "reviews": level_reviews,
        })
        unlocked = approved and unlocked

    approved_count = sum(1 for r in result if r["status"] == "GODKENDT")
    expected = expected_level(consultant["start_date"])
    if current is None:
        next_step = "Fuldt oplært – du kan vejlede nye konsulenter." if l == "da" else "Fully trained – you can mentor new consultants."
    else:
        cur = next(r for r in result if r["id"] == current["id"])
        if cur["missing"]:
            next_step = (f"Næste skridt: {cur['missing'][0]}" if l == "da" else f"Next step: {cur['missing'][0]}")
        elif cur["certification_missing"]:
            next_step = (f"Registrér certificeringen {cur['requires_certification']}" if l == "da"
                         else f"Register the {cur['requires_certification']} certification")
        else:
            next_step = ("Alt er gennemført – din vejleder skal godkende niveauet." if l == "da"
                         else "Everything is done – your mentor needs to approve the level.")
    return {"consultant": {k: consultant[k] for k in ("id", "name", "email", "office_id", "language", "mentor_id", "start_date")},
            "current_level": current["number"] if current else 6, "fully_trained": current is None,
            "approved_levels": approved_count, "expected_level": expected,
            "on_track": approved_count + 1 >= expected or current is None,
            "percent": round(100 * sum(r["completed_count"] for r in result) / max(1, sum(r["activity_count"] for r in result))),
            "next_step": next_step, "levels": result, "certifications": certifications}


def expected_level(start_date):
    """Hvilket niveau konsulenten burde være på ifølge estimaterne (maks-estimat, ca. 20 t/uge)."""
    if not start_date:
        return 1
    weeks = (date.today() - date.fromisoformat(start_date)).days / 7
    total = 0
    for level in query_all("SELECT number, estimate_weeks_max FROM level ORDER BY number"):
        total += level["estimate_weeks_max"]
        if weeks < total:
            return level["number"]
    return 6


# ---------------------------------------------------------------- CRUD (niveauer og aktiviteter ændres kun af HR)
register_crud(app, "offices", "office", fields=["name", "country"], required=["name", "country"])
register_crud(app, "levels", "level",
              fields=["number", "title_da", "title_en", "goal_da", "goal_en", "learning_form", "estimate_weeks_min",
                      "estimate_weeks_max", "requires_certification"],
              required=["number", "title_da", "title_en", "goal_da", "goal_en", "learning_form", "estimate_weeks_min",
                        "estimate_weeks_max"], order_by="number")
register_crud(app, "activities", "activity", fields=["level_id", "title_da", "title_en", "type", "link", "sort"],
              required=["level_id", "title_da", "title_en", "type"], order_by="level_id, sort, id")


@app.get("/api/people")
def people():
    """Testbrugere til det simulerede login."""
    return jsonify(query_all("""SELECT p.id, p.name, p.role, p.language, o.name AS office FROM person p
                                JOIN office o ON o.id = p.office_id ORDER BY p.role, p.name"""))


@app.get("/api/me")
def me():
    """Den indloggede bruger."""
    return jsonify(current_user())


# ---------------------------------------------------------------- Konsulenter
@app.get("/api/consultants")
def consultants():
    """Konsulenter, brugeren må se, med niveau og fremdrift."""
    user = current_user()
    rows = query_all("""SELECT p.*, o.name AS office, m.name AS mentor FROM person p JOIN office o ON o.id = p.office_id
                        LEFT JOIN person m ON m.id = p.mentor_id WHERE p.role = 'KONSULENT' ORDER BY o.name, p.name""")
    result = []
    for c in rows:
        if can_see(user, c):
            p = progress(c)
            pending = next((lv for lv in p["levels"] if lv["ready_for_review"]), None)
            result.append({"id": c["id"], "name": c["name"], "office": c["office"], "mentor": c["mentor"],
                           "start_date": c["start_date"], "current_level": p["current_level"],
                           "fully_trained": p["fully_trained"], "expected_level": p["expected_level"],
                           "on_track": p["on_track"], "percent": p["percent"],
                           "awaiting_review": pending["number"] if pending else None})
    return jsonify(result)


@app.post("/api/consultants")
def create_consultant():
    """HR opretter en ny konsulent med et forløb med de seks niveauer – uden udvikler (F1)."""
    user = current_user()
    require_role(user, "HR")
    data = json_body()
    require(data, "name", "email", "office_id", "mentor_id", "start_date")
    mentor = get_or_404("person", data["mentor_id"], "Vejleder")
    if mentor["role"] != "VEJLEDER":
        raise ApiError("Den valgte person er ikke vejleder")
    get_or_404("office", data["office_id"], "Kontor")
    with transaction() as db:
        consultant_id = db.execute(
            """INSERT INTO person (name, email, role, office_id, language, mentor_id, start_date)
               VALUES (?, ?, 'KONSULENT', ?, ?, ?, ?)""",
            (data["name"], data["email"], data["office_id"], data.get("language") or "da", mentor["id"],
             data["start_date"])).lastrowid
        db.execute("INSERT INTO programme (consultant_id, created_by, created_at) VALUES (?, ?, ?)",
                   (consultant_id, user["id"], now()))
    return jsonify(progress(get_or_404("person", consultant_id))), 201


@app.get("/api/consultants/<int:consultant_id>/progress")
def consultant_progress(consultant_id):
    """Konsulentens forside: aktuelt niveau, fremdrift og hvad der mangler til næste niveau (F2). ?lang=en for engelsk."""
    user = current_user()
    return jsonify(progress(get_consultant(consultant_id, user)))


@app.post("/api/consultants/<int:consultant_id>/activities/<int:activity_id>/toggle")
def toggle_activity(consultant_id, activity_id):
    """Konsulenten markerer en aktivitet som gennemført (eller fortryder). Status opdateres med det samme (F3)."""
    user = current_user()
    consultant = get_consultant(consultant_id, user)
    if user["id"] != consultant_id:
        raise ApiError("Kun konsulenten selv kan markere sine aktiviteter", 403)
    activity = get_or_404("activity", activity_id, "Aktivitet")
    level = next(lv for lv in progress(consultant)["levels"] if lv["id"] == activity["level_id"])
    if level["status"] != "AKTUEL":
        raise ApiError("Niveauet er låst eller allerede godkendt", 409)
    with transaction() as db:
        deleted = db.execute("DELETE FROM activity_completion WHERE consultant_id = ? AND activity_id = ?",
                             (consultant_id, activity_id)).rowcount
        if not deleted:
            db.execute("INSERT INTO activity_completion (consultant_id, activity_id, completed_at) VALUES (?, ?, ?)",
                       (consultant_id, activity_id, now()))
    return jsonify(progress(consultant))


@app.post("/api/consultants/<int:consultant_id>/levels/<int:level_id>/review")
def review_level(consultant_id, level_id):
    """Vejlederen godkender eller afviser et niveau med kommentar. Godkendelse låser op for næste niveau (F4, F5)."""
    user = current_user()
    consultant = get_consultant(consultant_id, user)
    if not (user["role"] == "VEJLEDER" and consultant["mentor_id"] == user["id"]):
        raise ApiError("Kun konsulentens vejleder kan godkende niveauer", 403)
    data = json_body()
    require(data, "decision")
    if data["decision"] not in ("GODKENDT", "AFVIST"):
        raise ApiError("Beslutningen skal være GODKENDT eller AFVIST")
    if data["decision"] == "AFVIST" and not (data.get("comment") or "").strip():
        raise ApiError("Skriv en kommentar, så konsulenten ved, hvad der mangler")
    level = next((lv for lv in progress(consultant)["levels"] if lv["id"] == level_id), None)
    if level is None:
        raise ApiError(f"Niveau med id {level_id} findes ikke", 404)
    if level["status"] != "AKTUEL":
        raise ApiError("Kun konsulentens aktuelle niveau kan vurderes", 409)
    if data["decision"] == "GODKENDT" and level["missing"]:
        raise ApiError("Niveauet kan ikke godkendes, før alle aktiviteter er gennemført: " + ", ".join(level["missing"]))
    if data["decision"] == "GODKENDT" and level["certification_missing"]:
        raise ApiError(f"Niveauet kræver certificeringen {level['requires_certification']}")
    with transaction() as db:
        db.execute("""INSERT INTO level_review (consultant_id, level_id, mentor_id, decision, comment, reviewed_at)
                      VALUES (?, ?, ?, ?, ?, ?)""",
                   (consultant_id, level_id, user["id"], data["decision"], data.get("comment"), now()))
    return jsonify(progress(consultant)), 201


@app.post("/api/consultants/<int:consultant_id>/certifications")
def register_certification(consultant_id):
    """Registrér en bestået Salesforce-certificering manuelt (F8)."""
    user = current_user()
    consultant = get_consultant(consultant_id, user)
    if user["role"] == "LEDELSE":
        raise ApiError("Ledelsen kan ikke registrere certificeringer", 403)
    data = json_body()
    require(data, "name", "passed_at")
    if date.fromisoformat(data["passed_at"]) > date.today():
        raise ApiError("Datoen for beståelse kan ikke ligge i fremtiden")
    with transaction() as db:
        db.execute("INSERT INTO certification (consultant_id, name, passed_at, registered_by) VALUES (?, ?, ?, ?)",
                   (consultant_id, data["name"].strip(), data["passed_at"], user["id"]))
    return jsonify(progress(consultant)), 201


# ---------------------------------------------------------------- Statusrapport pr. kontor (F7, BUC 6)
def build_report():
    offices = query_all("SELECT * FROM office ORDER BY country, name")
    rows = []
    for office in offices:
        consultants = query_all("SELECT * FROM person WHERE role = 'KONSULENT' AND office_id = ?", (office["id"],))
        progresses = [progress(c) for c in consultants]
        first_project = [c for c, p in zip(consultants, progresses) if p["approved_levels"] >= 3]
        rows.append({
            "office": office["name"], "country": office["country"], "consultants": len(consultants),
            "average_level": round(sum(p["current_level"] for p in progresses) / len(progresses), 1) if progresses else None,
            "fully_trained": sum(p["fully_trained"] for p in progresses),
            "behind_plan": sum(not p["on_track"] for p in progresses),
            "awaiting_review": sum(any(lv["ready_for_review"] for lv in p["levels"]) for p in progresses),
            "on_project": len(first_project),
            "levels": {str(n): sum(p["current_level"] == n and not p["fully_trained"] for p in progresses) for n in range(1, 7)},
        })
    return rows


@app.get("/api/reports/status")
def status_report():
    """Statusrapport fordelt på kontor – samme niveaukrav i Danmark og Norge (F6, F7)."""
    user = current_user()
    require_role(user, "LEDELSE", "HR")
    last = query_one("SELECT * FROM status_report ORDER BY id DESC LIMIT 1")
    next_run = (date.fromisoformat(last["sent_at"][:10]) + timedelta(days=REPORT_INTERVAL_DAYS)).isoformat() if last else date.today().isoformat()
    return jsonify(offices=build_report(), interval_days=REPORT_INTERVAL_DAYS, next_automatic=next_run,
                   sent=query_all("SELECT id, sent_at, sent_to, trigger_type FROM status_report ORDER BY id DESC LIMIT 10"))


@app.post("/api/reports/send")
def send_report():
    """Send statusrapporten til ledelsen nu. I drift sker det automatisk hver 14. dag."""
    user = current_user()
    require_role(user, "LEDELSE", "HR")
    recipients = ", ".join(r["email"] for r in query_all("SELECT email FROM person WHERE role = 'LEDELSE'"))
    report = build_report()
    with transaction() as db:
        db.execute("INSERT INTO status_report (sent_at, sent_to, trigger_type, summary) VALUES (?, ?, 'MANUEL', ?)",
                   (now(), recipients, json.dumps(report, ensure_ascii=False)))
    return jsonify(sent_to=recipients, offices=report), 201


if __name__ == "__main__":
    init_db()
    run(app, PORT)
