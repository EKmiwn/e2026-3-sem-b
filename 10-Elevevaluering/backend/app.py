"""Elevevaluering (Læringsrum 2.0) – elever vurderer trivsel, læring og møbler. Flask API (logiklag).

Kravgrundlag: ../Kravspecifikation.md
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5210

Brugeren logger ind med sit brugernavn (simuleret login) og sendes derefter i headeren X-User-Id.
Rollen styrer brugerrettighederne: elev, lærer eller administrator (Læringsrum 2.0).
"""
import os
from datetime import date

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5210))
app = create_app(__name__, "Elevevaluering")

CATEGORIES = {"TRIVSEL": "Trivsel", "LÆRING": "Læring", "MØBLER": "Møbler", "MILJØ": "Miljø og larm"}
MIN_RESPONDENTS = 3     # færre svar vises ikke, så den enkelte elev ikke kan genkendes (sikker behandling af data)
FEEDBACK = {            # personlig feedback med konkrete forslag, når en kategori er lav
    "TRIVSEL": "Tal med din lærer eller en voksen, du er tryg ved, hvis du ikke har det godt i klassen.",
    "LÆRING": "Sig til din lærer, hvis du har svært ved at følge med – så kan I finde en løsning sammen.",
    "MØBLER": "Fortæl din lærer, hvad der er ubehageligt ved din plads. Dine svar bruges til at forbedre indretningen.",
    "MILJØ": "Prøv det stille hjørne eller høreværn, når der er meget larm.",
}


# ---------------------------------------------------------------- Login og rettigheder
@app.post("/api/login")
def login():
    """Log ind med brugernavn (simuleret – ingen adgangskode i prototypen)."""
    data = json_body()
    require(data, "username")
    user = query_one("SELECT * FROM app_user WHERE username = ?", (data["username"].strip().lower(),))
    if user is None:
        raise ApiError("Brugernavnet findes ikke", 401)
    return jsonify(user)


def current_user(*roles):
    user_id = request.headers.get("X-User-Id")
    user = query_one("SELECT * FROM app_user WHERE id = ?", (user_id,)) if user_id and user_id.isdigit() else None
    if user is None:
        raise ApiError("Log ind først", 401)
    if roles and user["role"] not in roles:
        raise ApiError("Din rolle giver ikke adgang til denne side", 403)
    return user


def check_class_access(user, class_id):
    """Læreren ser kun sin egen klasse. Administratoren (Læringsrum 2.0) ser alle."""
    cls = get_or_404("class", class_id, "Klasse")
    if user["role"] == "LÆRER" and user["class_id"] != class_id:
        raise ApiError("Du kan kun se resultater for din egen klasse", 403)
    if user["role"] == "ELEV":
        raise ApiError("Elever kan ikke se klassens samlede resultater", 403)
    return cls


def open_round():
    today = date.today().isoformat()
    return query_one("SELECT * FROM survey_round WHERE opens_on <= ? AND closes_on >= ? ORDER BY opens_on DESC",
                     (today, today))


# ---------------------------------------------------------------- Beregning: gennemsnit og procenttal
def summarise(values):
    n = len(values)
    if not n:
        return {"answers": 0, "average": None, "positive_pct": None, "negative_pct": None, "distribution": {}}
    return {"answers": n, "average": round(sum(values) / n, 2),
            "positive_pct": round(100 * sum(v >= 4 for v in values) / n),
            "negative_pct": round(100 * sum(v <= 2 for v in values) / n),
            "distribution": {str(k): round(100 * values.count(k) / n) for k in range(1, 6)}}


def class_answers(class_id, round_id):
    return query_all("""SELECT a.value, q.id AS question_id, q.text, q.category, q.emoji, r.student_id
                        FROM answer a JOIN response r ON r.id = a.response_id JOIN question q ON q.id = a.question_id
                        JOIN app_user u ON u.id = r.student_id
                        WHERE u.class_id = ? AND r.round_id = ? ORDER BY q.sort""", (class_id, round_id))


# ---------------------------------------------------------------- CRUD (administrator)
register_crud(app, "schools", "school", fields=["name", "city"], required=["name", "city"])
register_crud(app, "classes", "class", fields=["school_id", "name", "grade"], required=["school_id", "name", "grade"],
              order_by="school_id, grade, name")
register_crud(app, "questions", "question", fields=["text", "category", "emoji", "active", "sort"],
              required=["text", "category"], order_by="sort, id")
register_crud(app, "rounds", "survey_round", fields=["name", "opens_on", "closes_on"],
              required=["name", "opens_on", "closes_on"], order_by="opens_on")


@app.get("/api/users")
def users():
    """Testbrugere til login-siden (brugernavn og rolle)."""
    return jsonify(query_all("""SELECT u.id, u.name, u.username, u.role, c.name AS class_name FROM app_user u
                                LEFT JOIN class c ON c.id = u.class_id ORDER BY u.role, c.name, u.name"""))


