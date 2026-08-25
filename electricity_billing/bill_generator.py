"""Generate electricity bill as a text file and a PDF invoice."""

from __future__ import annotations

import os
import re
from datetime import datetime

from fpdf import FPDF

from bill_calculator import BillResult
from billing_config import BILLS_DIR, TARIFF_NAME, TARIFF_ORDER
from database import (
    bill_number_exists,
    insert_bill,
    suggest_next_bill_number,
    update_pdf_path,
)


def _next_bill_number() -> str:
    """Allocate a unique bill number based on today's date + DB sequence."""
    return suggest_next_bill_number()


def _normalize_bill_no(bill_no: str) -> str:
    return " ".join(bill_no.strip().split())


def _safe_filename(bill_no: str) -> str:
    """Filesystem-safe name while keeping the display bill number unchanged."""
    cleaned = re.sub(r"[^\w.\-]+", "_", bill_no.strip())
    return cleaned or "bill"


def resolve_bill_number(bill: BillResult, bill_no: str | None = None) -> str:
    """Prefer explicit arg, then ``bill.bill_no``, else allocate from DB."""
    for candidate in (bill_no, getattr(bill, "bill_no", "")):
        if candidate and str(candidate).strip():
            return _normalize_bill_no(str(candidate))
    return _next_bill_number()


def _ensure_bills_dir() -> str:
    os.makedirs(BILLS_DIR, exist_ok=True)
    return BILLS_DIR


def _bill_text(bill: BillResult, bill_no: str, timestamp: str) -> str:
    """Return a human-readable plain-text version of the bill."""
    sep = "=" * 62
    lines = [
        sep,
        f"       ELECTRICITY BILL / INVOICE ({TARIFF_NAME})",
        sep,
        f"  Bill No         : {bill_no}",
        f"  Bill Period     : {bill.bill_period}",
        f"  Date            : {timestamp}",
        f"  Prompt Due Date : {bill.prompt_due_date}",
        f"  Late Due Date   : {bill.due_date}",
        f"  Customer        : {bill.customer_name}",
        f"  Phone           : {bill.phone}",
        f"  Conn. Load      : {bill.connected_load_kw:g} kW",
        sep,
        f"  Units Consumed  : {bill.units_consumed} kWh",
        "",
        "  --- Energy + FAC (per slab) ---",
    ]
    for s in bill.slab_details:
        lines.append(f"    {s.slab_label}")
        lines.append(
            f"      {s.units} units  Energy Rs.{s.energy_amount:.2f}  "
            f"+ FAC Rs.{s.fac_amount:.2f}  =  Rs.{s.amount:.2f}"
        )
    lines += [
        "",
        "  --- Direct / flat charges ---",
        f"  Fixed Charge (Res.)        : Rs.{bill.tod_fixed_charge:.2f}",
        f"  Municipal Surcharge        : Rs.{bill.municipal_surcharge:.2f}",
        f"  Total Fixed Charge         : Rs.{bill.fixed_charge:.2f}",
        f"  Energy Charge              : Rs.{bill.energy_charge:.2f}",
        f"  FAC Charge                 : Rs.{bill.fac_charge:.2f}",
        f"  Wheeling @ Rs.{bill.wheeling_rate:.2f}/U : Rs.{bill.wheeling_charge:.2f}",
        f"  Duty Base                  : Rs.{bill.duty_base:.2f}",
        f"  Elec. Duty ({bill.electricity_duty_percent:.0f}%)         : Rs.{bill.electricity_duty:.2f}",
        "",
        "  --- Bill roll-up ---",
        f"  Current Bill               : Rs.{bill.current_bill:.2f}",
        f"  Net Adjustment             : Rs.{bill.net_adjustment:.2f}",
        f"  Net Amount                 : Rs.{bill.net_amount:.2f}",
        f"  Rounded Bill (payable)     : Rs.{bill.total:.2f}",
        "",
        "  --- Payable on due dates ---",
        f"  Prompt Discount ({bill.prompt_payment_discount:.2f})",
        f"  Pay by {bill.prompt_due_date} (prompt) : Rs.{bill.prompt_payable:.2f}",
        f"  Pay by {bill.due_date} (normal)  : Rs.{bill.total:.2f}",
        f"  After {bill.due_date}            : Rs.{bill.after_due_payable:.2f}",
    ]
    lines += [
        "",
        "  --- Footnote / separate items ---",
        f"  SD Held                    : Rs.{bill.security_deposit_held:.2f}",
        f"  SD Arrears                 : Rs.{bill.security_deposit_arrears:.2f}",
        f"  Interest on SD             : Rs.{bill.security_deposit_interest:.2f}",
        f"  Digital Pay Discount       : Rs.{bill.digital_payment_discount:.2f}",
    ]
    if bill.include_security_deposit_in_total and bill.security_deposit_arrears > 0:
        lines.append("  (SD arrears INCLUDED in current bill total)")
    else:
        lines.append("  (SD arrears NOT included in rounded bill — footnote only)")

    lines += [
        sep,
        f"  TOTAL AMOUNT PAYABLE      : Rs.{bill.total:.2f}",
        sep,
        "",
        f"  Tariff: {TARIFF_NAME}" + (f" ({TARIFF_ORDER})" if TARIFF_ORDER else ""),
        f"  Please pay before {bill.due_date} to avoid late fees.",
        "",
    ]
    return "\n".join(lines)


