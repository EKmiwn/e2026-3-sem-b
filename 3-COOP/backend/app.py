"""Coop – Grønne Besparelser: digitale gule mærker i Coop-appen. Flask API (logiklag).

Kravgrundlag: ../Kravspecifikation.md
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5203
"""
import os
from datetime import date, datetime

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5203))
app = create_app(__name__, "Coop Grønne Besparelser")

DISCOUNTS = [25, 40, 50, 70]      # knapperne på håndterminalen

LABEL_SQL = """SELECT l.*, p.name AS product_name, p.ean, p.category, s.name AS store_name, e.name AS employee_name,
                      l.quantity - l.quantity_sold AS quantity_left
               FROM yellow_label l JOIN product p ON p.id = l.product_id
               JOIN store s ON s.id = l.store_id JOIN employee e ON e.id = l.employee_id"""


def kr(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " kr."


# ---------------------------------------------------------------- F4: udsolgte og udløbne mærker forsvinder automatisk
def expire_labels():
    """Markerer mærker som udløbne, når sidste anvendelsesdato er passeret eller butikken er lukket på sidste dag.
    Kaldes før hver læsning, så feedet aldrig viser et mærke, der ikke længere findes på hylden."""
    today = date.today().isoformat()
    clock = datetime.now().strftime("%H:%M")
    with transaction() as db:
        db.execute("""UPDATE yellow_label SET status = 'UDLØBET', removed_at = ?
                      WHERE status = 'AKTIV' AND (expiry_date < ? OR (expiry_date = ? AND
                            ? >= (SELECT closing_time FROM store WHERE store.id = yellow_label.store_id)))""",
                   (now(), today, today, clock))


# ---------------------------------------------------------------- CRUD
register_crud(app, "stores", "store", fields=["name", "city", "closing_time"], required=["name", "city"])
register_crud(app, "products", "product", fields=["ean", "name", "category", "normal_price"],
              required=["ean", "name", "category", "normal_price"], order_by="name")
register_crud(app, "employees", "employee", fields=["name", "store_id"], required=["name", "store_id"])
register_crud(app, "customers", "customer", fields=["name", "email"], required=["name", "email"])


@app.get("/api/products/ean/<ean>")
def product_by_ean(ean):
    """Scanning på håndterminalen: slå varen op på stregkode (EAN)."""
    product = query_one("SELECT * FROM product WHERE ean = ?", (ean.strip(),))
    if product is None:
        raise ApiError(f"Stregkoden {ean} findes ikke i Coop One", 404)
    return jsonify(product=product, discounts=DISCOUNTS)


# ---------------------------------------------------------------- F3: medarbejderen opretter et gult mærke
@app.post("/api/labels")
def create_label():
    """Opret gult mærke: scan vare, vælg rabat (og antal). Kunder med samtykke i butikken får besked (F5)."""
    data = json_body()
    require(data, "employee_id", "ean", "discount_pct", "expiry_date")
    employee = get_or_404("employee", data["employee_id"], "Medarbejder")
    product = query_one("SELECT * FROM product WHERE ean = ?", (str(data["ean"]).strip(),))
    if product is None:
        raise ApiError(f"Stregkoden {data['ean']} findes ikke i Coop One", 404)
    discount = int(data["discount_pct"])
    if not 1 <= discount <= 90:
        raise ApiError("Rabatten skal være mellem 1 og 90 %")
    quantity = int(data.get("quantity") or 1)
    if quantity < 1:
        raise ApiError("Antal på hylden skal være mindst 1")
    try:
        expiry = date.fromisoformat(data["expiry_date"])
    except ValueError:
        raise ApiError("Sidste anvendelsesdato skal have formatet ÅÅÅÅ-MM-DD")
    if expiry < date.today():
        # Lovgivning (Template 17): varer med passeret sidste anvendelsesdato må ikke vises eller sælges
        raise ApiError("Sidste anvendelsesdato er passeret – varen må ikke sælges og kan ikke vises i appen")
    existing = query_one("""SELECT id FROM yellow_label WHERE store_id = ? AND product_id = ? AND expiry_date = ?
                            AND status = 'AKTIV'""", (employee["store_id"], product["id"], expiry.isoformat()))
    if existing:
        raise ApiError("Varen med denne dato har allerede et aktivt gult mærke", 409)

    new_price = round(product["normal_price"] * (100 - discount) / 100, 2)
    store = get_or_404("store", employee["store_id"], "Butik")
    with transaction() as db:
        label_id = db.execute(
            """INSERT INTO yellow_label (store_id, product_id, employee_id, old_price, discount_pct, new_price,
                                         expiry_date, quantity, creation_seconds, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (store["id"], product["id"], employee["id"], product["normal_price"], discount, new_price,
             expiry.isoformat(), quantity, data.get("creation_seconds"), now())).lastrowid
        message = f"{store['name']} har nedsat {product['name']} til {kr(new_price)} (før {kr(product['normal_price'])})"
        # F5: kun kunder, der har valgt butikken og givet samtykke til notifikationer
        customers = db.execute("""SELECT id FROM customer WHERE store_id = ? AND notifications_consent = 1""",
                               (store["id"],)).fetchall()
        for customer in customers:
            db.execute("INSERT INTO notification (customer_id, label_id, message, created_at) VALUES (?, ?, ?, ?)",
                       (customer["id"], label_id, message, now()))
    label = query_one(LABEL_SQL + " WHERE l.id = ?", (label_id,))
    return jsonify(label=label, notified_customers=len(customers)), 201


@app.get("/api/labels")
def list_labels():
    """Alle mærker i en butik – også udsolgte og udløbne (medarbejderens overblik)."""
    expire_labels()
    store_id = request.args.get("store_id", type=int)
    sql = LABEL_SQL + (" WHERE l.store_id = ?" if store_id else "") + " ORDER BY l.status = 'AKTIV' DESC, l.id DESC"
    return jsonify(query_all(sql, (store_id,) if store_id else ()))


@app.post("/api/labels/<int:label_id>/remove")
def remove_label(label_id):
    """Medarbejderen fjerner et mærke manuelt (fx hvis varen er kasseret)."""
    label = get_or_404("yellow_label", label_id, "Gult mærke")
    if label["status"] != "AKTIV":
        raise ApiError("Mærket er ikke aktivt", 409)
    with transaction() as db:
        db.execute("UPDATE yellow_label SET status = 'FJERNET', removed_at = ? WHERE id = ?", (now(), label_id))
    return jsonify(query_one(LABEL_SQL + " WHERE l.id = ?", (label_id,)))


# ---------------------------------------------------------------- Salg i kassen (Coop One) – F4
@app.post("/api/labels/<int:label_id>/sell")
def sell(label_id):
    """Simulerer et salg i kassen. Når sidste vare er solgt, forsvinder mærket fra appen med det samme."""
    expire_labels()
    label = query_one(LABEL_SQL + " WHERE l.id = ?", (label_id,))
    if label is None:
        raise ApiError(f"Gult mærke med id {label_id} findes ikke", 404)
    if label["status"] != "AKTIV":
        raise ApiError(f"Mærket er {label['status'].lower()} og kan ikke sælges", 409)
    quantity = int((request.get_json(silent=True) or {}).get("quantity") or 1)
    if not 1 <= quantity <= label["quantity_left"]:
        raise ApiError(f"Der er kun {label['quantity_left']} tilbage på hylden")
    with transaction() as db:
        db.execute("INSERT INTO sale (label_id, quantity, sold_at) VALUES (?, ?, ?)", (label_id, quantity, now()))
        db.execute("""UPDATE yellow_label SET quantity_sold = quantity_sold + ?,
                             status = CASE WHEN quantity_sold + ? >= quantity THEN 'UDSOLGT' ELSE status END,
                             removed_at = CASE WHEN quantity_sold + ? >= quantity THEN ? ELSE removed_at END
                      WHERE id = ?""", (quantity, quantity, quantity, now(), label_id))
    return jsonify(query_one(LABEL_SQL + " WHERE l.id = ?", (label_id,))), 201


# ---------------------------------------------------------------- Kunden i Coop-appen – F1, F2, F5
@app.get("/api/stores/<int:store_id>/feed")
def store_feed(store_id):
    """Feed med aktive gule mærker fra netop denne butik (F1) med vare, ny pris, førpris, dato og antal (F2)."""
    store = get_or_404("store", store_id, "Butik")
    expire_labels()
    labels = query_all(LABEL_SQL + """ WHERE l.store_id = ? AND l.status = 'AKTIV'
                                       ORDER BY l.expiry_date, l.discount_pct DESC""", (store_id,))
    fields = ["id", "product_name", "category", "new_price", "old_price", "discount_pct", "expiry_date",
              "quantity_left", "created_at"]
    return jsonify(store=store, updated_at=now(), labels=[{k: label[k] for k in fields} for label in labels],
                   saving_total=round(sum((l["old_price"] - l["new_price"]) * l["quantity_left"] for l in labels), 2))


@app.put("/api/customers/<int:customer_id>/preferences")
def preferences(customer_id):
    """Kunden vælger sin butik og slår notifikationer til/fra. Samtykket gemmes med tidspunkt (GDPR)."""
    customer = get_or_404("customer", customer_id, "Kunde")
    data = json_body()
    store_id = data.get("store_id", customer["store_id"])
    if store_id:
        get_or_404("store", store_id, "Butik")
    consent = 1 if data.get("notifications_consent", customer["notifications_consent"]) else 0
    consent_at = customer["consent_at"] if consent and customer["notifications_consent"] else (now() if consent else None)
    with transaction() as db:
        db.execute("UPDATE customer SET store_id = ?, notifications_consent = ?, consent_at = ? WHERE id = ?",
                   (store_id, consent, consent_at, customer_id))
    return jsonify(get_or_404("customer", customer_id))


@app.get("/api/customers/<int:customer_id>/notifications")
def notifications(customer_id):
    """Kundens beskeder om nye gule mærker."""
    get_or_404("customer", customer_id, "Kunde")
    return jsonify(query_all("""SELECT n.*, l.status AS label_status FROM notification n
                                JOIN yellow_label l ON l.id = n.label_id
                                WHERE n.customer_id = ? ORDER BY n.id DESC LIMIT 20""", (customer_id,)))


# ---------------------------------------------------------------- Nøgletal
@app.get("/api/stats")
def stats():
    """Nøgletal pr. butik: mærker, solgt før udløb, madspild og tid pr. oprettelse."""
    expire_labels()
    per_store = query_all("""
        SELECT s.id, s.name,
               COUNT(l.id) AS labels,
               SUM(l.status = 'AKTIV') AS active,
               SUM(l.status = 'UDSOLGT') AS sold_out,
               SUM(l.status = 'UDLØBET') AS expired,
               COALESCE(SUM(l.quantity_sold), 0) AS units_sold,
               COALESCE(SUM(CASE WHEN l.status = 'UDLØBET' THEN l.quantity - l.quantity_sold END), 0) AS units_wasted,
               ROUND(AVG(l.creation_seconds)) AS avg_creation_seconds,
               (SELECT COUNT(*) FROM customer c WHERE c.store_id = s.id AND c.notifications_consent = 1) AS subscribers
        FROM store s LEFT JOIN yellow_label l ON l.store_id = s.id
        GROUP BY s.id ORDER BY s.name""")
    totals = query_one("""SELECT COALESCE(SUM(quantity_sold), 0) AS sold, COALESCE(SUM(quantity), 0) AS units,
                                 ROUND(AVG(creation_seconds)) AS avg_seconds,
                                 SUM(creation_seconds <= 20) AS within_20s, COUNT(creation_seconds) AS timed
                          FROM yellow_label""")
    return jsonify(per_store=per_store, units_sold=totals["sold"],
                   sell_through_pct=round(100 * totals["sold"] / totals["units"]) if totals["units"] else 0,
                   avg_creation_seconds=totals["avg_seconds"],
                   within_20s_pct=round(100 * (totals["within_20s"] or 0) / totals["timed"]) if totals["timed"] else None,
                   notifications=query_one("SELECT COUNT(*) AS n FROM notification")["n"])


if __name__ == "__main__":
    init_db()
    run(app, PORT)
