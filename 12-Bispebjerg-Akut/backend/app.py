"""Bispebjerg Akutmodtagelse – digital patientregistrering. Flask API (logiklag).

Kravgrundlag: ../Kravspecifikation.md
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5212

Patienten registrerer sig uden login og slår sig selv op med registreringsnummer + fødselsdato.
Personalet vælges i frontenden og sendes i headeren X-User-Id (simuleret login).
Sygeplejersker og læger ser alle patienter – personale på en modtagende afdeling ser kun egne bestillinger.
"""
import os
import secrets
from datetime import date, datetime

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5212))
app = create_app(__name__, "Bispebjerg Akutmodtagelse")

INJURY_TYPES = ["SYGDOM", "FALD", "BRUD", "FORSTUVNING", "SÅR", "FORBRÆNDING", "HOVEDSKADE", "ANDET"]
TRIAGE_LEVELS = ["RØD", "ORANGE", "GUL", "GRØN", "BLÅ"]      # mest akut først
CLINICAL = ("SYGEPLEJERSKE", "LÆGE")
MAX_FILL_SECONDS = 5 * 60                                    # afsnit 11: højst 5 minutter at udfylde


# ---------------------------------------------------------------- Simuleret login og rollebaseret adgang (afsnit 15)
def current_user(*roles):
    user_id = request.headers.get("X-User-Id")
    user = query_one("SELECT * FROM staff WHERE id = ?", (user_id,)) if user_id and user_id.isdigit() else None
    if user is None:
        raise ApiError("Vælg en medarbejder (header X-User-Id mangler eller er ugyldig)", 401)
    if roles and user["role"] not in roles:
        raise ApiError("Din rolle har ikke adgang til denne funktion", 403)
    return user


def log(db, user, registration_id, action):
    db.execute("INSERT INTO access_log (staff_id, registration_id, action, created_at) VALUES (?, ?, ?, ?)",
               (user["id"], registration_id, action, now()))


def set_status(db, registration_id, status, staff_id=None):
    db.execute("UPDATE registration SET status = ? WHERE id = ?", (status, registration_id))
    db.execute("INSERT INTO status_event (registration_id, status, staff_id, created_at) VALUES (?, ?, ?, ?)",
               (registration_id, status, staff_id, now()))