# ---------------------------------------------------------------- Eleven: besvar spørgsmål og se egen udvikling
@app.get("/api/my/survey")
def my_survey():
    """Den åbne måling med spørgsmål – og om eleven allerede har svaret."""
    user = current_user("ELEV")
    rnd = open_round()
    if rnd is None:
        return jsonify(round=None, questions=[], answered=False)
    answered = query_one("SELECT id FROM response WHERE student_id = ? AND round_id = ?", (user["id"], rnd["id"]))
    return jsonify(round=rnd, answered=answered is not None,
                   questions=query_all("SELECT id, text, category, emoji FROM question WHERE active = 1 ORDER BY sort, id"))


@app.post("/api/my/responses")
def submit():
    """Gem elevens besvarelse (1–5 pr. spørgsmål). Svaret giver personlig feedback med det samme."""
    user = current_user("ELEV")
    rnd = open_round()
    if rnd is None:
        raise ApiError("Der er ingen åben måling lige nu")
    data = json_body()
    require(data, "answers")
    questions = query_all("SELECT id FROM question WHERE active = 1")
    answers = {int(k): int(v) for k, v in data["answers"].items()}
    missing = [q["id"] for q in questions if q["id"] not in answers]
    if missing:
        raise ApiError(f"Svar på alle spørgsmål – der mangler {len(missing)}")
    if any(not 1 <= v <= 5 for v in answers.values()):
        raise ApiError("Svarene skal være mellem 1 og 5")
    if query_one("SELECT id FROM response WHERE student_id = ? AND round_id = ?", (user["id"], rnd["id"])):
        raise ApiError("Du har allerede svaret i denne måling", 409)
    with transaction() as db:
        response_id = db.execute("INSERT INTO response (student_id, round_id, comment, submitted_at) VALUES (?, ?, ?, ?)",
                                 (user["id"], rnd["id"], (data.get("comment") or "").strip() or None, now())).lastrowid
        for question_id, value in answers.items():
            db.execute("INSERT INTO answer (response_id, question_id, value) VALUES (?, ?, ?)",
                       (response_id, question_id, value))
    return jsonify(my_development(user)), 201


def my_development(user):
    rows = query_all("""SELECT r.round_id, s.name AS round_name, s.opens_on, q.category, a.value
                        FROM response r JOIN answer a ON a.response_id = r.id JOIN question q ON q.id = a.question_id
                        JOIN survey_round s ON s.id = r.round_id WHERE r.student_id = ? ORDER BY s.opens_on""", (user["id"],))
    rounds = []
    for rid in dict.fromkeys(r["round_id"] for r in rows):
        rr = [r for r in rows if r["round_id"] == rid]
        rounds.append({"round_id": rid, "round_name": rr[0]["round_name"], "opens_on": rr[0]["opens_on"],
                       "categories": {c: summarise([r["value"] for r in rr if r["category"] == c])["average"]
                                      for c in CATEGORIES}})
    feedback = []
    if rounds:
        latest = rounds[-1]["categories"]
        previous = rounds[-2]["categories"] if len(rounds) > 1 else {}
        for cat, label in CATEGORIES.items():
            value = latest.get(cat)
            if value is None:
                continue
            change = round(value - previous[cat], 1) if previous.get(cat) is not None else None
            text = (f"{label}: {value:.1f} af 5" + (f" ({'+' if change > 0 else ''}{change} siden sidst)" if change else "")).replace(".", ",")
            feedback.append({"category": cat, "text": text, "change": change,
                             "tip": FEEDBACK[cat] if value < 3 else None,
                             "praise": "Godt at høre! 🎉" if change and change >= 0.5 else None})
    follow_ups = query_all("""SELECT f.*, u.name AS teacher FROM follow_up f JOIN app_user u ON u.id = f.teacher_id
                              WHERE f.class_id = ? ORDER BY f.id DESC""", (user["class_id"],))
    return {"rounds": rounds, "feedback": feedback, "follow_ups": follow_ups, "categories": CATEGORIES}


@app.get("/api/my/development")
def development():
    """Elevens egen udvikling over tid, personlig feedback og lærerens opfølgning ("Det gør vi nu")."""
    return jsonify(my_development(current_user("ELEV")))


