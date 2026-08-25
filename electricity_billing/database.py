"""SQLite database layer for persisting electricity bills."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
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
    connected_load_kw REAL  NOT NULL DEFAULT 1.0,
    energy_charge   REAL    NOT NULL,
    fac_charge      REAL    NOT NULL DEFAULT 0.0,
    tod_fixed_charge REAL   NOT NULL DEFAULT 0.0,
    municipal_surcharge REAL NOT NULL DEFAULT 0.0,
    fixed_charge    REAL    NOT NULL,
    security_deposit_arrears REAL NOT NULL DEFAULT 0.0,
    delayed_payment_charge REAL NOT NULL DEFAULT 0.0,
    meter_rent      REAL    NOT NULL DEFAULT 0.0,
    electricity_duty_percent REAL NOT NULL DEFAULT 0.0,
    electricity_duty REAL   NOT NULL DEFAULT 0.0,
    gst_percent     REAL    NOT NULL,
    gst_amount      REAL    NOT NULL,
    subtotal        REAL    NOT NULL,
    total           REAL    NOT NULL,
    txt_path        TEXT    NOT NULL DEFAULT '',
    pdf_path        TEXT    NOT NULL DEFAULT '',
    whatsapp_sent   INTEGER NOT NULL DEFAULT 0
);
"""

_NEW_COLUMNS: list[tuple[str, str]] = [
    ("connected_load_kw", "REAL NOT NULL DEFAULT 1.0"),
    ("fac_charge", "REAL NOT NULL DEFAULT 0.0"),
    ("tod_fixed_charge", "REAL NOT NULL DEFAULT 0.0"),
    ("municipal_surcharge", "REAL NOT NULL DEFAULT 0.0"),
    ("security_deposit_arrears", "REAL NOT NULL DEFAULT 0.0"),
    ("delayed_payment_charge", "REAL NOT NULL DEFAULT 0.0"),
]


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


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(bills)").fetchall()
    }
    for col, col_type in _NEW_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE bills ADD COLUMN {col} {col_type}")


def init_db() -> None:
    """Create tables if they don't exist and apply lightweight migrations."""
    with _connect() as conn:
        conn.execute(_CREATE_BILLS_TABLE)
        _migrate(conn)


def insert_bill(
    bill_no: str,
    created_at: str,
    due_date: str,
    customer_name: str,
    phone: str,
    units_consumed: int,
    energy_charge: float,
    fixed_charge: float,
    gst_percent: float,
    gst_amount: float,
    subtotal: float,
    total: float,
    connected_load_kw: float = 1.0,
    fac_charge: float = 0.0,
    tod_fixed_charge: float = 0.0,
    municipal_surcharge: float = 0.0,
    security_deposit_arrears: float = 0.0,
    delayed_payment_charge: float = 0.0,
    meter_rent: float = 0.0,
    electricity_duty_percent: float = 0.0,
    electricity_duty: float = 0.0,
    txt_path: str = "",
    pdf_path: str = "",
) -> int:
    """Insert a new bill record and return the row id."""
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO bills (
                bill_no, created_at, due_date, customer_name, phone,
                units_consumed, connected_load_kw,
                energy_charge, fac_charge, tod_fixed_charge, municipal_surcharge,
                fixed_charge, security_deposit_arrears, delayed_payment_charge,
                meter_rent, electricity_duty_percent, electricity_duty,
                gst_percent, gst_amount, subtotal, total,
                txt_path, pdf_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bill_no, created_at, due_date, customer_name, phone,
                units_consumed, connected_load_kw,
                energy_charge, fac_charge, tod_fixed_charge, municipal_surcharge,
                fixed_charge, security_deposit_arrears, delayed_payment_charge,
                meter_rent, electricity_duty_percent, electricity_duty,
                gst_percent, gst_amount, subtotal, total,
                txt_path, pdf_path,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def next_bill_seq_for_date(date_yyyymmdd: str) -> int:
    """Return the next 4-digit sequence for bill numbers on a given date.

    Looks at existing ``EB-YYYYMMDD-NNNN`` rows so counters survive restarts.
    """
    prefix = f"EB-{date_yyyymmdd}-"
    with _connect() as conn:
        rows = conn.execute(
            "SELECT bill_no FROM bills WHERE bill_no LIKE ?",
            (f"{prefix}%",),
        ).fetchall()
    max_seq = 0
    for row in rows:
        bill_no = row["bill_no"]
        try:
            seq = int(bill_no.rsplit("-", 1)[-1])
        except ValueError:
            continue
        if seq > max_seq:
            max_seq = seq
    return max_seq + 1


def suggest_next_bill_number() -> str:
    """Suggest the next unique bill number for today, based on DB contents."""
    from datetime import datetime

    date_part = datetime.now().strftime("%Y%m%d")
    seq = next_bill_seq_for_date(date_part)
    return f"EB-{date_part}-{seq:04d}"


def bill_number_exists(bill_no: str) -> bool:
    """Return True if ``bill_no`` is already stored in the database."""
    return get_bill_by_no(bill_no.strip()) is not None


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


def search_bills(
    customer_name: str = "",
    phone: str = "",
    bill_no: str = "",
) -> list[dict]:
    """Search bills by customer name, phone, or bill number (partial match)."""
    clauses: list[str] = []
    params: list[str] = []
    if customer_name:
        clauses.append("customer_name LIKE ?")
        params.append(f"%{customer_name}%")
    if phone:
        clauses.append("phone LIKE ?")
        params.append(f"%{phone}%")
    if bill_no:
        clauses.append("bill_no LIKE ?")
        params.append(f"%{bill_no}%")
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
