import os, json, sqlite3, httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB = os.getenv("DB_PATH", "orders.db")
PRODUCT_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000")

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

@asynccontextmanager
async def lifespan(_app):
    init()
    yield

def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT, address TEXT, items TEXT, total REAL, status TEXT DEFAULT 'placed')""")

app = FastAPI(title="Order Service", lifespan=lifespan)

class Line(BaseModel):
    product_id: int; qty: int = Field(gt=0)

class OrderIn(BaseModel):
    customer: str = Field(min_length=1); address: str = Field(min_length=1); items: list[Line] = Field(min_length=1)

@app.get("/health")
def health(): return {"status": "ok", "env": os.getenv("APP_ENV", "dev")}

@app.post("/orders", status_code=201)
def place_order(o: OrderIn):
    lines, total = [], 0.0
    with httpx.Client(base_url=PRODUCT_URL, timeout=5) as http:
        for it in o.items:
            r = http.get(f"/products/{it.product_id}")
            if r.status_code != 200: raise HTTPException(400, f"Unknown product {it.product_id}")
            p = r.json()
            if http.post(f"/products/{it.product_id}/reserve", params={"qty": it.qty}).status_code != 200:
                raise HTTPException(409, f"Not enough stock for {p['name']}")
            sub = round(p["price"] * it.qty, 2); total += sub
            lines.append({"product_id": p["id"], "name": p["name"], "qty": it.qty, "subtotal": sub})
    total = round(total, 2)
    with conn() as c:
        cur = c.execute("INSERT INTO orders(customer,address,items,total) VALUES(?,?,?,?)",
                        (o.customer, o.address, json.dumps(lines), total))
    return {"id": cur.lastrowid, "status": "placed", "total": total, "items": lines}

@app.get("/orders")
def list_orders():
    with conn() as c:
        return [{**dict(r), "items": json.loads(r["items"])} for r in c.execute("SELECT * FROM orders ORDER BY id DESC")]

@app.get("/orders/{oid}")
def get_order(oid: int):
    with conn() as c: r = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not r: raise HTTPException(404, "Order not found")
    return {**dict(r), "items": json.loads(r["items"])}