def _persist_bill(
    bill: BillResult,
    bill_no: str,
    timestamp: str,
    filepath: str,
) -> None:
    insert_bill(
        bill_no=bill_no,
        created_at=timestamp,
        due_date=bill.due_date,
        prompt_due_date=bill.prompt_due_date,
        bill_month=bill.bill_month,
        bill_year=bill.bill_year,
        customer_name=bill.customer_name,
        phone=bill.phone,
        units_consumed=bill.units_consumed,
        connected_load_kw=bill.connected_load_kw,
        energy_charge=bill.energy_charge,
        fac_charge=bill.fac_charge,
        wheeling_charge=bill.wheeling_charge,
        tod_fixed_charge=bill.tod_fixed_charge,
        municipal_surcharge=bill.municipal_surcharge,
        fixed_charge=bill.fixed_charge,
        duty_base=bill.duty_base,
        electricity_duty_percent=bill.electricity_duty_percent,
        electricity_duty=bill.electricity_duty,
        current_bill=bill.current_bill,
        net_adjustment=bill.net_adjustment,
        net_amount=bill.net_amount,
        prompt_payment_discount=bill.prompt_payment_discount,
        prompt_payable=bill.prompt_payable,
        after_due_payable=bill.after_due_payable,
        security_deposit_arrears=bill.security_deposit_arrears,
        security_deposit_held=bill.security_deposit_held,
        security_deposit_interest=bill.security_deposit_interest,
        delayed_payment_charge=bill.delayed_payment_charge,
        gst_percent=bill.gst_percent,
        gst_amount=bill.gst_amount,
        subtotal=bill.subtotal,
        total=bill.total,
        txt_path=filepath,
    )