def minutes_between(start, end=None):
    if not start:
        return None
    return int((datetime.fromisoformat(end or now()) - datetime.fromisoformat(start)).total_seconds() // 60)


# ---------------------------------------------------------------- Validering af patientens oplysninger (FR1)
def clean_patient_data(data):
    """Returnerer de helbredsoplysninger, der er sendt med, i valideret form."""
    clean = {}
    for field in ("symptoms", "medication", "allergies"):
        if field in data:
            clean[field] = " ".join(str(data[field] or "").split())
    if "symptoms" in clean and len(clean["symptoms"]) < 3:
        raise ApiError("Beskriv dine symptomer")
    if "injury_type" in data:
        if data["injury_type"] not in INJURY_TYPES:
            raise ApiError("Ukendt skadetype. Vælg en af: " + ", ".join(INJURY_TYPES))
        clean["injury_type"] = data["injury_type"]
    if "pain_level" in data:
        level = data["pain_level"]
        if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= 10:
            raise ApiError("Smertegrad skal være et helt tal fra 0 til 10")
        clean["pain_level"] = level
    return clean


def check_birth_date(value):
    try:
        born = date.fromisoformat(str(value))
    except ValueError:
        raise ApiError("Fødselsdato skal have formatet ÅÅÅÅ-MM-DD")
    if born > date.today() or born.year < 1900:
        raise ApiError("Fødselsdatoen er ikke gyldig")
    return born.isoformat()


def new_reg_number():
    while True:
        number = f"BBH-{secrets.randbelow(9000) + 1000}"
        if query_one("SELECT id FROM registration WHERE reg_number = ?", (number,)) is None:
            return number


def own_registration(reg_number, birth_date):
    """Patienten identificerer sig med registreringsnummer og fødselsdato."""
    reg = query_one("SELECT * FROM registration WHERE reg_number = ?", (reg_number.strip().upper(),))
    if reg is None or reg["birth_date"] != (birth_date or "").strip():
        raise ApiError("Registreringsnummer og fødselsdato passer ikke sammen", 404)
    return reg


EXAMINATION_SQL = """SELECT e.*, t.name AS exam_name, d.id AS department_id, d.name AS department_name,
                            o.name AS ordered_by_name, c.name AS completed_by_name
                     FROM examination e JOIN exam_type t ON t.id = e.exam_type_id
                     JOIN department d ON d.id = t.department_id JOIN staff o ON o.id = e.ordered_by
                     LEFT JOIN staff c ON c.id = e.completed_by"""


def patient_view(reg):
    """Det, patienten selv må se: egne oplysninger, status og forløb – ikke personalets noter og triage."""
    fields = ["reg_number", "name", "birth_date", "language", "symptoms", "injury_type", "pain_level", "medication",
              "allergies", "registered_from", "status", "created_at", "arrived_at", "patient_updated_at", "closed_at"]
    view = {f: reg[f] for f in fields}
    view["waited_minutes"] = minutes_between(reg["arrived_at"], reg["closed_at"])
    view["timeline"] = query_all("SELECT status, created_at FROM status_event WHERE registration_id = ? ORDER BY id",
                                 (reg["id"],))
    view["examinations"] = query_all("""SELECT t.name AS exam_name, e.status FROM examination e
                                        JOIN exam_type t ON t.id = e.exam_type_id
                                        WHERE e.registration_id = ? ORDER BY e.id""", (reg["id"],))
    return view


# ---------------------------------------------------------------- CRUD (opsætning)
def validate_staff(data, _existing):
    if data.get("role") not in (*CLINICAL, "AFDELING"):
        raise ApiError("Rollen skal være SYGEPLEJERSKE, LÆGE eller AFDELING")
    if data["role"] == "AFDELING" and not data.get("department_id"):
        raise ApiError("Personale med rollen AFDELING skal knyttes til en afdeling")


register_crud(app, "departments", "department", fields=["name"], required=["name"], order_by="name")
register_crud(app, "exam-types", "exam_type", fields=["name", "department_id"], required=["name", "department_id"],
              order_by="name")
register_crud(app, "staff", "staff", fields=["name", "role", "department_id"], required=["name", "role"],
              validate=validate_staff)


# ---------------------------------------------------------------- Patient: registrér, følg status og opdatér
@app.post("/api/patient/registrations")
def create_registration():
    """Patienten indtaster symptomer, skadetype, smertegrad, medicin og allergier og får et unikt registreringsnummer."""
    data = json_body()
    require(data, "name", "birth_date", "symptoms", "injury_type", "pain_level")
    if not data.get("consent"):
        raise ApiError("Du skal give samtykke til, at akutmodtagelsen behandler dine oplysninger")
    registered_from = data.get("registered_from", "VED_ANKOMST")
    if registered_from not in ("HJEMMEFRA", "VED_ANKOMST"):
        raise ApiError("registered_from skal være HJEMMEFRA eller VED_ANKOMST")
    language = data.get("language", "da")
    if language not in ("da", "en"):
        raise ApiError("Sproget skal være da eller en")
    clean = {"medication": "", "allergies": "", **clean_patient_data(data)}
    arrived = registered_from == "VED_ANKOMST"
    fill_seconds = data.get("fill_seconds") if isinstance(data.get("fill_seconds"), int) else None
    with transaction() as db:
        reg_id = db.execute(
            """INSERT INTO registration (reg_number, name, birth_date, language, symptoms, injury_type, pain_level,
                                         medication, allergies, registered_from, fill_seconds, status, created_at, arrived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'REGISTRERET', ?, ?)""",
            (new_reg_number(), " ".join(str(data["name"]).split()), check_birth_date(data["birth_date"]), language,
             clean["symptoms"], clean["injury_type"], clean["pain_level"], clean["medication"], clean["allergies"],
             registered_from, fill_seconds, now(), now() if arrived else None)).lastrowid
        set_status(db, reg_id, "REGISTRERET")
        if arrived:
            set_status(db, reg_id, "VENTER_PÅ_SYGEPLEJERSKE")
    return jsonify(patient_view(get_or_404("registration", reg_id))), 201


@app.get("/api/patient/registrations/<reg_number>")
def get_own_registration(reg_number):
    """Patienten ser egne oplysninger og status i forløbet (kræver ?birth_date=ÅÅÅÅ-MM-DD)."""
    return jsonify(patient_view(own_registration(reg_number, request.args.get("birth_date"))))


@app.put("/api/patient/registrations/<reg_number>")
def update_own_registration(reg_number):
    """Patienten opdaterer sine oplysninger ved behov. Personalet kan se, at der er ændret."""
    data = json_body()
    reg = own_registration(reg_number, data.get("birth_date"))
    if reg["status"] == "AFSLUTTET":
        raise ApiError("Forløbet er afsluttet og kan ikke ændres", 409)
    clean = clean_patient_data(data)
    if not clean:
        raise ApiError("Ingen felter at opdatere. Tilladte felter: symptoms, injury_type, pain_level, medication, allergies")
    assignments = ", ".join(f"{field} = ?" for field in clean)
    with transaction() as db:
        db.execute(f"UPDATE registration SET {assignments}, patient_updated_at = ? WHERE id = ?",
                   (*clean.values(), now(), reg["id"]))
    return jsonify(patient_view(get_or_404("registration", reg["id"])))


@app.post("/api/patient/registrations/<reg_number>/arrive")
def arrive(reg_number):
    """Patienten, der har registreret sig hjemmefra, melder sin ankomst og kommer i kø til sygeplejersken."""
    reg = own_registration(reg_number, json_body().get("birth_date"))
    if reg["status"] != "REGISTRERET":
        raise ApiError("Ankomsten er allerede registreret", 409)
    with transaction() as db:
        db.execute("UPDATE registration SET arrived_at = ? WHERE id = ?", (now(), reg["id"]))
        set_status(db, reg["id"], "VENTER_PÅ_SYGEPLEJERSKE")
    return jsonify(patient_view(get_or_404("registration", reg["id"])))


# ---------------------------------------------------------------- Personale: patientkø og patientprofil (FR3, FR4)
@app.get("/api/registrations")
def list_registrations():
    """Patientkøen for sygeplejersker og læger: ikke-vurderede først, derefter efter triage og ventetid (?status=… eller ?status=ALLE)."""
    current_user(*CLINICAL)
    status = request.args.get("status")
    where, params = "r.status != 'AFSLUTTET'", ()
    if status == "ALLE":
        where = "1 = 1"
    elif status:
        where, params = "r.status = ?", (status,)
    rows = query_all(f"""SELECT r.id, r.reg_number, r.name, r.birth_date, r.injury_type, r.pain_level, r.status,
                                r.triage_level, r.registered_from, r.created_at, r.arrived_at, r.closed_at,
                                COALESCE(r.patient_updated_at > COALESCE(r.triaged_at, ''), 0) AS updated_since_triage,
                                (SELECT COUNT(*) FROM examination e
                                 WHERE e.registration_id = r.id AND e.status = 'BESTILT') AS open_examinations
                         FROM registration r WHERE {where}
                         ORDER BY r.status = 'AFSLUTTET', r.status = 'REGISTRERET',
                                  CASE COALESCE(r.triage_level, '') WHEN '' THEN 0 WHEN 'RØD' THEN 1 WHEN 'ORANGE' THEN 2
                                       WHEN 'GUL' THEN 3 WHEN 'GRØN' THEN 4 ELSE 5 END,
                                  COALESCE(r.arrived_at, r.created_at)""", params)
    for row in rows:
        row["waited_minutes"] = minutes_between(row["arrived_at"], row["closed_at"])
    return jsonify(rows)


@app.get("/api/registrations/<int:registration_id>")
def get_registration(registration_id):
    """Patientprofil: symptomer, forløb, undersøgelser og tidligere besøg. Opslaget logges."""
    user = current_user(*CLINICAL)
    reg = get_or_404("registration", registration_id, "Registrering")
    # Ét opslag logges pr. medarbejder pr. 10 minutter, så loggen ikke fyldes, når siden genindlæses
    recent = query_one("SELECT created_at FROM access_log WHERE staff_id = ? AND registration_id = ? ORDER BY id DESC",
                       (user["id"], registration_id))
    if recent is None or minutes_between(recent["created_at"]) >= 10:
        with transaction() as db:
            log(db, user, registration_id, "Så patientens oplysninger")
    reg["waited_minutes"] = minutes_between(reg["arrived_at"], reg["closed_at"])
    reg["triaged_by_name"] = (query_one("SELECT name FROM staff WHERE id = ?", (reg["triaged_by"],)) or {}).get("name")
    return jsonify(
        registration=reg,
        timeline=query_all("""SELECT e.status, e.created_at, s.name AS staff_name FROM status_event e
                              LEFT JOIN staff s ON s.id = e.staff_id WHERE e.registration_id = ? ORDER BY e.id""",
                           (registration_id,)),
        examinations=query_all(EXAMINATION_SQL + " WHERE e.registration_id = ? ORDER BY e.id", (registration_id,)),
        history=query_all("""SELECT reg_number, created_at, symptoms, injury_type, triage_level, triage_note
                             FROM registration WHERE name = ? AND birth_date = ? AND id != ? ORDER BY created_at DESC""",
                          (reg["name"], reg["birth_date"], registration_id)))


@app.post("/api/registrations/<int:registration_id>/triage")
def triage(registration_id):
    """Sygeplejersken eller lægen sætter triageniveau og note. Systemet foreslår aldrig selv et niveau."""
    user = current_user(*CLINICAL)
    reg = get_or_404("registration", registration_id, "Registrering")
    if reg["status"] == "AFSLUTTET":
        raise ApiError("Forløbet er afsluttet", 409)
    if reg["status"] == "REGISTRERET":
        raise ApiError("Patienten er ikke ankommet endnu", 409)
    data = json_body()
    if data.get("triage_level") not in TRIAGE_LEVELS:
        raise ApiError("Vælg et triageniveau: " + ", ".join(TRIAGE_LEVELS))
    with transaction() as db:
        db.execute("UPDATE registration SET triage_level = ?, triage_note = ?, triaged_by = ?, triaged_at = ? WHERE id = ?",
                   (data["triage_level"], (data.get("triage_note") or "").strip() or None, user["id"], now(), registration_id))
        log(db, user, registration_id, f"Triage sat til {data['triage_level']}")
    return jsonify(get_or_404("registration", registration_id))


@app.post("/api/registrations/<int:registration_id>/status")
def change_status(registration_id):
    """Send patienten videre til lægen (VENTER_PÅ_LÆGE) eller afslut forløbet (AFSLUTTET – kun læger)."""
    user = current_user(*CLINICAL)
    reg = get_or_404("registration", registration_id, "Registrering")
    status = json_body().get("status")
    if status not in ("VENTER_PÅ_LÆGE", "AFSLUTTET"):
        raise ApiError("Status kan sættes til VENTER_PÅ_LÆGE eller AFSLUTTET")
    if reg["status"] in ("AFSLUTTET", status):
        raise ApiError("Forløbet har allerede denne status eller er afsluttet", 409)
    if reg["status"] == "REGISTRERET":
        raise ApiError("Patienten er ikke ankommet endnu", 409)
    if reg["triage_level"] is None:
        raise ApiError("Patienten skal vurderes (triage), før forløbet kan gå videre", 409)
    if status == "AFSLUTTET":
        if user["role"] != "LÆGE":
            raise ApiError("Kun en læge kan afslutte forløbet", 403)
        if query_one("SELECT id FROM examination WHERE registration_id = ? AND status = 'BESTILT'", (registration_id,)):
            raise ApiError("Der er bestilte undersøgelser, som ikke er udført", 409)
    with transaction() as db:
        if status == "AFSLUTTET":
            db.execute("UPDATE registration SET closed_at = ? WHERE id = ?", (now(), registration_id))
        set_status(db, registration_id, status, user["id"])
        log(db, user, registration_id, f"Status ændret til {status}")
    return jsonify(get_or_404("registration", registration_id))


# ---------------------------------------------------------------- Undersøgelser: bestil og send til afdeling (FR6, FR7)
@app.post("/api/registrations/<int:registration_id>/examinations")
def order_examinations(registration_id):
    """Personalet markerer behov for undersøgelser. Bestillingen sendes til den afdeling, der udfører den."""
    user = current_user(*CLINICAL)
    reg = get_or_404("registration", registration_id, "Registrering")
    if reg["status"] in ("REGISTRERET", "AFSLUTTET"):
        raise ApiError("Undersøgelser kan kun bestilles til patienter, der er ankommet og ikke afsluttet", 409)
    ids = json_body().get("exam_type_ids")
    if not isinstance(ids, list) or not ids:
        raise ApiError("Vælg mindst én undersøgelse (exam_type_ids)")
    types = [get_or_404("exam_type", type_id, "Undersøgelse") for type_id in dict.fromkeys(ids)]
    for exam_type in types:
        if query_one("SELECT id FROM examination WHERE registration_id = ? AND exam_type_id = ? AND status = 'BESTILT'",
                     (registration_id, exam_type["id"])):
            raise ApiError(f"{exam_type['name']} er allerede bestilt til patienten", 409)
    with transaction() as db:
        for exam_type in types:
            db.execute("INSERT INTO examination (registration_id, exam_type_id, ordered_by, ordered_at) VALUES (?, ?, ?, ?)",
                       (registration_id, exam_type["id"], user["id"], now()))
            log(db, user, registration_id, f"Bestilte undersøgelse: {exam_type['name']}")
        if reg["status"] != "UNDERSØGELSE_BESTILT":
            set_status(db, registration_id, "UNDERSØGELSE_BESTILT", user["id"])
    return jsonify(query_all(EXAMINATION_SQL + " WHERE e.registration_id = ? ORDER BY e.id", (registration_id,))), 201


@app.get("/api/examinations")
def list_examinations():
    """Bestilte undersøgelser. Afdelingspersonale ser kun egen afdeling og kun de oplysninger, undersøgelsen kræver (?status=BESTILT)."""
    user = current_user()
    where, params = ["1 = 1"], []
    if user["role"] == "AFDELING":
        where.append("d.id = ?")
        params.append(user["department_id"])
    if request.args.get("status"):
        where.append("e.status = ?")
        params.append(request.args["status"])
    sql = EXAMINATION_SQL.replace(" FROM examination e", """, r.reg_number, r.name AS patient_name, r.birth_date,
                                  r.injury_type, r.symptoms, r.allergies, r.triage_level
                                  FROM examination e JOIN registration r ON r.id = e.registration_id""")
    return jsonify(query_all(sql + " WHERE " + " AND ".join(where) + " ORDER BY e.status, e.ordered_at", tuple(params)))


@app.post("/api/examinations/<int:examination_id>/complete")
def complete_examination(examination_id):
    """Markér en undersøgelse som udført. Når alle patientens undersøgelser er udført, venter patienten på lægen."""
    user = current_user()
    exam = query_one(EXAMINATION_SQL + " WHERE e.id = ?", (examination_id,))
    if exam is None:
        raise ApiError(f"Undersøgelse med id {examination_id} findes ikke", 404)
    if user["role"] == "AFDELING" and user["department_id"] != exam["department_id"]:
        raise ApiError("Undersøgelsen hører til en anden afdeling", 403)
    if exam["status"] == "UDFØRT":
        raise ApiError("Undersøgelsen er allerede markeret som udført", 409)
    with transaction() as db:
        db.execute("UPDATE examination SET status = 'UDFØRT', completed_by = ?, completed_at = ? WHERE id = ?",
                   (user["id"], now(), examination_id))
        log(db, user, exam["registration_id"], f"Markerede {exam['exam_name']} som udført")
        remaining = db.execute("SELECT COUNT(*) FROM examination WHERE registration_id = ? AND status = 'BESTILT'",
                               (exam["registration_id"],)).fetchone()[0]
        reg = db.execute("SELECT status FROM registration WHERE id = ?", (exam["registration_id"],)).fetchone()
        if remaining == 0 and reg["status"] == "UNDERSØGELSE_BESTILT":
            set_status(db, exam["registration_id"], "VENTER_PÅ_LÆGE", user["id"])
    return jsonify(query_one(EXAMINATION_SQL + " WHERE e.id = ?", (examination_id,)))


# ---------------------------------------------------------------- Overblik og logning
@app.get("/api/stats")
def stats():
    """Nøgletal uden persondata: patienter pr. status, ventetid, udfyldelsestid og åbne undersøgelser."""
    rows = query_all("SELECT status, triage_level, registered_from, fill_seconds, arrived_at, closed_at FROM registration")
    active = [r for r in rows if r["status"] != "AFSLUTTET"]
    waits = [minutes_between(r["arrived_at"]) for r in active if r["arrived_at"]]
    fills = [r["fill_seconds"] for r in rows if r["fill_seconds"]]
    return jsonify(
        registrations=len(rows), active=len(active),
        not_arrived=sum(r["status"] == "REGISTRERET" for r in active),
        not_triaged=sum(r["status"] != "REGISTRERET" and r["triage_level"] is None for r in active),
        from_home=sum(r["registered_from"] == "HJEMMEFRA" for r in rows),
        open_examinations=query_one("SELECT COUNT(*) AS n FROM examination WHERE status = 'BESTILT'")["n"],
        avg_wait_minutes=round(sum(waits) / len(waits)) if waits else None,
        avg_fill_seconds=round(sum(fills) / len(fills)) if fills else None,
        within_fill_limit=sum(f <= MAX_FILL_SECONDS for f in fills), fill_measured=len(fills),
        per_status=query_all("SELECT status, COUNT(*) AS count FROM registration GROUP BY status"),
        assumption=f"Krav: registreringen skal kunne udfyldes på højst {MAX_FILL_SECONDS // 60} minutter")


@app.get("/api/access-log")
def access_log():
    """De seneste 50 opslag og ændringer i patientdata – hvem, hvad og hvornår."""
    current_user(*CLINICAL)
    return jsonify(query_all("""SELECT l.id, l.created_at, l.action, s.name AS staff_name, r.reg_number
                                FROM access_log l JOIN staff s ON s.id = l.staff_id
                                JOIN registration r ON r.id = l.registration_id ORDER BY l.id DESC LIMIT 50"""))


if __name__ == "__main__":
    init_db()
    run(app, PORT)
