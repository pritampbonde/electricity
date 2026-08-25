"""Billing configuration — loads LT-I Residential tariff from tariff_config.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).resolve().parent / "tariff_config.json"


def _load_tariff_config() -> dict[str, Any]:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


TARIFF = _load_tariff_config()

TARIFF_NAME: str = TARIFF["tariff_name"]
TARIFF_DETAILS: str = TARIFF.get("tariff_details", "")
TARIFF_ORDER: str = TARIFF.get("tariff_order", "")
DUE_DAYS: int = int(TARIFF.get("due_days", 15))
GST_PERCENT: float = float(TARIFF.get("gst_percent", 0.0))

# Each slab: (up_to_units | None for open-ended, energy_rate, fac_rate, label)
SLABS: list[tuple[int | None, float, float, str]] = [
    (
        s["up_to_units"],
        float(s["energy_rate"]),
        float(s["fac_rate"]),
        str(s["label"]),
    )
    for s in TARIFF["slabs"]
]

_FIXED = TARIFF["fixed_charges"]
TOD_FIXED_PER_KW: float = float(_FIXED["tod_per_kw"])
DEFAULT_CONNECTED_LOAD_KW: float = float(_FIXED.get("default_connected_load_kw", 1.0))
TOD_FIXED_NOTE: str = str(_FIXED.get("tod_note", ""))
MUNICIPAL_SURCHARGE: float = float(_FIXED["municipal_surcharge"])
MUNICIPAL_SURCHARGE_NOTE: str = str(_FIXED.get("municipal_surcharge_note", ""))
MUNICIPAL_SURCHARGE_EFFECTIVE_FROM: str = str(
    _FIXED.get("municipal_surcharge_effective_from", "")
)


def total_fixed_charge(connected_load_kw: float | None = None) -> float:
    """TOD fixed + municipal surcharge for the given connected load (kW)."""
    kw = DEFAULT_CONNECTED_LOAD_KW if connected_load_kw is None else connected_load_kw
    tod = round(TOD_FIXED_PER_KW * kw, 2)
    return round(tod + MUNICIPAL_SURCHARGE, 2)


# Back-compat alias used by older call sites / UI totals
FIXED_CHARGE: float = total_fixed_charge()

_OTHER = TARIFF["other_charges"]
SECURITY_DEPOSIT_ARREARS: float = float(_OTHER.get("security_deposit_arrears", 0.0))
SECURITY_DEPOSIT_HELD: float = float(_OTHER.get("security_deposit_held", 0.0))
SECURITY_DEPOSIT_INTEREST: float = float(_OTHER.get("security_deposit_interest", 0.0))
SECURITY_DEPOSIT_NOTE: str = str(_OTHER.get("security_deposit_note", ""))
DELAYED_PAYMENT_CHARGE: float = float(_OTHER.get("delayed_payment_charge", 0.0))
DELAYED_PAYMENT_CHARGE_AFTER: float = float(
    _OTHER.get("delayed_payment_charge_after", 0.0)
)
DELAYED_PAYMENT_EARLY_DEADLINE: str = str(
    _OTHER.get("delayed_payment_early_deadline", "")
)
DELAYED_PAYMENT_LATE_DEADLINE: str = str(
    _OTHER.get("delayed_payment_late_deadline", "")
)
DELAYED_PAYMENT_NOTE: str = str(_OTHER.get("delayed_payment_note", ""))
INCLUDE_SECURITY_DEPOSIT_BY_DEFAULT: bool = bool(
    _OTHER.get("include_security_deposit_by_default", True)
)
INCLUDE_DELAYED_PAYMENT_BY_DEFAULT: bool = bool(
    _OTHER.get("include_delayed_payment_by_default", True)
)

BILLS_DIR = "bills"
TARIFF_CONFIG_PATH = str(_CONFIG_PATH)

# ── Twilio WhatsApp Configuration ───────────────────────────────────────────
# Sign up at https://www.twilio.com and enable the WhatsApp Sandbox.
# Set these values here OR via environment variables of the same name.
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")


def reload_tariff_config() -> None:
    """Reload tariff_config.json into module-level constants (for tests / hot reload)."""
    global TARIFF, TARIFF_NAME, TARIFF_DETAILS, TARIFF_ORDER, DUE_DAYS, GST_PERCENT
    global SLABS, TOD_FIXED_PER_KW, DEFAULT_CONNECTED_LOAD_KW, TOD_FIXED_NOTE
    global MUNICIPAL_SURCHARGE, MUNICIPAL_SURCHARGE_NOTE, MUNICIPAL_SURCHARGE_EFFECTIVE_FROM
    global FIXED_CHARGE
    global SECURITY_DEPOSIT_ARREARS, SECURITY_DEPOSIT_HELD, SECURITY_DEPOSIT_INTEREST
    global SECURITY_DEPOSIT_NOTE, DELAYED_PAYMENT_CHARGE, DELAYED_PAYMENT_CHARGE_AFTER
    global DELAYED_PAYMENT_EARLY_DEADLINE, DELAYED_PAYMENT_LATE_DEADLINE
    global DELAYED_PAYMENT_NOTE, INCLUDE_SECURITY_DEPOSIT_BY_DEFAULT
    global INCLUDE_DELAYED_PAYMENT_BY_DEFAULT

    TARIFF = _load_tariff_config()
    TARIFF_NAME = TARIFF["tariff_name"]
    TARIFF_DETAILS = TARIFF.get("tariff_details", "")
    TARIFF_ORDER = TARIFF.get("tariff_order", "")
    DUE_DAYS = int(TARIFF.get("due_days", 15))
    GST_PERCENT = float(TARIFF.get("gst_percent", 0.0))
    SLABS = [
        (
            s["up_to_units"],
            float(s["energy_rate"]),
            float(s["fac_rate"]),
            str(s["label"]),
        )
        for s in TARIFF["slabs"]
    ]
    _fixed = TARIFF["fixed_charges"]
    TOD_FIXED_PER_KW = float(_fixed["tod_per_kw"])
    DEFAULT_CONNECTED_LOAD_KW = float(_fixed.get("default_connected_load_kw", 1.0))
    TOD_FIXED_NOTE = str(_fixed.get("tod_note", ""))
    MUNICIPAL_SURCHARGE = float(_fixed["municipal_surcharge"])
    MUNICIPAL_SURCHARGE_NOTE = str(_fixed.get("municipal_surcharge_note", ""))
    MUNICIPAL_SURCHARGE_EFFECTIVE_FROM = str(
        _fixed.get("municipal_surcharge_effective_from", "")
    )
    FIXED_CHARGE = total_fixed_charge()
    _other = TARIFF["other_charges"]
    SECURITY_DEPOSIT_ARREARS = float(_other.get("security_deposit_arrears", 0.0))
    SECURITY_DEPOSIT_HELD = float(_other.get("security_deposit_held", 0.0))
    SECURITY_DEPOSIT_INTEREST = float(_other.get("security_deposit_interest", 0.0))
    SECURITY_DEPOSIT_NOTE = str(_other.get("security_deposit_note", ""))
    DELAYED_PAYMENT_CHARGE = float(_other.get("delayed_payment_charge", 0.0))
    DELAYED_PAYMENT_CHARGE_AFTER = float(
        _other.get("delayed_payment_charge_after", 0.0)
    )
    DELAYED_PAYMENT_EARLY_DEADLINE = str(
        _other.get("delayed_payment_early_deadline", "")
    )
    DELAYED_PAYMENT_LATE_DEADLINE = str(
        _other.get("delayed_payment_late_deadline", "")
    )
    DELAYED_PAYMENT_NOTE = str(_other.get("delayed_payment_note", ""))
    INCLUDE_SECURITY_DEPOSIT_BY_DEFAULT = bool(
        _other.get("include_security_deposit_by_default", True)
    )
    INCLUDE_DELAYED_PAYMENT_BY_DEFAULT = bool(
        _other.get("include_delayed_payment_by_default", True)
    )
