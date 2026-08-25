# Electricity Bill Calculator & WhatsApp Billing System

A Python application that calculates electricity bills using **2026 Residential Tariff** rates, generates invoices (TXT + PDF), persists all records in a **SQLite database**, and sends bill summaries via WhatsApp — with PDF attachment.

## 2026 Residential Tariff

| Slab | Rate |
|---|---|
| 0 - 100 units | ₹4.43/unit |
| 101 - 300 units | ₹9.64/unit |
| 301 - 500 units | ₹12.83/unit |
| Above 500 units | ₹14.33/unit |

**Other Charges:**
- Fixed Charge: ₹150/month
- Meter Rent: ₹35/month
- Electricity Duty: 16% on energy charges
- Due Date: 15 days from bill date

## Features

- **Slab-based billing** with 4-tier 2026 residential rates
- **PDF & TXT invoice generation** saved under `bills/`
- **SQLite database** — every bill is persisted with full details (created date, due date, customer info, charge breakdown, file paths, WhatsApp status)
- **Dashboard stats** — total bills, total revenue, average bill, total units sold
- **Search** — find bills by customer name or phone number
- **Due date calculation** — auto-computed 15 days from bill creation
- **WhatsApp delivery with PDF attachment** via Twilio API
- **Fallback** — wa.me link (text-only) if Twilio is not configured
- **Modern web UI** built with Streamlit (gradient cards, slab tables, interactive data table)
- **CLI mode** for terminal usage

## Use Tmux Session 
- ** tmux new-session -c /Users/pritam.bonde@cohesity.com/Downloads/electricity-main/electricity_billing \; split-window -h -c /Users/pritam.bonde@cohesity.com/Downloads/electricity-main/electricity_billing

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Option 1: Launch the web UI (recommended)
streamlit run app.py

# Option 2: Run CLI mode
python main.py
```

No database setup needed — SQLite is built into Python. The database file (`electricity_billing.db`) is auto-created in the `bills/` directory on first run.

## Database

All bills are stored in `bills/electricity_billing.db` with the following schema:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `bill_no` | TEXT | Unique bill number (e.g. EB-20260411-0001) |
| `created_at` | TEXT | Bill creation timestamp |
| `due_date` | TEXT | Payment due date (bill date + 15 days) |
| `customer_name` | TEXT | Customer name |
| `phone` | TEXT | Phone number |
| `units_consumed` | INTEGER | kWh consumed |
| `energy_charge` | REAL | Slab-based energy cost |
| `fixed_charge` | REAL | Monthly fixed charge |
| `meter_rent` | REAL | Meter rent |
| `electricity_duty_percent` | REAL | Duty rate (16%) |
| `electricity_duty` | REAL | Calculated duty amount |
| `gst_percent` | REAL | GST rate |
| `gst_amount` | REAL | GST amount |
| `subtotal` | REAL | Pre-tax subtotal |
| `total` | REAL | Final bill amount |
| `txt_path` | TEXT | Path to generated TXT file |
| `pdf_path` | TEXT | Path to generated PDF file |
| `whatsapp_sent` | INTEGER | 0 = not sent, 1 = sent |

## WhatsApp Setup (Twilio — for PDF attachment)

To send the PDF bill as a WhatsApp attachment, you need a **Twilio** account:

1. Sign up at [twilio.com](https://www.twilio.com)
2. Activate the **WhatsApp Sandbox** in the Twilio Console:
   - Go to *Messaging → Try it out → Send a WhatsApp message*
   - Follow the instructions to join the sandbox from your phone
3. Copy your credentials and set them in `billing_config.py`:

```python
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN   = "your_auth_token_here"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"  # sandbox number
```

Or set them as environment variables:

```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token_here"
export TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"
```

**Without Twilio:** The app falls back to a wa.me link that opens WhatsApp Web with the text message pre-filled (no PDF attachment).

## Project Structure

```
electricity_billing/
├── app.py               # Streamlit web frontend
├── main.py              # CLI entry point
├── bill_calculator.py   # Slab-based calculation engine
├── bill_generator.py    # TXT & PDF invoice generation + DB insert
├── database.py          # SQLite schema, CRUD, search, stats
├── whatsapp_sender.py   # WhatsApp sender (Twilio + wa.me fallback)
├── billing_config.py    # 2026 tariff + Twilio config
├── bills/               # Generated invoices + SQLite database
│   └── electricity_billing.db
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10+
- `fpdf2` — PDF generation
- `twilio` — WhatsApp API (send PDF attachment)
- `requests` — temporary PDF hosting for Twilio media
- `streamlit` — Web UI
- `sqlite3` — database (built into Python, no install needed)
