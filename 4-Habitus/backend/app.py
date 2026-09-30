"""Habitus – tale-til-tekst-dokumentation på botilbud. Flask API (logiklag).

Kravgrundlag: ../Kravspecifikation.md
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5204

Medarbejderen vælges i frontenden og sendes i headeren X-User-Id (simuleret login).
Man ser kun beboere og dokumentation fra sin egen afdeling – lederen ser alt.
"""
import json
import os
import re

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5204))
app = create_app(__name__, "Habitus Tale-til-tekst")

# Nøgleord pr. kategori. I virkeligheden en sprogmodel – her regler, så klassificeringen kan forklares.
KEYWORDS = {
    "MEDICIN": ["medicin", "pille", "piller", "tablet", "tabletter", "mg", "dosis", "pn", "gav ham", "gav hende",
                "fik udleveret", "indtog", "mikrogram"],
    "UDVIKLING": ["lærte", "lært", "selv", "for første gang", "mål", "fremskridt", "udvikling", "øvede", "klarede",
                  "selvstændig", "selvstændigt", "bedre til"],
    "OBSERVATION": ["humør", "glad", "ked af", "urolig", "rolig", "sov", "spiste", "træt", "vred", "tur", "besøg",
                    "grinede", "trist", "hovedpine", "ondt"],
}
HANDOVER_WORDS = ["næste vagt", "husk", "aftale", "overlever", "aftenvagt", "nattevagt"]
TARGET_FIELD = {
    "OBSERVATION": "Døgnrapport – observationer",
    "UDVIKLING": "Handleplan – udviklingsmål",
    "MEDICIN": "Medicinmodul – PN-registrering",
}
CONFIDENCE_LIMIT = 0.75      # under denne grænse markeres resultatet som usikkert
MANUAL_MINUTES = 6           # antaget tid for at skrive en post manuelt ved en computer


# ---------------------------------------------------------------- Simuleret login og adgang (afsnit 15)
def current_user():
    user_id = request.headers.get("X-User-Id")
    user = query_one("SELECT * FROM staff WHERE id = ?", (user_id,)) if user_id and user_id.isdigit() else None
    if user is None:
        raise ApiError("Vælg en medarbejder (header X-User-Id mangler eller er ugyldig)", 401)
    return user


def check_resident_access(user, resident_id):
    resident = get_or_404("resident", resident_id, "Beboer")
    if user["role"] != "LEDER" and resident["department_id"] != user["department_id"]:
        raise ApiError("Du har ikke adgang til beboere i en anden afdeling", 403)
    return resident


# ---------------------------------------------------------------- Transskription → klassificering → struktureret udkast
def contains(text, word):
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text) is not None


def analyse(text, transcript_confidence, residents, medications):
    """Klassificerer teksten, foreslår beboer og markerer alt, systemet er usikkert på."""
    lower = text.lower()
    hits = {cat: [w for w in words if contains(lower, w)] for cat, words in KEYWORDS.items()}
    med_names = {m["name"].lower() for m in medications}
    hits["MEDICIN"] += [name for name in med_names if contains(lower, name)]
    scores = {cat: len(words) for cat, words in hits.items()}
    total = sum(scores.values())
    # Ved lige mange træffere vinder medicin (højeste konsekvens ved fejl), derefter udvikling
    priority = {"MEDICIN": 2, "UDVIKLING": 1, "OBSERVATION": 0}
    category = max(scores, key=lambda c: (scores[c], priority[c])) if total else "OBSERVATION"
    category_confidence = round(scores[category] / total, 2) if total else 0.4

    uncertain = []
    if transcript_confidence < CONFIDENCE_LIMIT:
        uncertain.append({"type": "TRANSSKRIPTION", "text": f"Talegenkendelsen er usikker ({round(transcript_confidence * 100)} %). Læs teksten igennem."})
    if category_confidence < CONFIDENCE_LIMIT:
        uncertain.append({"type": "KATEGORI", "text": f"Usikker på kategorien – foreslår {category.lower()}. Vælg den rigtige."})

    # Forslag til beboer ud fra navn eller kaldenavn i talen
    suggested = [r for r in residents if contains(lower, r["name"].split()[0].lower())
                 or (r["nickname"] and contains(lower, r["nickname"].lower()))]
    return {
        "category": category, "category_confidence": category_confidence, "keywords": hits,
        "contains_medication": bool(hits["MEDICIN"]),
        "handover": any(contains(lower, w) for w in HANDOVER_WORDS),
        "suggested_resident_id": suggested[0]["id"] if len(suggested) == 1 else None,
        "uncertain": uncertain,
    }


