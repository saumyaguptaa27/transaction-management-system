import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "transaction_db")
CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": DB_NAME,
}


class DatabaseError(Exception):
    """Raised for any database problem, with a user-friendly message."""


@contextmanager
def get_conn(with_db=True):
    cfg = dict(CONFIG)
    if not with_db:
        cfg.pop("database")
    conn = None
    try:
        conn = mysql.connector.connect(**cfg)
        yield conn
    except Error as e:
        if conn is not None and conn.is_connected():
            conn.rollback()
        raise DatabaseError(str(e)) from e
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


def init_db():
    with get_conn(with_db=False) as conn:
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
        conn.commit()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                txn_date DATE NOT NULL,
                description VARCHAR(255) NOT NULL,
                category VARCHAR(50) NOT NULL,
                txn_type ENUM('Income','Expense') NOT NULL,
                amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_date (txn_date),
                INDEX idx_category (category)
            )""")
        conn.commit()


def _run(query, params=(), fetch=False, many=False):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
        return cur.lastrowid if not many else cur.rowcount


# ---------- CREATE ----------
def add_transaction(t):
    q = """INSERT INTO transactions (txn_date, description, category, txn_type, amount)
           VALUES (%s, %s, %s, %s, %s)"""
    return _run(q, (t["txn_date"], t["description"], t["category"],
                    t["txn_type"], t["amount"]))


# ---------- READ / SEARCH / FILTER ----------
def get_transactions(search=None, txn_type=None, category=None,
                     date_from=None, date_to=None,
                     min_amount=None, max_amount=None, order="DESC"):
    where, params = [], []
    if search:
        where.append("(description LIKE %s OR category LIKE %s)")
        params += [f"%{search}%", f"%{search}%"]
    if txn_type and txn_type != "All":
        where.append("txn_type = %s"); params.append(txn_type)
    if category and category != "All":
        where.append("category = %s"); params.append(category)
    if date_from:
        where.append("txn_date >= %s"); params.append(date_from)
    if date_to:
        where.append("txn_date <= %s"); params.append(date_to)
    if min_amount:
        where.append("amount >= %s"); params.append(min_amount)
    if max_amount:
        where.append("amount <= %s"); params.append(max_amount)

    order = "ASC" if order == "ASC" else "DESC"  # never interpolate user input
    q = "SELECT id, txn_date, description, category, txn_type, amount FROM transactions"
    if where:
        q += " WHERE " + " AND ".join(where)
    q += f" ORDER BY txn_date {order}, id {order}"
    return _run(q, tuple(params), fetch=True)


def get_transaction(txn_id):
    rows = _run("SELECT * FROM transactions WHERE id = %s", (txn_id,), fetch=True)
    return rows[0] if rows else None


# ---------- UPDATE ----------
def update_transaction(txn_id, t):
    q = """UPDATE transactions SET txn_date=%s, description=%s, category=%s,
           txn_type=%s, amount=%s WHERE id=%s"""
    return _run(q, (t["txn_date"], t["description"], t["category"],
                    t["txn_type"], t["amount"], txn_id), many=True)


# ---------- DELETE ----------
def delete_transaction(txn_id):
    return _run("DELETE FROM transactions WHERE id = %s", (txn_id,), many=True)


# ---------- SUMMARY ----------
def get_summary():
    q = """SELECT
             COALESCE(SUM(CASE WHEN txn_type='Income' THEN amount END),0) AS income,
             COALESCE(SUM(CASE WHEN txn_type='Expense' THEN amount END),0) AS expense,
             COUNT(*) AS total
           FROM transactions"""
    return _run(q, fetch=True)[0]


def get_category_totals():
    q = """SELECT category, SUM(amount) AS total FROM transactions
           WHERE txn_type='Expense' GROUP BY category ORDER BY total DESC"""
    return _run(q, fetch=True)
