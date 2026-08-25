# Electricity Bill Calculator & WhatsApp Billing System

A Python application that calculates electricity bills using **LT-I Residential** tariff rates (MYT Order 217/2024), generates invoices (TXT + PDF), persists all records in a **SQLite database**, and sends bill summaries via WhatsApp — with PDF attachment.

## Tariff Configuration

All rates and fixed charges live in **`tariff_config.json`** (loaded by `billing_config.py`). Edit that file to change slabs, FAC, or fixed charges — no code changes required.

### Tariff slabs (LT-I Residential)

| Units slab | Energy charge (₹/unit) | FAC (₹/unit) |
|---|---|---|
| 0–100 | 3.96 | 0.200 |
| 101–300 | 10.80 | 0.400 |
| 301–500 | 15.03 | 0.550 |
| 501–1000 | 17.53 | 0.600 |
| Above 1000 | 17.53 | 0.600 |

### Fixed charges (not linked to consumption)

| Item | Amount (₹) | Note |
|---|---|---|
| Fixed charge (TOD) | 130.00 /kW/month | ₹130 per kW of connected load per month, per MYT Order 217/2024 |
| Municipal corporation area surcharge | 10.00 /month | Additional fixed charge for MC-area consumers, effective 01-07-2025 |
| Total fixed charge (at 1 kW) | 140.00 | Payable even at zero consumption |

### Other charges

| Item | Amount (₹) | Note |
|---|---|---|
| Security deposit arrears | 3,000.00 | Outstanding SD (₹2,190 currently held); interest on SD ₹4.87 |
| Delayed payment charge | 10.00 | ₹10 by 31-08-2026 → ₹20 after 11-09-2026 |

## Features

- **Slab-based billing** with Energy + FAC per slab
- **Config-driven tariff** via `tariff_config.json`
- **PDF & TXT invoice generation** saved under `bills/`
- **SQLite database** — every bill is persisted with full charge breakdown
- **Dashboard stats** — total bills, total revenue, average bill, total units sold
- **Search** — find bills by customer name or phone number
- **Due date calculation** — auto-computed from `due_days` in config
- **WhatsApp delivery with PDF attachment** via Twilio API
- **Fallback** — wa.me link (text-only) if Twilio is not configured
- **Modern web UI** built with Streamlit (tariff card, fixed/other charges, slab tables)
- **CLI mode** for terminal usage

## Quick Start

```bash
# Create a virtual environment (recommended on Homebrew Python)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Option 1: Launch the web UI (recommended)
streamlit run app.py

# Option 2: Run CLI mode
python main.py
```

No database setup needed — SQLite is built into Python. The database file (`electricity_billing.db`) is auto-created in the `bills/` directory on first run.

## Project Structure

```
electricity_billing/
├── tariff_config.json   # Editable LT-I rates, fixed & other charges
├── billing_config.py    # Loads tariff_config.json + Twilio settings
├── app.py               # Streamlit web frontend
├── main.py              # CLI entry point
├── bill_calculator.py   # Slab + FAC calculation engine
├── bill_generator.py    # TXT & PDF invoice generation + DB insert
├── database.py          # SQLite schema, CRUD, search, stats
├── whatsapp_sender.py   # WhatsApp sender (Twilio + wa.me fallback)
├── bills/               # Generated invoices + SQLite database
├── requirements.txt
└── README.md
```

## WhatsApp Setup (Twilio — for PDF attachment)

To send the PDF bill as a WhatsApp attachment, you need a **Twilio** account:

1. Sign up at [twilio.com](https://www.twilio.com)
2. Activate the **WhatsApp Sandbox** in the Twilio Console
3. Set credentials in `billing_config.py` or as environment variables:

```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token_here"
export TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"
```

**Without Twilio:** The app falls back to a wa.me link (text-only, no PDF attachment).

## Requirements

- Python 3.10+
- `fpdf2` — PDF generation
- `twilio` — WhatsApp API (send PDF attachment)
- `requests` — temporary PDF hosting for Twilio media
- `streamlit` — Web UI
- `sqlite3` — database (built into Python, no install needed)
