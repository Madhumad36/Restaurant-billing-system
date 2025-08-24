import sqlite3
import os
import csv
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'db', 'restaurant.db')

def get_connection():
    # Ensure the db directory exists (important on fresh deploys)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)
def setup_database():
    conn = get_connection()
    c = conn.cursor()
    # MENU TABLE
    c.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        price REAL,
        gst REAL
    )''')
    # ORDERS TABLE with customer info columns
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        mode TEXT,
        payment_method TEXT,
        total REAL,
        discount_percent REAL,
        coupon_code TEXT,
        gst_amount REAL,
        customer_name TEXT,
        customer_phone TEXT
    )''')
    # ORDER_ITEMS TABLE
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        order_id INTEGER,
        menu_id INTEGER,
        name TEXT,
        quantity INTEGER,
        price REAL,
        gst REAL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    )''')
    conn.commit()
    conn.close()

def import_menu_from_csv(menu_csv_path):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM menu")
    if c.fetchone()[0] > 0:
        conn.close()
        return
    with open(menu_csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                price = float(row['price'])
                gst = float(row['gst'])
            except (ValueError, TypeError):
                continue
            c.execute('INSERT INTO menu (name, category, price, gst) VALUES (?, ?, ?, ?)',
                      (row['name'], row['category'], price, gst))
    conn.commit()
    conn.close()

def fetch_menu():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, category, price, gst FROM menu")
    rows = c.fetchall()
    menu = []
    for row in rows:
        menu.append({'id': row[0],'name': row[1], 'category': row[2], 'price': row[3], 'gst': row[4]})
    conn.close()
    return menu

def save_order(mode, payment_method, items, total, discount_percent=0, coupon_code=None, gst_amount=0, customer_name=None, customer_phone=None):
    from datetime import datetime
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO orders (timestamp, mode, payment_method, total, discount_percent, coupon_code, gst_amount, customer_name, customer_phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (datetime.now().isoformat(), mode, payment_method, total, discount_percent, coupon_code, gst_amount, customer_name, customer_phone))
    order_id = c.lastrowid
    for it in items:
        c.execute('INSERT INTO order_items (order_id, menu_id, name, quantity, price, gst) VALUES (?, ?, ?, ?, ?, ?)',
            (order_id, it['menu_id'], it['name'], it['qty'], it['price'], it['gst']))
    conn.commit()
    conn.close()
    return order_id

def fetch_orders():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders")
    rows = c.fetchall()
    conn.close()
    return rows
