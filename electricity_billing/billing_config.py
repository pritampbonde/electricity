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
DUE_DAYS: int = int(TARIFF.get("due_days", 20))
PROMPT_DUE_DAYS: int = int(TARIFF.get("prompt_due_days", 10))
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
RESIDENTIAL_FIXED: float = float(_FIXED.get("residential_fixed", 130.0))
RESIDENTIAL_FIXED_NOTE: str = str(_FIXED.get("residential_fixed_note", ""))
FIXED_CHARGE_MODE: str = str(_FIXED.get("fixed_charge_mode", "flat")).lower()
TOD_FIXED_PER_KW: float = float(_FIXED.get("tod_per_kw", RESIDENTIAL_FIXED))
DEFAULT_CONNECTED_LOAD_KW: float = float(_FIXED.get("default_connected_load_kw", 4.0))
TOD_FIXED_NOTE: str = str(_FIXED.get("tod_note", ""))
MUNICIPAL_SURCHARGE: float = float(_FIXED["municipal_surcharge"])
MUNICIPAL_SURCHARGE_NOTE: str = str(_FIXED.get("municipal_surcharge_note", ""))
MUNICIPAL_SURCHARGE_EFFECTIVE_FROM: str = str(
    _FIXED.get("municipal_surcharge_effective_from", "")
)


def residential_fixed_component(connected_load_kw: float | None = None) -> float:
    """Residential fixed portion before municipal surcharge."""
    kw = DEFAULT_CONNECTED_LOAD_KW if connected_load_kw is None else connected_load_kw
    if FIXED_CHARGE_MODE == "per_kw":
        return round(TOD_FIXED_PER_KW * float(kw), 2)
    return round(RESIDENTIAL_FIXED, 2)


def total_fixed_charge(connected_load_kw: float | None = None) -> float:
    """Residential fixed + municipal surcharge."""
    return round(
        residential_fixed_component(connected_load_kw) + MUNICIPAL_SURCHARGE, 2
    )


# Back-compat alias used by older call sites / UI totals
FIXED_CHARGE: float = total_fixed_charge()

_DIRECT = TARIFF.get("direct_charges", {})
WHEELING_RATE_PER_UNIT: float = float(_DIRECT.get("wheeling_rate_per_unit", 1.60))
WHEELING_NOTE: str = str(_DIRECT.get("wheeling_note", ""))
ELECTRICITY_DUTY_PERCENT: float = float(_DIRECT.get("electricity_duty_percent", 16.0))
ELECTRICITY_DUTY_NOTE: str = str(_DIRECT.get("electricity_duty_note", ""))
PROMPT_PAYMENT_DISCOUNT_PERCENT: float = float(
    _DIRECT.get("prompt_payment_discount_percent", 1.0)
)
PROMPT_PAYMENT_DISCOUNT_NOTE: str = str(
    _DIRECT.get("prompt_payment_discount_note", "")
)
AFTER_DUE_SURCHARGE: float = float(_DIRECT.get("after_due_surcharge", 50.0))
AFTER_DUE_SURCHARGE_NOTE: str = str(_DIRECT.get("after_due_surcharge_note", ""))
DIGITAL_PAYMENT_DISCOUNT: float = float(_DIRECT.get("digital_payment_discount", 0.0))
DIGITAL_PAYMENT_DISCOUNT_NOTE: str = str(
    _DIRECT.get("digital_payment_discount_note", "")
)

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
    _OTHER.get("include_security_deposit_by_default", False)
)
INCLUDE_DELAYED_PAYMENT_BY_DEFAULT: bool = bool(
    _OTHER.get("include_delayed_payment_by_default", False)
)
DEFAULT_NET_ADJUSTMENT: float = float(_OTHER.get("default_net_adjustment", 0.0))
DEFAULT_NET_ADJUSTMENT_NOTE: str = str(
    _OTHER.get("default_net_adjustment_note", "")
)

BILLS_DIR = "bills"
TARIFF_CONFIG_PATH = str(_CONFIG_PATH)

# ── Twilio WhatsApp Configuration ───────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")


