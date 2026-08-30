#!/usr/bin/env python3
"""Electricity Bill Calculator & WhatsApp Billing System — CLI entry point."""

from __future__ import annotations

import os
import sys

from bill_calculator import calculate_bill, BillResult
from bill_generator import save_bill_txt, save_bill_pdf
from whatsapp_sender import send_bill_whatsapp, is_twilio_configured
from billing_config import BILLS_DIR
from database import get_all_bills, search_bills, get_bill_stats, delete_bill

BANNER = r"""
 _____ _           _        _      _ _         ____  _ _ _ _
| ____| | ___  ___| |_ _ __(_) ___(_) |_ _   _| __ )(_) | (_)_ __   __ _
|  _| | |/ _ \/ __| __| '__| |/ __| | __| | | |  _ \| | | | | '_ \ / _` |
| |___| |  __/ (__| |_| |  | | (__| | |_| |_| | |_) | | | | | | | | (_| |
|_____|_|\___|\___|\__|_|  |_|\___|_|\__|\__, |____/|_|_|_|_|_| |_|\__, |
                                         |___/                     |___/
"""

_last_bill: BillResult | None = None
_last_bill_no: str | None = None
_last_pdf_path: str | None = None


def _input_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("  Please enter a valid integer.")


def _create_bill() -> None:
    global _last_bill, _last_bill_no, _last_pdf_path

    print("\n--- Create New Bill ---")
    name = input("  Customer name : ").strip()
    if not name:
        print("  Name cannot be empty.")
        return
    phone = input("  Phone number  : ").strip()
    if not phone:
        print("  Phone number cannot be empty.")
        return
    units = _input_int("  Units consumed (kWh): ")
    try:
        load_raw = input("  Connected load kW [4]: ").strip()
        connected_kw = float(load_raw) if load_raw else 4.0
    except ValueError:
        print("  Invalid connected load; using 4 kW.")
        connected_kw = 4.0
    try:
        adj_raw = input("  Net adjustment (credit as negative) [0]: ").strip()
        net_adj = float(adj_raw) if adj_raw else 0.0
    except ValueError:
        print("  Invalid adjustment; using 0.")
        net_adj = 0.0
    from datetime import datetime as _dt
    _now = _dt.now()
    try:
        month_raw = input(f"  Bill month 1-12 [{_now.month}]: ").strip()
        bill_month = int(month_raw) if month_raw else _now.month
    except ValueError:
        print("  Invalid month; using current month.")
        bill_month = _now.month
    try:
        year_raw = input(f"  Bill year [{_now.year}]: ").strip()
        bill_year = int(year_raw) if year_raw else _now.year
    except ValueError:
        print("  Invalid year; using current year.")
        bill_year = _now.year

    from database import suggest_next_bill_number, bill_number_exists
    suggested = suggest_next_bill_number()
    bill_no_raw = input(f"  Bill number [{suggested}]: ").strip()
    bill_no_custom = bill_no_raw or suggested
    if bill_number_exists(bill_no_custom):
        print(f"  Error: Bill number '{bill_no_custom}' already exists in the database.")
        return

    try:
        bill = calculate_bill(
            name,
            phone,
            units,
            connected_load_kw=connected_kw,
            net_adjustment=net_adj,
            bill_month=bill_month,
            bill_year=bill_year,
            bill_no=bill_no_custom,
        )
    except ValueError as exc:
        print(f"  Error: {exc}")
        return

    try:
        bill_no, txt_path, bill_text = save_bill_txt(bill, bill_no=bill.bill_no)
    except ValueError as exc:
        print(f"  Error: {exc}")
        return
    print(f"\n{bill_text}")
    print(f"  Bill Number      : {bill.bill_no}")
    print(f"  Text bill saved  → {txt_path}")

    pdf_path = ""
    try:
        _, pdf_path = save_bill_pdf(bill, bill_no=bill.bill_no)
        print(f"  PDF  bill saved  → {pdf_path}")
    except Exception as exc:
        print(f"  (PDF generation skipped: {exc})")

    print(f"  Saved to database ✓  (bill_no={bill.bill_no})")

    _last_bill = bill
    _last_bill_no = bill.bill_no
    _last_pdf_path = pdf_path


