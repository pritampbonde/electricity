"""Send electricity bill (with PDF attachment) via WhatsApp.

Supports two modes:
  1. **Twilio API** (recommended) — sends the message + PDF attachment
     programmatically. Requires Twilio credentials in billing_config.py
     or environment variables.
  2. **wa.me fallback** — opens WhatsApp Web with the text message
     pre-filled (no PDF attachment, user sends manually).
"""

import os
import urllib.parse
import webbrowser
import time

import requests
from twilio.rest import Client as TwilioClient

from bill_calculator import BillResult
from billing_config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM,
)

# ── Helpers ─────────────────────────────────────────────────────────────────


def _format_message(bill: BillResult, bill_no: str) -> str:
    """Build a WhatsApp-friendly bill summary message."""
    lines = [
        f"Hello {bill.customer_name},",
        "",
        "Here is your electricity bill summary:",
        f"  Bill No         : {bill_no}",
        f"  Units Consumed  : {bill.units_consumed} kWh",
        f"  Energy Charge   : Rs.{bill.energy_charge:.2f}",
        f"  Fixed Charge    : Rs.{bill.fixed_charge:.2f}",
        f"  Meter Rent      : Rs.{bill.meter_rent:.2f}",
        f"  Elec. Duty({bill.electricity_duty_percent}%): Rs.{bill.electricity_duty:.2f}",
    ]
    if bill.gst_percent > 0:
        lines.append(f"  GST ({bill.gst_percent}%)      : Rs.{bill.gst_amount:.2f}")
    lines += [
        f"  *Total Amount   : Rs.{bill.total:.2f}*",
        "",
        f"Please pay before *{bill.due_date}* to avoid late fees.",
        "Thank you!",
    ]
    return "\n".join(lines)


def _normalize_phone(phone: str) -> str:
    """Ensure phone number has country code and no extra characters."""
    digits = phone.strip().lstrip("+")
    digits = "".join(c for c in digits if c.isdigit())
    if not digits.startswith("91"):
        digits = "91" + digits
    return digits


def _upload_pdf_to_fileio(pdf_path: str) -> str:
    """Upload a PDF to file.io and return a one-time public download URL.

    file.io provides free temporary file hosting (file auto-deletes after
    first download, which is perfect for a one-time WhatsApp send).
    """
    with open(pdf_path, "rb") as f:
        resp = requests.post(
            "https://file.io",
            files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
            timeout=30,
        )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"file.io upload failed: {data}")
    return data["link"]


def _get_twilio_config() -> tuple[str, str, str] | None:
    """Return (account_sid, auth_token, from_number) or None if not configured."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID") or TWILIO_ACCOUNT_SID
    token = os.environ.get("TWILIO_AUTH_TOKEN") or TWILIO_AUTH_TOKEN
    from_num = os.environ.get("TWILIO_WHATSAPP_FROM") or TWILIO_WHATSAPP_FROM
    if sid and token and from_num:
        return sid, token, from_num
    return None


def is_twilio_configured() -> bool:
    """Check whether Twilio credentials are available."""
    return _get_twilio_config() is not None


# ── Public API ──────────────────────────────────────────────────────────────


def send_bill_twilio(bill: BillResult, bill_no: str, pdf_path: str) -> str:
    """Send bill summary + PDF attachment via Twilio WhatsApp API.

    The PDF is first uploaded to file.io to obtain a public URL that
    Twilio can fetch. Then a WhatsApp message is sent with the text
    summary and the PDF attached as media.

    Returns a status string.
    """
    config = _get_twilio_config()
    if config is None:
        raise RuntimeError(
            "Twilio is not configured. Set TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM in "
            "billing_config.py or as environment variables."
        )
    sid, token, from_number = config
    phone = _normalize_phone(bill.phone)
    to_number = f"whatsapp:+{phone}"
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"

    pdf_url = _upload_pdf_to_fileio(pdf_path)

    client = TwilioClient(sid, token)
    message = client.messages.create(
        from_=from_number,
        to=to_number,
        body=_format_message(bill, bill_no),
        media_url=[pdf_url],
    )
    return f"Sent! Twilio SID: {message.sid}"


def send_bill_whatsapp(bill: BillResult, bill_no: str, pdf_path: str = "") -> str:
    """Send bill via WhatsApp — Twilio (with PDF) or wa.me fallback (text only).

    Returns a status/URL string.
    """
    if is_twilio_configured() and pdf_path and os.path.isfile(pdf_path):
        return send_bill_twilio(bill, bill_no, pdf_path)

    phone = _normalize_phone(bill.phone)
    message = _format_message(bill, bill_no)
    encoded_msg = urllib.parse.quote(message)
    url = f"https://wa.me/{phone}?text={encoded_msg}"
    webbrowser.open(url)
    time.sleep(2)
    return url


def get_whatsapp_url(bill: BillResult, bill_no: str) -> str:
    """Return the WhatsApp wa.me URL (text only, no attachment)."""
    phone = _normalize_phone(bill.phone)
    message = _format_message(bill, bill_no)
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/{phone}?text={encoded_msg}"
