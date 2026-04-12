"""Generate electricity bill as a text file and a PDF invoice."""

import os
from datetime import datetime

from fpdf import FPDF

from bill_calculator import BillResult
from billing_config import BILLS_DIR
from database import insert_bill, update_pdf_path

_bill_counter = 0


def _next_bill_number() -> str:
    global _bill_counter
    _bill_counter += 1
    return f"EB-{datetime.now().strftime('%Y%m%d')}-{_bill_counter:04d}"


def _ensure_bills_dir() -> str:
    os.makedirs(BILLS_DIR, exist_ok=True)
    return BILLS_DIR


def _bill_text(bill: BillResult, bill_no: str, timestamp: str) -> str:
    """Return a human-readable plain-text version of the bill."""
    sep = "=" * 55
    lines = [
        sep,
        "       ELECTRICITY BILL / INVOICE (2026)",
        sep,
        f"  Bill No    : {bill_no}",
        f"  Date       : {timestamp}",
        f"  Due Date   : {bill.due_date}",
        f"  Customer   : {bill.customer_name}",
        f"  Phone      : {bill.phone}",
        sep,
        f"  Units Consumed : {bill.units_consumed} kWh",
        "",
        "  --- Cost Breakdown (per slab) ---",
    ]
    for s in bill.slab_details:
        lines.append(f"    {s.slab_label}")
        lines.append(f"      {s.units} units x Rs.{s.rate}  =  Rs.{s.amount:.2f}")
    lines += [
        "",
        f"  Energy Charge       : Rs.{bill.energy_charge:.2f}",
        f"  Fixed Charge        : Rs.{bill.fixed_charge:.2f}",
        f"  Meter Rent          : Rs.{bill.meter_rent:.2f}",
        f"  Elec. Duty ({bill.electricity_duty_percent}%) : Rs.{bill.electricity_duty:.2f}",
    ]
    if bill.gst_percent > 0:
        lines.append(f"  GST ({bill.gst_percent}%)           : Rs.{bill.gst_amount:.2f}")
    lines += [
        sep,
        f"  TOTAL AMOUNT        : Rs.{bill.total:.2f}",
        sep,
        "",
        f"  Please pay before {bill.due_date} to avoid late fees.",
        "",
    ]
    return "\n".join(lines)


def save_bill_txt(bill: BillResult) -> tuple[str, str, str]:
    """Save bill as .txt, persist to SQLite, and return (bill_no, filepath, bill_text)."""
    bills_dir = _ensure_bills_dir()
    bill_no = _next_bill_number()
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    text = _bill_text(bill, bill_no, timestamp)
    filename = f"{bill_no}.txt"
    filepath = os.path.join(bills_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    insert_bill(
        bill_no=bill_no,
        created_at=timestamp,
        due_date=bill.due_date,
        customer_name=bill.customer_name,
        phone=bill.phone,
        units_consumed=bill.units_consumed,
        energy_charge=bill.energy_charge,
        fixed_charge=bill.fixed_charge,
        meter_rent=bill.meter_rent,
        electricity_duty_percent=bill.electricity_duty_percent,
        electricity_duty=bill.electricity_duty,
        gst_percent=bill.gst_percent,
        gst_amount=bill.gst_amount,
        subtotal=bill.subtotal,
        total=bill.total,
        txt_path=filepath,
    )

    return bill_no, filepath, text


def save_bill_pdf(bill: BillResult, bill_no: str = "") -> tuple[str, str]:
    """Save bill as a styled PDF invoice and return (bill_no, filepath).

    If bill_no is provided the PDF reuses that number (linking it to the
    same database record created by save_bill_txt). Otherwise a new
    bill number is generated.
    """
    bills_dir = _ensure_bills_dir()
    if not bill_no:
        bill_no = _next_bill_number()
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    filename = f"{bill_no}.pdf"
    filepath = os.path.join(bills_dir, filename)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "ELECTRICITY BILL (2026)", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Bill No: {bill_no}    |    Date: {timestamp}", ln=True, align="C")
    pdf.cell(0, 7, f"Due Date: {bill.due_date}", ln=True, align="C")
    pdf.ln(6)

    # Customer info
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Customer Details", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Name  : {bill.customer_name}", ln=True)
    pdf.cell(0, 7, f"Phone : {bill.phone}", ln=True)
    pdf.cell(0, 7, f"Units Consumed : {bill.units_consumed} kWh", ln=True)
    pdf.ln(4)

    # Slab breakdown table
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Cost Breakdown", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    col_w = [90, 30, 25, 35]
    headers = ["Slab", "Units", "Rate", "Amount"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for s in bill.slab_details:
        pdf.cell(col_w[0], 8, s.slab_label, border=1)
        pdf.cell(col_w[1], 8, str(s.units), border=1, align="C")
        pdf.cell(col_w[2], 8, f"{s.rate:.2f}", border=1, align="C")
        pdf.cell(col_w[3], 8, f"{s.amount:.2f}", border=1, align="R")
        pdf.ln()
    pdf.ln(4)

    # Totals
    pdf.set_font("Helvetica", "", 11)
    _pdf_row(pdf, "Energy Charge", bill.energy_charge)
    _pdf_row(pdf, "Fixed Charge", bill.fixed_charge)
    _pdf_row(pdf, "Meter Rent", bill.meter_rent)
    _pdf_row(pdf, f"Electricity Duty ({bill.electricity_duty_percent}%)", bill.electricity_duty)
    if bill.gst_percent > 0:
        _pdf_row(pdf, f"GST ({bill.gst_percent}%)", bill.gst_amount)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(100, 10, "TOTAL AMOUNT")
    pdf.cell(40, 10, f"Rs. {bill.total:.2f}", ln=True, align="R")

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(
        0, 7,
        f"Please pay before {bill.due_date} to avoid late fees.",
        ln=True, align="C",
    )

    pdf.output(filepath)
    update_pdf_path(bill_no, filepath)
    return bill_no, filepath


def _pdf_row(pdf: FPDF, label: str, value: float) -> None:
    pdf.cell(100, 7, label, border=0)
    pdf.cell(40, 7, f"Rs. {value:.2f}", ln=True, align="R")
