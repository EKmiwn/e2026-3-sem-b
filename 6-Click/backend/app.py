"""Fotohuset Click – bestillingsplatform for billedprint. Flask API (logiklag).

Kravgrundlag: ../Kravspecifikation.md (FK1–FK23)
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5206

Kunden får adgang til sin ordre med ordre-id + tilfældig adgangsnøgle (?key=…).
Operatøren logger ind med PIN og sendes derefter i headeren X-User-Id (simuleret login).
"""
import json
import os
import secrets
from datetime import date, datetime, timedelta

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5206))
app = create_app(__name__, "Fotohuset Click")

FILE_TYPES = {"JPEG": "JPEG", "JPG": "JPEG", "PNG": "PNG", "TIFF": "TIFF", "TIF": "TIFF"}   # FK1
STATUS_FLOW = ["MODTAGET", "I_PRODUKTION", "KLAR", "AFHENTET"]               # FK19


def setting(key):
    row = query_one("SELECT value FROM setting WHERE key = ?", (key,))
    if row is None:
        raise ApiError(f"Indstillingen {key} mangler", 500)
    return row["value"]


# ---------------------------------------------------------------- 2.4.3 Beregn effektiv DPI
def effective_dpi(px_width, px_height, width_mm, height_mm, rotation=0):
    """Pixels divideret med printmål i tommer. Den laveste akse bestemmer skarpheden.
    Printet vendes efter billedet, så billedets lange side ligger på printets lange side."""
    if rotation in (90, 270):
        px_width, px_height = px_height, px_width
    long_px, short_px = max(px_width, px_height), min(px_width, px_height)
    long_in, short_in = max(width_mm, height_mm) / 25.4, min(width_mm, height_mm) / 25.4
    return round(min(long_px / long_in, short_px / short_in))


def validate_line(image, product, quantity, rotation):
    """2.4 Validér opløsning + 2.5 Beregn pris. Advarslen blokerer ikke, men forklarer konsekvensen (§11)."""
    if not 1 <= quantity <= 999:
        raise ApiError("Antal skal være mellem 1 og 999")
    if rotation not in (0, 90, 180, 270):
        raise ApiError("Billedet kan kun roteres i trin på 90 grader")
    dpi = effective_dpi(image["px_width"], image["px_height"], product["width_mm"], product["height_mm"], rotation)
    threshold = setting("dpi_threshold")
    warning = None
    if dpi < threshold:
        warning = (f"Billedet har kun {dpi} dpi i {product['label']} (anbefalet mindst {threshold:g}). "
                   f"Printet kan blive uskarpt. Vælg et mindre format for et skarpere billede.")
    return {"effective_dpi": dpi, "dpi_warning": warning, "unit_price": product["price"],
            "line_price": round(product["price"] * quantity, 2)}


# ---------------------------------------------------------------- Adgang
def customer_order(order_id):
    """Kundens adgang: ordre-id + tilfældig adgangsnøgle (§15)."""
    order = get_or_404("photo_order", order_id, "Ordre")
    if request.args.get("key") != order["access_key"]:
        raise ApiError("Forkert adgangsnøgle til ordren", 403)
    return order


def current_operator():
    user_id = request.headers.get("X-User-Id")
    operator = query_one("SELECT * FROM operator WHERE id = ?", (user_id,)) if user_id and user_id.isdigit() else None
    if operator is None:
        raise ApiError("Operatørfladen kræver login", 401)
    return operator


def order_view(order_id, include_thumbnails=True):
    order = get_or_404("photo_order", order_id, "Ordre")
    images = query_all(f"""SELECT id, filename, file_type, px_width, px_height, file_size, orientation, uploaded_at,
                                  deleted_at{', thumbnail' if include_thumbnails else ''}
                           FROM image WHERE order_id = ? ORDER BY id""", (order_id,))
    lines = query_all("""SELECT l.*, p.label, p.width_mm, p.height_mm, p.surface, p.quality, p.roll_width_mm, p.price AS unit_price, i.filename
                         FROM order_line l JOIN product p ON p.id = l.product_id JOIN image i ON i.id = l.image_id
                         WHERE l.order_id = ? ORDER BY l.id""", (order_id,))
    subtotal = round(sum(l["line_price"] for l in lines), 2)
    shipping = setting("shipping_price") if order["delivery"] == "FORSENDELSE" else 0
    customer = query_one("SELECT * FROM customer WHERE id = ?", (order["customer_id"],)) if order["customer_id"] else None
    return {**order, "customer": customer, "images": images, "lines": lines,
            "subtotal": subtotal, "shipping": shipping, "total_now": round(subtotal + shipping, 2),
            "warnings": sum(l["dpi_warning"] for l in lines)}