def check_medication(text, resident_id, uncertain):
    """Nævnes medicin, som beboeren ikke har ordineret, markeres det – i stedet for at gætte stiltiende."""
    lower = text.lower()
    all_meds = {m["name"].lower() for m in query_all("SELECT name FROM medication")}
    own = {m["name"].lower() for m in query_all("SELECT name FROM medication WHERE resident_id = ?", (resident_id,))}
    for name in sorted(all_meds - own):
        if contains(lower, name):
            uncertain.append({"type": "MEDICIN", "text": f"{name.capitalize()} står ikke på beboerens medicinliste. Kontrollér navn og beboer."})
    if re.search(r"\d+\s*(mg|mikrogram)", lower) is None and any(contains(lower, n) for n in own):
        uncertain.append({"type": "MEDICIN", "text": "Dosis er ikke nævnt. Tilføj dosis før godkendelse."})


def recording_view(rec):
    rec = dict(rec)
    rec["uncertain"] = json.loads(rec["uncertain"])
    rec["target_field"] = TARGET_FIELD[rec["category"]]
    return rec


RECORDING_SQL = """SELECT r.*, s.name AS staff_name, res.name AS resident_name, sug.name AS suggested_resident_name
                   FROM recording r JOIN staff s ON s.id = r.staff_id
                   LEFT JOIN resident res ON res.id = r.resident_id
                   LEFT JOIN resident sug ON sug.id = r.suggested_resident_id"""


def save_journal(db, recording_id, resident_id, staff_id, category, text, handover):
    """Overfører godkendt tekst til det rette felt i Sofus – og til Outlook, hvis det er en besked til næste vagt."""
    db.execute("""INSERT INTO journal_entry (recording_id, resident_id, staff_id, target_system, target_field, category,
                                             text, created_at) VALUES (?, ?, ?, 'SOFUS', ?, ?, ?, ?)""",
               (recording_id, resident_id, staff_id, TARGET_FIELD[category], category, text, now()))
    if handover:
        db.execute("""INSERT INTO journal_entry (recording_id, resident_id, staff_id, target_system, target_field,
                                                 category, text, created_at)
                      VALUES (?, ?, ?, 'OUTLOOK', 'Vagtoverlevering til næste vagt', ?, ?, ?)""",
                   (recording_id, resident_id, staff_id, category, text, now()))


# ---------------------------------------------------------------- CRUD
register_crud(app, "departments", "department", fields=["name", "site"], required=["name", "site"])
register_crud(app, "staff", "staff", fields=["name", "role", "department_id"], required=["name", "role", "department_id"])
register_crud(app, "medications", "medication", fields=["resident_id", "name", "dose", "is_pn"],
              required=["resident_id", "name", "dose"], order_by="resident_id, name")
register_crud(app, "residents", "resident", fields=["name", "nickname", "room", "department_id"],
              required=["name", "department_id"], order_by="name")


@app.get("/api/my-residents")
def my_residents():
    """Beboere, som den indloggede medarbejder har adgang til (egen afdeling – lederen ser alle)."""
    user = current_user()
    if user["role"] == "LEDER":
        return jsonify(query_all("SELECT * FROM resident ORDER BY name"))
    return jsonify(query_all("SELECT * FROM resident WHERE department_id = ? ORDER BY name", (user["department_id"],)))