def _view_previous_bills() -> None:
    print("\n--- Previous Bills (from database) ---")
    bills = get_all_bills()
    if not bills:
        print("  No bills found in database.")
        return

    # Summary stats
    stats = get_bill_stats()
    print(f"  Total bills: {stats['total_bills']}  |  "
          f"Revenue: Rs.{stats['total_revenue']:.2f}  |  "
          f"Avg bill: Rs.{stats['avg_bill']:.2f}")
    print()

    for i, b in enumerate(bills, 1):
        wa = " [WA sent]" if b["whatsapp_sent"] else ""
        m = int(b.get("bill_month") or 0)
        y = int(b.get("bill_year") or 0)
        _names = [
            "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        period = f"{_names[m]} {y}" if 1 <= m <= 12 and y else "—"
        print(f"  {i}. {b['bill_no']}  |  {period:<12s}  |  {b['customer_name']:<20s}  |  "
              f"{b['units_consumed']:>5d} kWh  |  Rs.{b['total']:>10.2f}  |  "
              f"{b['created_at']}{wa}")

    print()
    choice = input("  Enter number to view detail (or press Enter to go back): ").strip()
    if not choice:
        return
    try:
        idx = int(choice) - 1
        b = bills[idx]
        m = int(b.get("bill_month") or 0)
        y = int(b.get("bill_year") or 0)
        _names = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        period = f"{_names[m]} {y}" if 1 <= m <= 12 and y else "N/A"
        print(f"\n  {'=' * 50}")
        print(f"  Bill No         : {b['bill_no']}")
        print(f"  Bill Period     : {period}")
        print(f"  Created         : {b['created_at']}")
        print(f"  Due Date        : {b['due_date']}")
        print(f"  Customer        : {b['customer_name']}")
        print(f"  Phone           : {b['phone']}")
        print(f"  Units Consumed  : {b['units_consumed']} kWh")
        print(f"  Connected Load  : {b.get('connected_load_kw', 1)} kW")
        print(f"  Energy Charge   : Rs.{b['energy_charge']:.2f}")
        print(f"  FAC Charge      : Rs.{b.get('fac_charge', 0):.2f}")
        print(f"  Wheeling        : Rs.{b.get('wheeling_charge', 0):.2f}")
        print(f"  Fixed Charge    : Rs.{b['fixed_charge']:.2f}")
        print(f"  Elec. Duty      : Rs.{b.get('electricity_duty', 0):.2f}")
        print(f"  Current Bill    : Rs.{b.get('current_bill', b['subtotal']):.2f}")
        print(f"  Net Adjustment  : Rs.{b.get('net_adjustment', 0):.2f}")
        print(f"  Rounded Total   : Rs.{b['total']:.2f}")
        print(f"  Prompt Payable  : Rs.{b.get('prompt_payable', 0):.2f} by {b.get('prompt_due_date', '')}")
        print(f"  After-Due Pay   : Rs.{b.get('after_due_payable', 0):.2f}")
        print(f"  SD Held/Arrears : Rs.{b.get('security_deposit_held', 0):.2f} / Rs.{b.get('security_deposit_arrears', 0):.2f}")
        print(f"  TXT file        : {b['txt_path'] or 'N/A'}")
        print(f"  PDF file        : {b['pdf_path'] or 'N/A'}")
        print(f"  WhatsApp sent   : {'Yes' if b['whatsapp_sent'] else 'No'}")
        print(f"  {'=' * 50}")
        del_choice = input("  Delete this bill? (y/n) [n]: ").strip().lower()
        if del_choice == "y":
            del_files = input("  Also delete invoice files (.txt / .pdf)? (y/n) [y]: ").strip().lower() != "n"
            if delete_bill(b["bill_no"], delete_files=del_files):
                print(f"  ✓ Bill {b['bill_no']} deleted successfully.")
            else:
                print("  ✗ Failed to delete bill.")
    except (ValueError, IndexError):
        print("  Invalid selection.")


def _send_via_whatsapp() -> None:
    if _last_bill is None or _last_bill_no is None:
        print("\n  No bill in current session. Create a bill first.")
        return

    print(f"\n--- Send Bill {_last_bill_no} via WhatsApp ---")
    print(f"  Customer : {_last_bill.customer_name}")
    print(f"  Phone    : {_last_bill.phone}")

    if is_twilio_configured() and _last_pdf_path:
        print("  Mode     : Twilio (message + PDF attachment)")
    else:
        print("  Mode     : WhatsApp Web (text only, no PDF attachment)")
        if not is_twilio_configured():
            print("  Tip: Configure Twilio in billing_config.py to send PDF.")

    confirm = input("  Send now? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    try:
        result = send_bill_whatsapp(_last_bill, _last_bill_no, _last_pdf_path or "")
        print(f"  {result}")
    except Exception as exc:
        print(f"  WhatsApp send failed: {exc}")


def main() -> None:
    print(BANNER)

    menu = (
        "\n==================== MENU ====================\n"
        "  1. Create New Bill\n"
        "  2. View Previous Bills\n"
        "  3. Send Last Bill via WhatsApp\n"
        "  4. Exit\n"
        "==============================================="
    )

    while True:
        print(menu)
        choice = input("  Choose an option (1-4): ").strip()

        if choice == "1":
            _create_bill()
        elif choice == "2":
            _view_previous_bills()
        elif choice == "3":
            _send_via_whatsapp()
        elif choice == "4":
            print("\n  Goodbye!\n")
            sys.exit(0)
        else:
            print("  Invalid option. Please choose 1-4.")


if __name__ == "__main__":
    main()
