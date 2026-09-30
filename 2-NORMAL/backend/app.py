"""NORMAL – se om en vare er på lager i en bestemt butik. Flask API (logiklag).

Kravgrundlag: ../kravspec.md
Kør:  pip install -r requirements.txt  &&  python app.py  →  http://localhost:5202
"""
import os

from flask import jsonify, request

from core import ApiError, create_app, get_or_404, json_body, now, register_crud, require, run
from database import init_db, query_all, query_one, transaction

PORT = int(os.environ.get("PORT", 5202))
app = create_app(__name__, "NORMAL Lagerstatus")

STATUS_TEXT = {
    "PÅ_LAGER": "På lager",
    "FÅ_TILBAGE": "Få tilbage – kom i god tid",
    "UDSOLGT": "Ikke på lager i denne butik",
}


def low_stock_limit():
    row = query_one("SELECT value FROM setting WHERE key = 'low_stock_limit'")
    return row["value"] if row else 3


def stock_status(quantity):
    if not quantity:
        return "UDSOLGT"
    return "FÅ_TILBAGE" if quantity <= low_stock_limit() else "PÅ_LAGER"


PRODUCT_SQL = """SELECT p.*, c.name AS category FROM product p JOIN category c ON c.id = p.category_id"""


# ---------------------------------------------------------------- CRUD
register_crud(app, "settings", "setting", fields=["key", "value", "description"], required=["key", "value"],
              update_fields=["value", "description"])
register_crud(app, "stores", "store", fields=["name", "city", "address", "opening_hours", "employees"],
              required=["name", "city", "address"], order_by="city, name")
register_crud(app, "categories", "category", fields=["name"], required=["name"], order_by="name")
register_crud(app, "products", "product", fields=["sku", "name", "brand", "category_id", "price", "keywords"],
              required=["sku", "name", "brand", "category_id", "price"], order_by="name")


# ---------------------------------------------------------------- Kunden: søg produkt
@app.get("/api/search")
def search():
    """Søg efter produkt på navn, mærke, kategori, varenummer eller søgeord. Søgningen logges til nøgletal."""
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        raise ApiError("Skriv mindst 2 tegn for at søge")
    like = f"%{q.lower()}%"
    rows = query_all(PRODUCT_SQL + """ WHERE lower(p.name) LIKE ? OR lower(p.brand) LIKE ? OR lower(c.name) LIKE ?
                                       OR p.sku LIKE ? OR lower(p.keywords) LIKE ? ORDER BY p.name""",
                     (like, like, like, like, like))
    with transaction() as db:
        db.execute("INSERT INTO search_log (query, result_count, created_at) VALUES (?, ?, ?)",
                   (q.lower(), len(rows), now()))
    return jsonify(query=q, count=len(rows), products=rows)


# ---------------------------------------------------------------- Kunden: vælg butik og se lagerstatus
@app.get("/api/products/<int:product_id>/availability")
def availability(product_id):
    """Lagerstatus for et produkt i den valgte butik. Er det udsolgt, foreslås andre butikker med varen på lager."""
    product = query_one(PRODUCT_SQL + " WHERE p.id = ?", (product_id,))
    if product is None:
        raise ApiError(f"Produkt med id {product_id} findes ikke", 404)
    store_id = request.args.get("store_id", type=int)
    if not store_id:
        raise ApiError("Vælg en butik")
    store = get_or_404("store", store_id, "Butik")
    row = query_one("SELECT quantity, updated_at FROM stock WHERE store_id = ? AND product_id = ?", (store_id, product_id))
    quantity = row["quantity"] if row else 0
    status = stock_status(quantity)

    alternatives = []
    if status == "UDSOLGT":
        others = query_all("""SELECT s.*, st.quantity FROM stock st JOIN store s ON s.id = st.store_id
                              WHERE st.product_id = ? AND st.store_id != ? AND st.quantity > 0""",
                           (product_id, store_id))
        # Butikker i samme by først, derefter flest på lager
        others.sort(key=lambda s: (s["city"] != store["city"], -s["quantity"]))
        alternatives = [{"store_id": s["id"], "name": s["name"], "city": s["city"], "address": s["address"],
                         "status": stock_status(s["quantity"]), "status_text": STATUS_TEXT[stock_status(s["quantity"])],
                         "same_city": s["city"] == store["city"]} for s in others]

    with transaction() as db:
        db.execute("INSERT INTO lookup_log (product_id, store_id, status, created_at) VALUES (?, ?, ?, ?)",
                   (product_id, store_id, status, now()))
    # Kunden ser en status – ikke det præcise antal, der kan ændre sig inden butiksbesøget
    return jsonify(product=product, store=store, status=status, status_text=STATUS_TEXT[status],
                   updated_at=row["updated_at"] if row else None,
                   message=(f"{product['name']} er på lager i {store['name']}." if status == "PÅ_LAGER" else
                            f"Der er kun få tilbage af {product['name']} i {store['name']}." if status == "FÅ_TILBAGE" else
                            f"{product['name']} er ikke på lager i {store['name']}. Vælg en anden butik."),
                   alternatives=alternatives)