# ---------------------------------------------------------------- Optagelse (start/stop i frontenden) → udkast
@app.post("/api/recordings")
def create_recording():
    """Modtager en afsluttet optagelse som tekst og laver et struktureret udkast.
    Medicin og usikre resultater kræver altid godkendelse – øvrigt gemmes med det samme og kan rettes bagefter."""
    user = current_user()
    data = json_body()
    require(data, "transcript")
    text = " ".join(data["transcript"].split())
    if len(text) < 5:
        raise ApiError("Optagelsen er for kort – prøv igen")
    transcript_confidence = float(data.get("transcript_confidence") or 1.0)
    visible = query_all("SELECT * FROM resident" + ("" if user["role"] == "LEDER" else " WHERE department_id = ?"),
                        () if user["role"] == "LEDER" else (user["department_id"],))
    medications = query_all("SELECT * FROM medication")
    result = analyse(text, transcript_confidence, visible, medications)

    resident_id = data.get("resident_id")
    if resident_id:
        check_resident_access(user, resident_id)
        if result["suggested_resident_id"] and result["suggested_resident_id"] != resident_id:
            result["uncertain"].append({"type": "BEBOER", "text": "Talen nævner en anden beboer end den valgte. Kontrollér beboeren."})
    else:
        resident_id = None
        if result["suggested_resident_id"] is None:
            result["uncertain"].append({"type": "BEBOER", "text": "Kunne ikke genkende beboeren. Vælg beboer."})
    check_id = resident_id or result["suggested_resident_id"]
    if check_id and result["contains_medication"]:
        check_medication(text, check_id, result["uncertain"])

    # Kræver godkendelse: medicin (altid, jf. afsnit 8), usikkerhed, eller beboer ikke bekræftet
    requires_approval = result["contains_medication"] or bool(result["uncertain"]) or resident_id is None
    status = "AFVENTER_GODKENDELSE" if requires_approval else "GODKENDT"
    with transaction() as db:
        rec_id = db.execute(
            """INSERT INTO recording (staff_id, resident_id, suggested_resident_id, transcript, final_text, category,
                                      category_confidence, transcript_confidence, contains_medication, handover,
                                      uncertain, requires_approval, status, audio_stored, duration_sec, recorded_at,
                                      approved_at, approved_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], resident_id, result["suggested_resident_id"], text, None if requires_approval else text,
             result["category"], result["category_confidence"], transcript_confidence,
             int(result["contains_medication"]), int(result["handover"]), json.dumps(result["uncertain"], ensure_ascii=False),
             int(requires_approval), status, int(requires_approval), data.get("duration_sec"), now(),
             None if requires_approval else now(), None if requires_approval else user["id"])).lastrowid
        if not requires_approval:
            save_journal(db, rec_id, resident_id, user["id"], result["category"], text, result["handover"])
    rec = recording_view(query_one(RECORDING_SQL + " WHERE r.id = ?", (rec_id,)))
    return jsonify(recording=rec, keywords=result["keywords"],
                   message="Gemt i journalen – du kan rette eller slette posten bagefter." if not requires_approval
                   else "Udkastet afventer din godkendelse."), 201


@app.get("/api/recordings")
def list_recordings():
    """Optagelser i medarbejderens afdeling (filtrér med ?status=AFVENTER_GODKENDELSE)."""
    user = current_user()
    status = request.args.get("status")
    where = ["s.department_id = ?" if user["role"] != "LEDER" else "1 = 1"]
    params = [user["department_id"]] if user["role"] != "LEDER" else []
    if status:
        where.append("r.status = ?")
        params.append(status)
    rows = query_all(RECORDING_SQL + " WHERE " + " AND ".join(where) + " ORDER BY r.id DESC", tuple(params))
    return jsonify([recording_view(r) for r in rows])


@app.post("/api/recordings/<int:recording_id>/approve")
def approve(recording_id):
    """Medarbejderen gennemser, retter og godkender udkastet. Derefter overføres det, og lydfilen slettes."""
    user = current_user()
    rec = get_or_404("recording", recording_id, "Optagelse")
    if rec["status"] != "AFVENTER_GODKENDELSE":
        raise ApiError("Optagelsen er allerede behandlet", 409)
    data = json_body()
    resident_id = data.get("resident_id") or rec["resident_id"] or rec["suggested_resident_id"]
    if not resident_id:
        raise ApiError("Vælg hvilken beboer optagelsen handler om")
    check_resident_access(user, resident_id)
    text = " ".join((data.get("text") or rec["transcript"]).split())
    category = data.get("category") or rec["category"]
    if category not in TARGET_FIELD:
        raise ApiError("Ukendt kategori")
    if rec["contains_medication"] and not data.get("medication_confirmed"):
        raise ApiError("Medicinoplysninger skal bekræftes manuelt, før de gemmes")
    with transaction() as db:
        db.execute("""UPDATE recording SET status = 'GODKENDT', resident_id = ?, category = ?, final_text = ?,
                             audio_stored = 0, approved_at = ?, approved_by = ? WHERE id = ?""",
                   (resident_id, category, text, now(), user["id"], recording_id))
        save_journal(db, recording_id, resident_id, rec["staff_id"], category, text, rec["handover"])
    return jsonify(recording_view(query_one(RECORDING_SQL + " WHERE r.id = ?", (recording_id,))))


@app.post("/api/recordings/<int:recording_id>/reject")
def reject(recording_id):
    """Forkast et forkert genkendt udkast. Lydfilen slettes, og intet gemmes i journalen."""
    current_user()
    rec = get_or_404("recording", recording_id, "Optagelse")
    if rec["status"] != "AFVENTER_GODKENDELSE":
        raise ApiError("Optagelsen er allerede behandlet", 409)
    with transaction() as db:
        db.execute("UPDATE recording SET status = 'FORKASTET', audio_stored = 0 WHERE id = ?", (recording_id,))
    return jsonify(recording_view(query_one(RECORDING_SQL + " WHERE r.id = ?", (recording_id,))))


# ---------------------------------------------------------------- Journal: se, ret og slet efterfølgende
@app.get("/api/residents/<int:resident_id>/journal")
def journal(resident_id):
    """Beboerens dokumentation grupperet efter system og felt – som den ville stå i Sofus og Outlook."""
    user = current_user()
    resident = check_resident_access(user, resident_id)
    entries = query_all("""SELECT j.*, s.name AS staff_name, u.name AS updated_by_name FROM journal_entry j
                           JOIN staff s ON s.id = j.staff_id LEFT JOIN staff u ON u.id = j.updated_by
                           WHERE j.resident_id = ? ORDER BY j.id DESC""", (resident_id,))
    return jsonify(resident=resident, entries=entries,
                   medications=query_all("SELECT * FROM medication WHERE resident_id = ?", (resident_id,)))


@app.put("/api/journal/<int:entry_id>")
def edit_entry(entry_id):
    """Ret en post efterfølgende. Hvem og hvornår gemmes."""
    user = current_user()
    entry = get_or_404("journal_entry", entry_id, "Journalpost")
    check_resident_access(user, entry["resident_id"])
    data = json_body()
    require(data, "text")
    with transaction() as db:
        db.execute("UPDATE journal_entry SET text = ?, updated_at = ?, updated_by = ? WHERE id = ?",
                   (data["text"].strip(), now(), user["id"], entry_id))
    return jsonify(get_or_404("journal_entry", entry_id))


@app.delete("/api/journal/<int:entry_id>")
def delete_entry(entry_id):
    """Slet en forkert post."""
    user = current_user()
    entry = get_or_404("journal_entry", entry_id, "Journalpost")
    check_resident_access(user, entry["resident_id"])
    with transaction() as db:
        db.execute("DELETE FROM journal_entry WHERE id = ?", (entry_id,))
    return "", 204


# ---------------------------------------------------------------- Overblik
@app.get("/api/stats")
def stats():
    """Optagelser, godkendelser og anslået sparet tid til direkte beboerkontakt."""
    totals = query_one("""SELECT COUNT(*) AS recordings, SUM(status = 'GODKENDT') AS approved,
                                 SUM(status = 'AFVENTER_GODKENDELSE') AS pending, SUM(status = 'FORKASTET') AS rejected,
                                 SUM(requires_approval = 0) AS auto_saved, SUM(contains_medication) AS medication,
                                 SUM(audio_stored) AS audio_stored, COALESCE(SUM(duration_sec), 0) AS seconds
                          FROM recording""")
    entries = query_one("SELECT COUNT(*) AS n FROM journal_entry WHERE target_system = 'SOFUS'")["n"]
    saved = max(0, round(entries * MANUAL_MINUTES - totals["seconds"] / 60))
    return jsonify(**totals, journal_entries=entries, minutes_saved=saved,
                   per_category=query_all("SELECT category, COUNT(*) AS count FROM recording GROUP BY category"),
                   assumption=f"Anslået {MANUAL_MINUTES} min. pr. post ved manuel indtastning")


if __name__ == "__main__":
    init_db()
    run(app, PORT)
