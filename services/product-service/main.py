import os, sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB = os.getenv("DB_PATH", "products.db")

SEED = [
    ("Bananas", "Fruit", 0.59, "per lb", "🍌", 120), ("Red apples", "Fruit", 1.29, "per lb", "🍎", 90),
    ("Avocados", "Fruit", 1.49, "each", "🥑", 60), ("Tomatoes", "Vegetables", 1.99, "per lb", "🍅", 75),
    ("Carrots", "Vegetables", 0.99, "per lb", "🥕", 100), ("Broccoli", "Vegetables", 1.79, "per head", "🥦", 40),
    ("Whole milk", "Dairy", 3.49, "1 gal", "🥛", 50), ("Cheddar", "Dairy", 4.29, "8 oz", "🧀", 35),
    ("Free-range eggs", "Dairy", 3.99, "dozen", "🥚", 80), ("Sourdough loaf", "Bakery", 4.50, "each", "🍞", 25),
    ("Basmati rice", "Pantry", 6.99, "2 lb", "🍚", 70), ("Olive oil", "Pantry", 9.49, "500 ml", "🫒", 30),
]

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

@asynccontextmanager
async def lifespan(_app):
    init()
    yield

def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, category TEXT, price REAL, unit TEXT, emoji TEXT, stock INTEGER)""")
        if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            c.executemany("INSERT INTO products(name,category,price,unit,emoji,stock) VALUES(?,?,?,?,?,?)", SEED)

app = FastAPI(title="Product Service", lifespan=lifespan)

class ProductIn(BaseModel):
    name: str; category: str; price: float = Field(gt=0); unit: str = "each"; emoji: str = "🛒"; stock: int = Field(ge=0, default=0)

@app.get("/health")
def health():
    # Demo hook for the rollback exercise: the pipeline sets SIMULATE_UNHEALTHY=true
    # when the "SIMULATE_BAD_RELEASE" build parameter is ticked. Off by default.
    if os.getenv("SIMULATE_UNHEALTHY", "false").lower() == "true":
        raise HTTPException(503, "Simulated bad release")
    return {"status": "ok", "env": os.getenv("APP_ENV", "dev")}

@app.get("/products")
def list_products(category: str | None = None):
    q, a = "SELECT * FROM products", ()
    if category: q, a = q + " WHERE category=?", (category,)
    with conn() as c: return [dict(r) for r in c.execute(q, a)]

@app.get("/products/{pid}")
def get_product(pid: int):
    with conn() as c: r = c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not r: raise HTTPException(404, "Product not found")
    return dict(r)

@app.post("/products", status_code=201)
def add_product(p: ProductIn):
    with conn() as c:
        cur = c.execute("INSERT INTO products(name,category,price,unit,emoji,stock) VALUES(?,?,?,?,?,?)",
                        (p.name, p.category, p.price, p.unit, p.emoji, p.stock))
    return {**p.model_dump(), "id": cur.lastrowid}

@app.post("/products/{pid}/reserve")
def reserve(pid: int, qty: int):
    with conn() as c:
        r = c.execute("SELECT stock FROM products WHERE id=?", (pid,)).fetchone()
        if not r: raise HTTPException(404, "Product not found")
        if r["stock"] < qty: raise HTTPException(409, "Not enough stock")
        c.execute("UPDATE products SET stock=stock-? WHERE id=?", (qty, pid))
    return {"reserved": qty}
