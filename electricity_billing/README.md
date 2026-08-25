# Electricity Bill Calculator & WhatsApp Billing System

A Python application that calculates electricity bills using **MSEDCL LT-I Residential** tariff rates (MYT Order 217/2024 + Case 75/2025), generates invoices (TXT + PDF), persists records in **SQLite**, and sends bill summaries via WhatsApp (with PDF attachment when Twilio is configured).

---

## Quick Start

```bash
cd electricity_billing
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Web UI (recommended)
streamlit run app.py

# CLI
python main.py
```

No separate database setup is required — SQLite creates `bills/electricity_billing.db` on first run.

---

## Features

- **MSEDCL-accurate bill roll-up** — Energy, FAC, fixed, wheeling, electricity duty, prompt/after-due payables
- **Bill month & year** — required billing period on every bill; stored in DB; shown in history and all exports
- **Config-driven tariff** — edit `tariff_config.json` without code changes
- **TXT & PDF invoices** — saved under `bills/`
- **SQLite persistence** — full charge breakdown + lightweight schema migration
- **Bill History** — stats, search (bill no / name / phone), re-download exports
- **WhatsApp** — Twilio (PDF) or wa.me text fallback
- **Streamlit UI** + **CLI**
- **pytest suite** — 61 tests with HTML report

---

## Tariff Configuration

All rates live in **`tariff_config.json`** (loaded by `billing_config.py`).

### Tariff slabs (LT-I Residential)

| Units slab | Energy charge (₹/unit) | FAC (₹/unit) |
|---|---:|---:|
| 0–100 | 3.96 | 0.350 |
| 101–300 | 10.80 | 0.650 |
| 301–500 | 15.03 | 0.850 |
| 501–1000 | 17.53 | 0.950 |
| Above 1000 | 17.53 | 0.950 |

### Fixed + direct / flat charges

| Item | Amount | Note |
|---|---|---|
| Residential fixed | ₹130 / month | Flat for LT-I Res 1-phase (`fixed_charge_mode: flat`) |
| Municipal surcharge | ₹10 / month | Effective 01-07-2025 |
| Wheeling | ₹1.60 / unit | Flat on all units |
| Electricity duty | 16% | On (Fixed + Energy + Wheeling + FAC) |
| Prompt discount | 1% | Of duty base; prompt payable rounded to nearest ₹10 |
| After-due surcharge | ₹50 | Added to rounded bill |

### Bill roll-up

1. Energy (slab) + FAC (slab) + Fixed + Wheeling  
2. Electricity duty **16%** on that duty base  
3. Current bill → net adjustment → **rounded payable** (ceil any paise to next rupee)  
4. Prompt payable / after-due payable  

### Footnote items (not in rounded total by default)

| Item | Amount |
|---|---:|
| Security deposit held | ₹2,190 |
| Security deposit arrears | ₹3,000 |
| Interest on SD | ₹54.27 |
| Digital payment discount | ₹9.36 |

---

## Workflow

### 1. Start the app

```bash
streamlit run app.py   # Web UI
python main.py         # CLI menu
```

### 2. Enter bill inputs

| Input | Notes |
|---|---|
| Bill number | Pre-filled from DB sequence (`EB-YYYYMMDD-NNNN`); must be unique |
| Customer name / phone | Required |
| **Bill month / year** | Billing period (e.g. May 2026); persisted and exported |
| Units (kWh) | Default `0` |
| Connected load (kW) | Default `0.00` |
| Net adjustment | Credit as negative (e.g. `-2.85`) |
| Optional items | Include SD arrears / delayed payment in total (off by default) |

### 3. Calculate (MSEDCL roll-up)

```
Energy (slab) + FAC (slab) + Fixed (₹130+₹10) + Wheeling (₹1.60×units)
        → Duty base × 16% electricity duty
        → Current bill ± net adjustment
        → Rounded payable (ceil paise)
        → Prompt payable (1% discount, nearest ₹10)
        → After-due payable (rounded + ₹50)
```

### 4. Persist & export

On **Generate Bill**:

1. Save to SQLite (`bills/electricity_billing.db`) including `bill_month` and `bill_year`
2. Write **TXT** invoice under `bills/` (includes bill period)
3. Write **PDF** invoice under `bills/` (includes bill period)
4. Show download buttons for TXT / PDF
5. Optional **WhatsApp** send (Twilio + PDF, or wa.me text) — includes bill period

### 5. Bill History