def reload_tariff_config() -> None:
    """Reload tariff_config.json into module-level constants (for tests / hot reload)."""
    global TARIFF, TARIFF_NAME, TARIFF_DETAILS, TARIFF_ORDER, DUE_DAYS, PROMPT_DUE_DAYS
    global GST_PERCENT, SLABS
    global RESIDENTIAL_FIXED, RESIDENTIAL_FIXED_NOTE, FIXED_CHARGE_MODE
    global TOD_FIXED_PER_KW, DEFAULT_CONNECTED_LOAD_KW, TOD_FIXED_NOTE
    global MUNICIPAL_SURCHARGE, MUNICIPAL_SURCHARGE_NOTE, MUNICIPAL_SURCHARGE_EFFECTIVE_FROM
    global FIXED_CHARGE
    global WHEELING_RATE_PER_UNIT, WHEELING_NOTE
    global ELECTRICITY_DUTY_PERCENT, ELECTRICITY_DUTY_NOTE
    global PROMPT_PAYMENT_DISCOUNT_PERCENT, PROMPT_PAYMENT_DISCOUNT_NOTE
    global AFTER_DUE_SURCHARGE, AFTER_DUE_SURCHARGE_NOTE
    global DIGITAL_PAYMENT_DISCOUNT, DIGITAL_PAYMENT_DISCOUNT_NOTE
    global SECURITY_DEPOSIT_ARREARS, SECURITY_DEPOSIT_HELD, SECURITY_DEPOSIT_INTEREST
    global SECURITY_DEPOSIT_NOTE, DELAYED_PAYMENT_CHARGE, DELAYED_PAYMENT_CHARGE_AFTER
    global DELAYED_PAYMENT_EARLY_DEADLINE, DELAYED_PAYMENT_LATE_DEADLINE
    global DELAYED_PAYMENT_NOTE, INCLUDE_SECURITY_DEPOSIT_BY_DEFAULT
    global INCLUDE_DELAYED_PAYMENT_BY_DEFAULT
    global DEFAULT_NET_ADJUSTMENT, DEFAULT_NET_ADJUSTMENT_NOTE

    TARIFF = _load_tariff_config()
    TARIFF_NAME = TARIFF["tariff_name"]
    TARIFF_DETAILS = TARIFF.get("tariff_details", "")
    TARIFF_ORDER = TARIFF.get("tariff_order", "")
    DUE_DAYS = int(TARIFF.get("due_days", 20))
    PROMPT_DUE_DAYS = int(TARIFF.get("prompt_due_days", 10))
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
    RESIDENTIAL_FIXED = float(_fixed.get("residential_fixed", 130.0))
    RESIDENTIAL_FIXED_NOTE = str(_fixed.get("residential_fixed_note", ""))
    FIXED_CHARGE_MODE = str(_fixed.get("fixed_charge_mode", "flat")).lower()
    TOD_FIXED_PER_KW = float(_fixed.get("tod_per_kw", RESIDENTIAL_FIXED))
    DEFAULT_CONNECTED_LOAD_KW = float(_fixed.get("default_connected_load_kw", 4.0))
    TOD_FIXED_NOTE = str(_fixed.get("tod_note", ""))
    MUNICIPAL_SURCHARGE = float(_fixed["municipal_surcharge"])
    MUNICIPAL_SURCHARGE_NOTE = str(_fixed.get("municipal_surcharge_note", ""))
    MUNICIPAL_SURCHARGE_EFFECTIVE_FROM = str(
        _fixed.get("municipal_surcharge_effective_from", "")
    )
    FIXED_CHARGE = total_fixed_charge()
    _direct = TARIFF.get("direct_charges", {})
    WHEELING_RATE_PER_UNIT = float(_direct.get("wheeling_rate_per_unit", 1.60))
    WHEELING_NOTE = str(_direct.get("wheeling_note", ""))
    ELECTRICITY_DUTY_PERCENT = float(_direct.get("electricity_duty_percent", 16.0))
    ELECTRICITY_DUTY_NOTE = str(_direct.get("electricity_duty_note", ""))
    PROMPT_PAYMENT_DISCOUNT_PERCENT = float(
        _direct.get("prompt_payment_discount_percent", 1.0)
    )
    PROMPT_PAYMENT_DISCOUNT_NOTE = str(
        _direct.get("prompt_payment_discount_note", "")
    )
    AFTER_DUE_SURCHARGE = float(_direct.get("after_due_surcharge", 50.0))
    AFTER_DUE_SURCHARGE_NOTE = str(_direct.get("after_due_surcharge_note", ""))
    DIGITAL_PAYMENT_DISCOUNT = float(_direct.get("digital_payment_discount", 0.0))
    DIGITAL_PAYMENT_DISCOUNT_NOTE = str(
        _direct.get("digital_payment_discount_note", "")
    )
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
        _other.get("include_security_deposit_by_default", False)
    )
    INCLUDE_DELAYED_PAYMENT_BY_DEFAULT = bool(
        _other.get("include_delayed_payment_by_default", False)
    )
    DEFAULT_NET_ADJUSTMENT = float(_other.get("default_net_adjustment", 0.0))
    DEFAULT_NET_ADJUSTMENT_NOTE = str(
        _other.get("default_net_adjustment_note", "")
    )