# ---------------------------------------------------------------- CRUD (FK23: indehaveren redigerer katalog og priser)
register_crud(app, "settings", "setting", fields=["key", "value", "description"], required=["key", "value"],
              update_fields=["value", "description"])
register_crud(app, "products", "product",
              fields=["label", "width_mm", "height_mm", "roll_width_mm", "surface", "quality", "price", "active"],
              required=["label", "width_mm", "height_mm", "roll_width_mm", "surface", "quality", "price"],
              order_by="width_mm, height_mm, surface, quality DESC")


# ---------------------------------------------------------------- Kundefladen: kurv, upload og konfiguration
@app.post("/api/orders")
def create_order():
    """Opretter en tom kurv med en tilfældig adgangsnøgle."""
    with transaction() as db:
        order_id = db.execute("INSERT INTO photo_order (access_key, created_at) VALUES (?, ?)",
                              (secrets.token_urlsafe(12), now())).lastrowid
    order = get_or_404("photo_order", order_id)
    return jsonify(id=order_id, access_key=order["access_key"]), 201


@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    """Kundens ordre med billeder, ordrelinjer og pris (kræver ?key=). Bruges også til indsigt (§17)."""
    customer_order(order_id)
    return jsonify(order_view(order_id))


@app.post("/api/orders/<int:order_id>/images")
def upload_image(order_id):
    """1.0 Håndtér billedupload: filtype, pixelmål, filstørrelse og miniature (FK1, FK2)."""
    order = customer_order(order_id)
    if order["status"] != "KURV":
        raise ApiError("Ordren er allerede bestilt – der kan ikke tilføjes billeder", 409)
    data = json_body()
    require(data, "filename", "file_type", "px_width", "px_height", "file_size")
    file_type = FILE_TYPES.get(data["file_type"].upper())
    if file_type is None:
        raise ApiError("Kun JPEG, TIFF og PNG kan uploades")
    w, h = int(data["px_width"]), int(data["px_height"])
    orientation = "LIGGENDE" if w > h else "STÅENDE" if h > w else "KVADRATISK"
    with transaction() as db:
        image_id = db.execute("""INSERT INTO image (order_id, filename, file_type, px_width, px_height, file_size,
                                                    orientation, thumbnail, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                              (order_id, data["filename"], file_type, w, h, int(data["file_size"]), orientation,
                               data.get("thumbnail"), now())).lastrowid
    return jsonify(get_or_404("image", image_id)), 201


@app.delete("/api/orders/<int:order_id>/images/<int:image_id>")
def delete_image(order_id, image_id):
    """Fjern et billede fra kurven (og dets ordrelinjer)."""
    order = customer_order(order_id)
    if order["status"] != "KURV":
        raise ApiError("Ordren er allerede bestilt", 409)
    with transaction() as db:
        db.execute("DELETE FROM image WHERE id = ? AND order_id = ?", (image_id, order_id))
    return "", 204


@app.post("/api/quote")
def quote():
    """Live pris og DPI-kontrol for ét billede i ét format (FK8, FK9 – vises inden for ét sekund)."""
    data = json_body()
    require(data, "px_width", "px_height", "product_id")
    product = get_or_404("product", data["product_id"], "Produkt")
    image = {"px_width": int(data["px_width"]), "px_height": int(data["px_height"])}
    return jsonify(validate_line(image, product, int(data.get("quantity") or 1), int(data.get("rotation") or 0)))


@app.post("/api/orders/<int:order_id>/lines")
def add_line(order_id):
    """2.0 Konfigurér printordre: format, overflade, kvalitet, beskæring, rotation og antal (FK3–FK9)."""
    order = customer_order(order_id)
    if order["status"] != "KURV":
        raise ApiError("Ordren er allerede bestilt", 409)
    data = json_body()
    require(data, "image_id", "product_id")
    image = get_or_404("image", data["image_id"], "Billede")
    if image["order_id"] != order_id:
        raise ApiError("Billedet hører ikke til denne ordre", 403)
    product = get_or_404("product", data["product_id"], "Produkt")
    if not product["active"]:
        raise ApiError("Formatet kan ikke bestilles lige nu")
    crop = data.get("crop") or "FYLD"
    if crop not in ("FYLD", "TILPAS_MED_KANT", "HELT_TIL_KANT"):
        raise ApiError("Beskæring skal være fyld, tilpas med kant eller helt til kant")
    quantity, rotation = int(data.get("quantity") or 1), int(data.get("rotation") or 0)
    result = validate_line(image, product, quantity, rotation)
    with transaction() as db:
        db.execute("""INSERT INTO order_line (order_id, image_id, product_id, quantity, crop, rotation, color_correction,
                                              effective_dpi, dpi_warning, line_price)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (order_id, image["id"], product["id"], quantity, crop, rotation,
                    0 if data.get("color_correction") is False else 1,
                    result["effective_dpi"], 1 if result["dpi_warning"] else 0, result["line_price"]))
    return jsonify(order=order_view(order_id), **result), 201