def save_bill_txt(
    bill: BillResult,
    bill_no: str | None = None,
) -> tuple[str, str, str]:
    """Save bill as .txt, persist to SQLite, and return (bill_no, filepath, bill_text)."""
    import sqlite3

    bills_dir = _ensure_bills_dir()
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    explicit = ""
    if bill_no and str(bill_no).strip():
        explicit = _normalize_bill_no(str(bill_no))
    elif bill.bill_no and str(bill.bill_no).strip():
        explicit = _normalize_bill_no(str(bill.bill_no))

    if explicit:
        if bill_number_exists(explicit):
            raise ValueError(
                f"Bill number '{explicit}' already exists in the database."
            )
        bill.bill_no = explicit
        text = _bill_text(bill, explicit, timestamp)
        filename = f"{_safe_filename(explicit)}.txt"
        filepath = os.path.join(bills_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            _persist_bill(bill, explicit, timestamp, filepath)
        except sqlite3.IntegrityError as exc:
            if os.path.exists(filepath):
                os.remove(filepath)
            raise ValueError(
                f"Bill number '{explicit}' already exists in the database."
            ) from exc
        return explicit, filepath, text

    last_error: Exception | None = None
    for _ in range(5):
        auto_no = _next_bill_number()
        bill.bill_no = auto_no
        text = _bill_text(bill, auto_no, timestamp)
        filename = f"{_safe_filename(auto_no)}.txt"
        filepath = os.path.join(bills_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

        try:
            _persist_bill(bill, auto_no, timestamp, filepath)
            return auto_no, filepath, text
        except sqlite3.IntegrityError as exc:
            last_error = exc
            if os.path.exists(filepath):
                os.remove(filepath)
            continue

    raise RuntimeError(f"Could not allocate a unique bill number: {last_error}")


def save_bill_pdf(bill: BillResult, bill_no: str = "") -> tuple[str, str]:
    """Save bill as a styled PDF invoice using the user bill number."""
    bills_dir = _ensure_bills_dir()
    resolved = resolve_bill_number(bill, bill_no or None)
    bill.bill_no = resolved
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    filename = f"{_safe_filename(resolved)}.pdf"
    filepath = os.path.join(bills_dir, filename)

    def _pdf_safe(text: str) -> str:
        return text.encode("latin-1", errors="replace").decode("latin-1")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _pdf_safe(f"ELECTRICITY BILL - {TARIFF_NAME}"), ln=True, align="C")
    if TARIFF_ORDER:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, _pdf_safe(TARIFF_ORDER), ln=True, align="C")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, _pdf_safe(f"Bill No: {resolved}"), ln=True, align="C")
    if bill.bill_period:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, _pdf_safe(f"Bill of Supply for: {bill.bill_period}"), ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Date: {timestamp}", ln=True, align="C")
    pdf.cell(0, 7, f"Prompt Due: {bill.prompt_due_date}   Late Due: {bill.due_date}", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Customer Details", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, _pdf_safe(f"Bill Period : {bill.bill_period}"), ln=True)
    pdf.cell(0, 7, _pdf_safe(f"Name  : {bill.customer_name}"), ln=True)
    pdf.cell(0, 7, _pdf_safe(f"Phone : {bill.phone}"), ln=True)
    pdf.cell(0, 7, f"Connected Load : {bill.connected_load_kw:g} kW", ln=True)
    pdf.cell(0, 7, f"Units Consumed : {bill.units_consumed} kWh", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Cost Breakdown (Energy + FAC)", ln=True)
    pdf.set_font("Helvetica", "B", 9)
    col_w = [72, 22, 24, 24, 22, 26]
    headers = ["Slab", "Units", "Energy", "FAC", "E+FAC", "Amount"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for s in bill.slab_details:
        short = _pdf_safe(s.slab_label.split(" @ ")[0][:40])
        pdf.cell(col_w[0], 8, short, border=1)
        pdf.cell(col_w[1], 8, str(s.units), border=1, align="C")
        pdf.cell(col_w[2], 8, f"{s.energy_rate:.2f}", border=1, align="C")
        pdf.cell(col_w[3], 8, f"{s.fac_rate:.3f}", border=1, align="C")
        pdf.cell(col_w[4], 8, f"{s.rate:.3f}", border=1, align="C")
        pdf.cell(col_w[5], 8, f"{s.amount:.2f}", border=1, align="R")
        pdf.ln()
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    _pdf_row(pdf, "Fixed Charge (Residential)", bill.tod_fixed_charge)
    _pdf_row(pdf, "Municipal Surcharge", bill.municipal_surcharge)
    _pdf_row(pdf, "Total Fixed Charge", bill.fixed_charge)
    _pdf_row(pdf, "Energy Charge", bill.energy_charge)
    _pdf_row(pdf, "FAC Charge", bill.fac_charge)
    _pdf_row(pdf, f"Wheeling @ Rs.{bill.wheeling_rate:.2f}/U", bill.wheeling_charge)
    _pdf_row(pdf, "Duty Base", bill.duty_base)
    _pdf_row(pdf, f"Electricity Duty ({bill.electricity_duty_percent:.0f}%)", bill.electricity_duty)
    _pdf_row(pdf, "Current Bill", bill.current_bill)
    _pdf_row(pdf, "Net Adjustment", bill.net_adjustment)
    _pdf_row(pdf, "Net Amount", bill.net_amount)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(100, 9, "ROUNDED BILL (PAYABLE)")
    pdf.cell(40, 9, f"Rs. {bill.total:.2f}", ln=True, align="R")
    pdf.set_font("Helvetica", "", 10)
    _pdf_row(pdf, f"Prompt payable by {bill.prompt_due_date}", bill.prompt_payable)
    _pdf_row(pdf, f"After due ({bill.due_date})", bill.after_due_payable)
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(
        0, 6,
        _pdf_safe(
            f"Footnote: SD held Rs.{bill.security_deposit_held:.2f} | "
            f"SD arrears Rs.{bill.security_deposit_arrears:.2f} | "
            f"SD interest Rs.{bill.security_deposit_interest:.2f}"
        ),
        ln=True,
    )

    pdf.output(filepath)
    update_pdf_path(resolved, filepath)
    return resolved, filepath


def _pdf_row(pdf: FPDF, label: str, value: float) -> None:
    pdf.cell(100, 7, label, border=0)
    pdf.cell(40, 7, f"Rs. {value:.2f}", ln=True, align="R")