- Dashboard metrics (count, revenue, average, units)
- Search by bill number, customer name, or phone
- Table / detail view shows **bill period** (month + year)
- Re-download TXT / PDF for any past bill

### End-to-end flow

```
Inputs (incl. month/year)
        │
        ▼
bill_calculator.py  ──► BillResult (charges + payables + period)
        │
        ├──► database.py      (SQLite: connection, insert, month/year, breakdown)
        ├──► bill_generator   (TXT + PDF exports with period)
        └──► whatsapp_sender  (optional message with period)
                │
                ▼
        Bill History (search / stats / re-download)
```

---

## Running Tests

Tests live under `tests/` and cover:

- MSEDCL calculation (including Flat2-May golden case)
- Tariff config
- **SQLite connection** + CRUD / search / stats
- TXT / PDF export
- WhatsApp message formatting

### Install & run

```bash
cd electricity_billing
source .venv/bin/activate
pip install -r requirements.txt

# All tests
pytest

# Verbose
pytest -v

# One module
pytest tests/test_bill_calculator.py -v

# SQLite connection tests only
pytest tests/test_database.py::TestSqliteConnection -v
```

### Generate HTML test report

```bash
pytest --html=test_report.html --self-contained-html
open test_report.html          # macOS
# xdg-open test_report.html    # Linux
```

### Latest report summary

| Metric | Value |
|---|---|
| Total tests | 61 |
| Passed | 61 |
| Failed | 0 |
| Report file | `test_report.html` |

### Test modules

| File | Coverage |
|---|---|
| `tests/test_bill_calculator.py` | Rounding, validation, bill period, Flat2-May golden case, slab boundaries |
| `tests/test_billing_config.py` | Tariff JSON rates, fixed-charge helpers |
| `tests/test_database.py` | **SQLite connection** (open/close, version, schema, columns), insert/fetch, duplicates, search, stats, bill-number sequence |
| `tests/test_bill_generator.py` | TXT/PDF export + DB persistence of month/year |
| `tests/test_whatsapp_sender.py` | Message text, phone normalize, wa.me URL |

### SQLite connection tests (`TestSqliteConnection`)

| Test | What it checks |
|---|---|
| `test_db_file_created_on_init` | `electricity_billing.db` is created under `bills/` |
| `test_connect_opens_and_closes` | `_connect()` opens a connection and closes it on exit |
| `test_connection_executes_select` | Live connection can run `SELECT 1` |
| `test_sqlite_version_available` | `sqlite_version()` is readable |
| `test_row_factory_is_sqlite_row` | Row factory is `sqlite3.Row` |
| `test_bills_table_exists` | `bills` table exists after `init_db()` |
| `test_bills_table_has_required_columns` | Required columns present (incl. `bill_month`, `bill_year`) |
| `test_reconnect_after_close` | New connection works after previous close |
| `test_init_db_is_idempotent` | Calling `init_db()` twice is safe |

---

## Project Structure

```
electricity_billing/
├── tariff_config.json      # Editable LT-I rates, fixed & direct charges
├── billing_config.py       # Loads tariff_config.json + Twilio settings
├── app.py                  # Streamlit web frontend
├── main.py                 # CLI entry point
├── bill_calculator.py      # MSEDCL calculation engine
├── bill_generator.py       # TXT & PDF invoice generation + DB insert
├── database.py             # SQLite connection, schema, CRUD, search, stats
├── whatsapp_sender.py      # WhatsApp sender (Twilio + wa.me fallback)
├── tests/                  # pytest suite (61 tests)
│   ├── conftest.py         # Isolated temp bills/ DB per test
│   ├── test_bill_calculator.py
│   ├── test_billing_config.py
│   ├── test_database.py    # Includes TestSqliteConnection
│   ├── test_bill_generator.py
│   └── test_whatsapp_sender.py
├── pytest.ini
├── test_report.html        # Generated HTML report
├── bills/                  # Invoices + electricity_billing.db
├── requirements.txt
└── README.md
```

---

## WhatsApp Setup (Twilio — for PDF attachment)

```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token_here"
export TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"
```

**Without Twilio:** the app falls back to a wa.me link (text-only, no PDF attachment).

---

## Requirements

- Python 3.10+
- `fpdf2` — PDF generation
- `streamlit` — Web UI
- `twilio` — WhatsApp API (PDF attachment)
- `requests` — temporary PDF hosting for Twilio media
- `pytest` / `pytest-html` — test runner and HTML report
- `sqlite3` — database (built into Python)