# ---------------------------------------------------------------- Medarbejdere: lagerstatus i egen butik
@app.get("/api/stores/<int:store_id>/stock")
def store_stock(store_id):
    """Butikkens lager med status pr. produkt (til medarbejdere)."""
    get_or_404("store", store_id, "Butik")
    rows = query_all("""SELECT p.id AS product_id, p.sku, p.name, p.brand, c.name AS category,
                               COALESCE(st.quantity, 0) AS quantity, st.updated_at
                        FROM product p JOIN category c ON c.id = p.category_id
                        LEFT JOIN stock st ON st.product_id = p.id AND st.store_id = ?
                        ORDER BY c.name, p.name""", (store_id,))
    return jsonify([{**r, "status": stock_status(r["quantity"])} for r in rows])


@app.put("/api/stores/<int:store_id>/stock/<int:product_id>")
def update_stock(store_id, product_id):
    """Medarbejderen retter antal på lager (i virkeligheden fra NORMALs lagersystem)."""
    get_or_404("store", store_id, "Butik")
    get_or_404("product", product_id, "Produkt")
    data = json_body()
    require(data, "quantity")
    quantity = int(data["quantity"])
    if quantity < 0:
        raise ApiError("Antal kan ikke være negativt")
    with transaction() as db:
        db.execute("""INSERT INTO stock (store_id, product_id, quantity, updated_at) VALUES (?, ?, ?, ?)
                      ON CONFLICT (store_id, product_id) DO UPDATE SET quantity = excluded.quantity,
                                                                       updated_at = excluded.updated_at""",
                   (store_id, product_id, quantity, now()))
    return jsonify(store_id=store_id, product_id=product_id, quantity=quantity, status=stock_status(quantity))


# ---------------------------------------------------------------- Nøgletal
@app.get("/api/stats")
def stats():
    """Nøgletal: søgninger, opslag, forgæves opslag (udsolgt) og efterspurgte produkter."""
    lookups = query_one("""SELECT COUNT(*) AS lookups, SUM(status = 'UDSOLGT') AS sold_out_lookups
                           FROM lookup_log""")
    return jsonify(
        searches=query_one("SELECT COUNT(*) AS n FROM search_log")["n"],
        searches_without_result=query_one("SELECT COUNT(*) AS n FROM search_log WHERE result_count = 0")["n"],
        lookups=lookups["lookups"], sold_out_lookups=lookups["sold_out_lookups"] or 0,
        stores=query_one("SELECT COUNT(*) AS n FROM store")["n"],
        employees=query_one("SELECT COALESCE(SUM(employees), 0) AS n FROM store")["n"],
        top_searches=query_all("""SELECT query, COUNT(*) AS count, MAX(result_count) AS results FROM search_log
                                  GROUP BY query ORDER BY count DESC, query LIMIT 10"""),
        top_products=query_all("""SELECT p.name, COUNT(*) AS lookups, SUM(l.status = 'UDSOLGT') AS sold_out
                                  FROM lookup_log l JOIN product p ON p.id = l.product_id
                                  GROUP BY p.id ORDER BY lookups DESC LIMIT 10"""),
        per_store=query_all("""SELECT s.name, s.city, s.employees,
                                      (SELECT COUNT(*) FROM stock st WHERE st.store_id = s.id AND st.quantity = 0) AS sold_out_products,
                                      (SELECT COUNT(*) FROM lookup_log l WHERE l.store_id = s.id) AS lookups
                               FROM store s ORDER BY s.city, s.name"""),
    )


if __name__ == "__main__":
    init_db()
    run(app, PORT)
