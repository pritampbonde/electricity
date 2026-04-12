"""Billing configuration — 2026 Residential Electricity Tariff."""

# Slab structure: (slab_width_in_units, rate_per_unit)
SLABS = [
    (100, 4.43),    # 0-100 units    -> Rs.4.43/unit
    (200, 9.64),    # 101-300 units  -> Rs.9.64/unit
    (200, 12.83),   # 301-500 units  -> Rs.12.83/unit
]
DEFAULT_RATE = 14.33  # above 500 units -> Rs.14.33/unit

FIXED_CHARGE = 150.0       # monthly fixed charge (Rs.)
METER_RENT = 35.0           # monthly meter rent (Rs.)
ELECTRICITY_DUTY_PERCENT = 16.0   # 16% on energy charges
GST_PERCENT = 0.0           # GST set to 0 since electricity duty applies instead

BILLS_DIR = "bills"

# ── Twilio WhatsApp Configuration ───────────────────────────────────────────
# Sign up at https://www.twilio.com and enable the WhatsApp Sandbox.
# Set these values here OR via environment variables of the same name.
TWILIO_ACCOUNT_SID = ""   # e.g. "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = ""     # e.g. "your_auth_token_here"
TWILIO_WHATSAPP_FROM = ""  # e.g. "whatsapp:+14155238886" (sandbox number)