# ---------------------------------------------------------------- Læreren: klassens resultater samlet
@app.get("/api/classes/<int:class_id>/results")
def class_results(class_id):
    """Klassens resultater for én måling: gennemsnit og procenttal pr. spørgsmål og kategori (kun ved mindst 3 svar)."""
    user = current_user("LÆRER", "ADMINISTRATOR")
    cls = check_class_access(user, class_id)
    round_id = request.args.get("round_id", type=int) or (open_round() or {}).get("id")
    rnd = get_or_404("survey_round", round_id, "Måling")
    rows = class_answers(class_id, round_id)
    students = query_one("SELECT COUNT(*) AS n FROM app_user WHERE role = 'ELEV' AND class_id = ?", (class_id,))["n"]
    respondents = len({r["student_id"] for r in rows})
    result = {"class": cls, "round": rnd, "students": students, "respondents": respondents,
              "participation_pct": round(100 * respondents / students) if students else 0,
              "hidden": respondents < MIN_RESPONDENTS, "min_respondents": MIN_RESPONDENTS,
              "categories": [], "questions": [], "comments": []}
    if result["hidden"]:
        return jsonify(result)
    for cat, label in CATEGORIES.items():
        result["categories"].append({"category": cat, "label": label,
                                     **summarise([r["value"] for r in rows if r["category"] == cat])})
    for qid in dict.fromkeys(r["question_id"] for r in rows):
        qrows = [r for r in rows if r["question_id"] == qid]
        result["questions"].append({"question_id": qid, "text": qrows[0]["text"], "category": qrows[0]["category"],
                                    "emoji": qrows[0]["emoji"], **summarise([r["value"] for r in qrows])})
    # Kommentarer vises uden navn
    result["comments"] = [r["comment"] for r in query_all(
        """SELECT r.comment FROM response r JOIN app_user u ON u.id = r.student_id
           WHERE u.class_id = ? AND r.round_id = ? AND r.comment IS NOT NULL ORDER BY r.id""", (class_id, round_id))]
    return jsonify(result)


@app.get("/api/classes/<int:class_id>/trend")
def class_trend(class_id):
    """Sammenlign klassens svar over tid: gennemsnit og andel positive pr. kategori for hver måling."""
    user = current_user("LÆRER", "ADMINISTRATOR")
    check_class_access(user, class_id)
    trend = []
    for rnd in query_all("SELECT * FROM survey_round ORDER BY opens_on"):
        rows = class_answers(class_id, rnd["id"])
        respondents = len({r["student_id"] for r in rows})
        entry = {"round_id": rnd["id"], "round_name": rnd["name"], "opens_on": rnd["opens_on"], "respondents": respondents,
                 "hidden": respondents < MIN_RESPONDENTS, "categories": {}}
        if not entry["hidden"]:
            for cat in CATEGORIES:
                s = summarise([r["value"] for r in rows if r["category"] == cat])
                entry["categories"][cat] = {"average": s["average"], "positive_pct": s["positive_pct"]}
        trend.append(entry)
    visible = [t for t in trend if not t["hidden"]]
    changes = {}
    if len(visible) >= 2:
        first, last = visible[0]["categories"], visible[-1]["categories"]
        changes = {cat: last[cat]["positive_pct"] - first[cat]["positive_pct"] for cat in CATEGORIES}
    return jsonify(trend=trend, change_positive_pct=changes, categories=CATEGORIES)


@app.post("/api/classes/<int:class_id>/follow-ups")
def add_follow_up(class_id):
    """Læreren fortæller klassen, hvad der gøres ved resultaterne – eleverne ser det på deres side."""
    user = current_user("LÆRER", "ADMINISTRATOR")
    check_class_access(user, class_id)
    data = json_body()
    require(data, "category", "text")
    if data["category"] not in CATEGORIES:
        raise ApiError("Ukendt kategori")
    with transaction() as db:
        db.execute("INSERT INTO follow_up (class_id, teacher_id, category, text, created_at) VALUES (?, ?, ?, ?, ?)",
                   (class_id, user["id"], data["category"], data["text"].strip(), now()))
    return jsonify(query_all("SELECT * FROM follow_up WHERE class_id = ? ORDER BY id DESC", (class_id,))), 201


# ---------------------------------------------------------------- Læringsrum 2.0: overblik på tværs af skoler
@app.get("/api/overview")
def overview():
    """Administratorens overblik: deltagelse og andel positive pr. kategori for alle klasser i hver måling."""
    current_user("ADMINISTRATOR")
    classes = query_all("""SELECT c.*, s.name AS school FROM class c JOIN school s ON s.id = c.school_id
                           ORDER BY s.name, c.grade, c.name""")
    rounds = query_all("SELECT * FROM survey_round ORDER BY opens_on")
    rows = []
    for cls in classes:
        students = query_one("SELECT COUNT(*) AS n FROM app_user WHERE role = 'ELEV' AND class_id = ?", (cls["id"],))["n"]
        for rnd in rounds:
            answers = class_answers(cls["id"], rnd["id"])
            respondents = len({a["student_id"] for a in answers})
            row = {"school": cls["school"], "class_id": cls["id"], "class": cls["name"], "round": rnd["name"],
                   "round_id": rnd["id"], "respondents": respondents, "students": students,
                   "hidden": respondents < MIN_RESPONDENTS}
            for cat in CATEGORIES:
                row[cat] = None if row["hidden"] else summarise([a["value"] for a in answers if a["category"] == cat])["positive_pct"]
            rows.append(row)
    return jsonify(rows=rows, categories=CATEGORIES, open_round=open_round())


if __name__ == "__main__":
    init_db()
    run(app, PORT)