@app.delete("/api/orders/<int:order_id>/lines/<int:line_id>")
def delete_line(order_id, line_id):
    """Fjern en ordrelinje fra kurven."""
    order = customer_order(order_id)
    if order["status"] != "KURV":
        raise ApiError("Ordren er allerede bestilt", 409)
    with transaction() as db:
        db.execute("DELETE FROM order_line WHERE id = ? AND order_id = ?", (line_id, order_id))
    return "", 204


# ---------------------------------------------------------------- 3.0 Gennemfør betaling (FK10–FK13)
@app.post("/api/orders/<int:order_id>/checkout")
def checkout(order_id):
    """Kunden godkender kurven, vælger afhentning/forsendelse, udfylder kontaktoplysninger og giver samtykke."""
    order = customer_order(order_id)
    if order["status"] != "KURV":
        raise ApiError("Ordren er allerede bestilt", 409)
    data = json_body()
    require(data, "name", "email", "phone", "delivery")
    if data["delivery"] not in ("AFHENTNING", "FORSENDELSE"):
        raise ApiError("Vælg afhentning i butik eller forsendelse")
    if data["delivery"] == "FORSENDELSE" and not data.get("address"):
        raise ApiError("Skriv adressen, ordren skal sendes til")
    if not data.get("consent"):
        raise ApiError("Du skal give samtykke til, at vi gemmer dine billeder, indtil ordren er afhentet")
    if not query_one("SELECT id FROM order_line WHERE order_id = ?", (order_id,)):
        raise ApiError("Kurven er tom – vælg format til mindst ét billede")
    with transaction() as db:
        customer_id = db.execute("INSERT INTO customer (name, email, phone, address, created_at) VALUES (?, ?, ?, ?, ?)",
                                 (data["name"], data["email"], data["phone"], data.get("address"), now())).lastrowid
        db.execute("""UPDATE photo_order SET customer_id = ?, delivery = ?, consent_at = ?, note = ?,
                             payment_status = 'AFVENTER' WHERE id = ?""",
                   (customer_id, data["delivery"], now(), data.get("note"), order_id))
    view = order_view(order_id, include_thumbnails=False)
    # Kortoplysninger passerer aldrig systemet: kunden sendes videre til betalingsudbyderen
    return jsonify(order_id=order_id, amount=view["total_now"],
                   payment_url=f"https://betaling.example/pay?order={order_id}&amount={view['total_now']}")


@app.post("/api/orders/<int:order_id>/payment")
def payment_callback(order_id):
    """Svar fra betalingsudbyderen (simuleret). Ved godkendt betaling placeres ordren i produktionskøen (FK12, FK13)."""
    order = customer_order(order_id)
    if order["payment_status"] not in ("AFVENTER", "AFVIST"):
        raise ApiError("Ordren afventer ikke betaling", 409)
    approved = bool(json_body().get("approved"))
    if not approved:
        with transaction() as db:
            db.execute("UPDATE photo_order SET payment_status = 'AFVIST' WHERE id = ?", (order_id,))
        raise ApiError("Betalingen blev afvist. Prøv igen eller brug et andet kort.", 402)
    view = order_view(order_id, include_thumbnails=False)
    days = int(setting("production_days")) + (2 if order["delivery"] == "FORSENDELSE" else 0)
    ready = date.today()
    while days:
        ready += timedelta(days=1)
        if ready.weekday() < 5:
            days -= 1
    with transaction() as db:
        db.execute("""UPDATE photo_order SET payment_status = 'BETALT', payment_ref = ?, status = 'MODTAGET', total = ?,
                             received_at = ?, desired_ready = ? WHERE id = ?""",
                   (f"PAY-{secrets.token_hex(3).upper()}", view["total_now"], now(), ready.isoformat(), order_id))
    return jsonify(order_view(order_id))


