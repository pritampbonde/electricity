"""SQLite database layer for persisting electricity bills."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from billing_config import BILLS_DIR

DB_PATH = os.path.join(BILLS_DIR, "electricity_billing.db")

_CREATE_BILLS_TABLE = """
CREATE TABLE IF NOT EXISTS bills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_no         TEXT    NOT NULL UNIQUE,
    created_at      TEXT    NOT NULL,
    due_date        TEXT    NOT NULL,
    customer_name   TEXT    NOT NULL,
    phone           TEXT    NOT NULL,
    units_consumed  INTEGER NOT NULL,
    energy_charge   REAL    NOT NULL,
    fixed_charge    REAL    NOT NULL,
    meter_rent      REAL    NOT NULL,
    electricity_duty_percent REAL NOT NULL,
    electricity_duty REAL   NOT NULL,
    gst_percent     REAL    NOT NULL,
    gst_amount      REAL    NOT NULL,
    subtotal        REAL    NOT NULL,
    total           REAL    NOT NULL,
    txt_path        TEXT    NOT NULL DEFAULT '',
    pdf_path        TEXT    NOT NULL DEFAULT '',
    whatsapp_sent   INTEGER NOT NULL DEFAULT 0
);
"""


@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    os.makedirs(BILLS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.execute(_CREATE_BILLS_TABLE)


def insert_bill(
    bill_no: str,
    created_at: str,
    due_date: str,
    customer_name: str,
    phone: str,
    units_consumed: int,
    energy_charge: float,
    fixed_charge: float,
    meter_rent: float,
    electricity_duty_percent: float,
    electricity_duty: float,
    gst_percent: float,
    gst_amount: float,
    subtotal: float,
    total: float,
    txt_path: str = "",
    pdf_path: str = "",
) -> int:
    """Insert a new bill record and return the row id."""
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO bills (
                bill_no, created_at, due_date, customer_name, phone,
                units_consumed, energy_charge, fixed_charge, meter_rent,
                electricity_duty_percent, electricity_duty,
                gst_percent, gst_amount, subtotal, total,
                txt_path, pdf_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bill_no, created_at, due_date, customer_name, phone,
                units_consumed, energy_charge, fixed_charge, meter_rent,
                electricity_duty_percent, electricity_duty,
                gst_percent, gst_amount, subtotal, total,
                txt_path, pdf_path,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def update_pdf_path(bill_no: str, pdf_path: str) -> None:
    """Set the PDF file path for an existing bill."""
    with _connect() as conn:
        conn.execute(
            "UPDATE bills SET pdf_path = ? WHERE bill_no = ?",
            (pdf_path, bill_no),
        )


def mark_whatsapp_sent(bill_no: str) -> None:
    """Flag a bill as sent via WhatsApp."""
    with _connect() as conn:
        conn.execute(
            "UPDATE bills SET whatsapp_sent = 1 WHERE bill_no = ?",
            (bill_no,),
        )


def get_all_bills() -> list[dict]:
    """Return all bills ordered by newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM bills ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_bill_by_no(bill_no: str) -> dict | None:
    """Return a single bill by bill number, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM bills WHERE bill_no = ?", (bill_no,)
        ).fetchone()
        return dict(row) if row else None


def search_bills(customer_name: str = "", phone: str = "") -> list[dict]:
    """Search bills by customer name or phone (partial match)."""
    clauses: list[str] = []
    params: list[str] = []
    if customer_name:
        clauses.append("customer_name LIKE ?")
        params.append(f"%{customer_name}%")
    if phone:
        clauses.append("phone LIKE ?")
        params.append(f"%{phone}%")
    where = " AND ".join(clauses) if clauses else "1=1"
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM bills WHERE {where} ORDER BY id DESC",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_bill_stats() -> dict:
    """Return summary statistics."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*)          AS total_bills,
                COALESCE(SUM(total), 0)           AS total_revenue,
                COALESCE(AVG(total), 0)           AS avg_bill,
                COALESCE(SUM(units_consumed), 0)  AS total_units,
                COALESCE(MAX(total), 0)           AS highest_bill,
                COALESCE(MIN(total), 0)           AS lowest_bill
            FROM bills
            """
        ).fetchone()
        return dict(row)  # type: ignore[arg-type]


# Auto-initialise on import
init_db()