@app.delete("/api/orders/<int:order_id>/images")
def delete_my_images(order_id):
    """Ret til sletning (§17): kunden sletter sine billedfiler. Ordrelinjerne bevares til regnskab."""
    customer_order(order_id)
    with transaction() as db:
        db.execute("UPDATE image SET thumbnail = NULL, deleted_at = ? WHERE order_id = ? AND deleted_at IS NULL",
                   (now(), order_id))
    return jsonify(order_view(order_id))


# ---------------------------------------------------------------- Operatørfladen (FK13–FK21)
@app.post("/api/operators/login")
def operator_login():
    """Operatøren logger ind med PIN (simuleret login)."""
    data = json_body()
    require(data, "pin")
    operator = query_one("SELECT id, name FROM operator WHERE pin = ?", (str(data["pin"]),))
    if operator is None:
        raise ApiError("Forkert PIN", 401)
    return jsonify(operator)


def purge_images():
    """1.0 Hændelse 10 (tidsstyret): billedfiler slettes, når opbevaringsfristen efter afhentning er udløbet (FK22)."""
    limit = (datetime.now() - timedelta(days=setting("retention_days"))).isoformat(sep=" ", timespec="seconds")
    with transaction() as db:
        cursor = db.execute("""UPDATE image SET thumbnail = NULL, deleted_at = ?
                               WHERE deleted_at IS NULL AND order_id IN
                                   (SELECT id FROM photo_order WHERE status = 'AFHENTET' AND closed_at < ?)""",
                            (now(), limit))
    return cursor.rowcount


@app.get("/api/queue")
def queue():
    """4.0 Produktionskøen sorteret efter ønsket færdigdato. Filtrér med ?roll_width=… (FK14, FK15)."""
    current_operator()
    purged = purge_images()
    roll = request.args.get("roll_width", type=int)
    orders = query_all("""SELECT o.*, c.name AS customer_name,
                                 (SELECT COUNT(*) FROM order_line l WHERE l.order_id = o.id) AS lines,
                                 (SELECT SUM(quantity) FROM order_line l WHERE l.order_id = o.id) AS prints,
                                 (SELECT SUM(dpi_warning) FROM order_line l WHERE l.order_id = o.id) AS warnings
                          FROM photo_order o LEFT JOIN customer c ON c.id = o.customer_id
                          WHERE o.status IN ('MODTAGET', 'I_PRODUKTION', 'KLAR')
                          ORDER BY o.desired_ready, o.received_at""")
    for order in orders:
        order["roll_widths"] = [r["roll_width_mm"] for r in query_all(
            """SELECT DISTINCT p.roll_width_mm FROM order_line l JOIN product p ON p.id = l.product_id
               WHERE l.order_id = ? ORDER BY p.roll_width_mm""", (order["id"],))]
    if roll:
        orders = [o for o in orders if roll in o["roll_widths"]]
    closed = query_all("""SELECT o.id, o.status, o.closed_at, c.name AS customer_name FROM photo_order o
                          JOIN customer c ON c.id = o.customer_id WHERE o.status = 'AFHENTET'
                          ORDER BY o.closed_at DESC LIMIT 10""")
    return jsonify(orders=orders, recently_closed=closed, images_purged=purged)


@app.get("/api/orders/<int:order_id>/slip")
def order_slip(order_id):
    """5.0 Ordreseddel: ordre-id, kunde og ordrelinjer grupperet efter papirrullebredde (FK16, FK17)."""
    current_operator()
    view = order_view(order_id, include_thumbnails=False)
    groups = {}
    for line in sorted(view["lines"], key=lambda l: (l["roll_width_mm"], l["label"])):
        groups.setdefault(line["roll_width_mm"], []).append(line)
    return jsonify(order_id=order_id, barcode=f"CLICK-{order_id:06d}", customer=view["customer"],
                   delivery=view["delivery"], desired_ready=view["desired_ready"], total=view["total"],
                   roll_groups=[{"roll_width_mm": k, "lines": v} for k, v in groups.items()],
                   roll_changes=max(0, len(groups) - 1))


@app.post("/api/orders/<int:order_id>/release")
def release(order_id):
    """Frigiv ordren til print: opretter printjobbet til C8 og sætter status 'i produktion' (FK18)."""
    operator = current_operator()
    order = get_or_404("photo_order", order_id, "Ordre")
    if order["status"] != "MODTAGET":
        raise ApiError("Kun modtagne ordrer kan frigives til print", 409)
    view = order_view(order_id, include_thumbnails=False)
    # Formatet, C8 accepterer, er et åbent punkt (§18) – her et JSON-forslag, som kan ændres ét sted
    payload = {"format": "C8-JSON (antaget – afklares, jf. §18)", "order_id": order_id,
               "jobs": [{"file": l["filename"], "width_mm": l["width_mm"], "height_mm": l["height_mm"],
                         "surface": l["surface"], "quality": l["quality"], "quantity": l["quantity"], "crop": l["crop"],
                         "rotation": l["rotation"], "color_correction": bool(l["color_correction"]),
                         "roll_width_mm": l["roll_width_mm"]}
                        for l in sorted(view["lines"], key=lambda l: l["roll_width_mm"])]}
    with transaction() as db:
        db.execute("INSERT INTO print_job (order_id, operator_id, payload, created_at) VALUES (?, ?, ?, ?)",
                   (order_id, operator["id"], json.dumps(payload, ensure_ascii=False), now()))
        db.execute("UPDATE photo_order SET status = 'I_PRODUKTION' WHERE id = ?", (order_id,))
    return jsonify(print_job=payload, order=order_view(order_id, include_thumbnails=False))


@app.put("/api/orders/<int:order_id>/status")
def change_status(order_id):
    """Operatøren skifter status manuelt. Ved 'klar' underrettes kunden (FK19–FK21)."""
    current_operator()
    order = get_or_404("photo_order", order_id, "Ordre")
    data = json_body()
    require(data, "status")
    new = data["status"]
    if new not in STATUS_FLOW or order["status"] not in STATUS_FLOW:
        raise ApiError("Ugyldig status")
    if abs(STATUS_FLOW.index(new) - STATUS_FLOW.index(order["status"])) != 1:
        raise ApiError(f"Status kan kun flyttes ét trin ad gangen (nu: {order['status'].lower().replace('_', ' ')})")
    message = None
    with transaction() as db:
        db.execute("UPDATE photo_order SET status = ?, closed_at = ? WHERE id = ?",
                   (new, now() if new == "AFHENTET" else None, order_id))
        if new == "KLAR" and not order["notified_at"]:
            customer = get_or_404("customer", order["customer_id"])
            message = (f"Hej {customer['name']}! Din ordre {order_id} er klar til afhentning i Fotohuset Click."
                       if order["delivery"] == "AFHENTNING" else f"Hej {customer['name']}! Din ordre {order_id} er sendt.")
            db.execute("UPDATE photo_order SET notified_at = ? WHERE id = ?", (now(), order_id))
    return jsonify(order=order_view(order_id, include_thumbnails=False), notification=message)


@app.post("/api/maintenance/purge-images")
def purge():
    """Kør sletning af billedfiler efter opbevaringsfristen nu (sker også automatisk, når køen åbnes)."""
    current_operator()
    return jsonify(images_deleted=purge_images())


@app.get("/api/stats")
def stats():
    """Ordredata til indkøb og prissætning: formater, ordrer og omsætning."""
    return jsonify(
        orders=query_one("SELECT COUNT(*) AS n FROM photo_order WHERE payment_status = 'BETALT'")["n"],
        revenue=query_one("SELECT COALESCE(SUM(total), 0) AS n FROM photo_order WHERE payment_status = 'BETALT'")["n"],
        dpi_warnings=query_one("SELECT COUNT(*) AS n FROM order_line WHERE dpi_warning = 1")["n"],
        images_stored=query_one("SELECT COUNT(*) AS n FROM image WHERE deleted_at IS NULL")["n"],
        popular=query_all("""SELECT p.label, p.surface, SUM(l.quantity) AS prints, SUM(l.line_price) AS revenue
                             FROM order_line l JOIN product p ON p.id = l.product_id
                             JOIN photo_order o ON o.id = l.order_id WHERE o.payment_status = 'BETALT'
                             GROUP BY p.label, p.surface ORDER BY prints DESC LIMIT 10"""),
    )


if __name__ == "__main__":
    init_db()
    run(app, PORT)
