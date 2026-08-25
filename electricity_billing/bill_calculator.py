"""MSEDCL LT-I Residential bill calculation engine.

Matches the official bill roll-up:
  Energy (slab) + FAC (slab) + Fixed + Wheeling + Electricity Duty
  → current bill → net adjustment → rounded payable
  → prompt / after-due amounts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from billing_config import (
    SLABS,
    DEFAULT_CONNECTED_LOAD_KW,
    MUNICIPAL_SURCHARGE,
    SECURITY_DEPOSIT_ARREARS,
    SECURITY_DEPOSIT_HELD,
    SECURITY_DEPOSIT_INTEREST,
    DELAYED_PAYMENT_CHARGE,
    INCLUDE_SECURITY_DEPOSIT_BY_DEFAULT,
    INCLUDE_DELAYED_PAYMENT_BY_DEFAULT,
    DEFAULT_NET_ADJUSTMENT,
    GST_PERCENT,
    DUE_DAYS,
    PROMPT_DUE_DAYS,
    WHEELING_RATE_PER_UNIT,
    ELECTRICITY_DUTY_PERCENT,
    PROMPT_PAYMENT_DISCOUNT_PERCENT,
    AFTER_DUE_SURCHARGE,
    DIGITAL_PAYMENT_DISCOUNT,
    residential_fixed_component,
)


def round_money(value: float) -> float:
    """Round to 2 decimal places (paise)."""
    return round(float(value) + 0.0, 2)


def round_payable_rupee(amount: float) -> float:
    """Round bill amount up to the next rupee when any paise remain (पूर्णांक देयक)."""
    amount = round_money(amount)
    whole = math.floor(amount)
    if round_money(amount - whole) == 0.0:
        return float(whole)
    return float(whole + 1)


def round_nearest_ten(amount: float) -> float:
    """Round to nearest ₹10 (used for prompt-payment payable on MSEDCL bills)."""
    return float(round(round_money(amount), -1))


@dataclass
class SlabBreakdown:
    slab_label: str
    units: int
    energy_rate: float
    fac_rate: float
    energy_amount: float
    fac_amount: float
    amount: float  # energy + FAC for this slab

    @property
    def rate(self) -> float:
        """Combined energy + FAC rate (for legacy display)."""
        return round(self.energy_rate + self.fac_rate, 3)


@dataclass
class BillResult:
    customer_name: str
    phone: str
    units_consumed: int
    bill_no: str = ""
    connected_load_kw: float = 1.0
    bill_month: int = 0
    bill_year: int = 0
    bill_date: str = ""
    prompt_due_date: str = ""
    due_date: str = ""
    slab_details: list[SlabBreakdown] = field(default_factory=list)

    # Core charges
    energy_charge: float = 0.0
    fac_charge: float = 0.0
    tod_fixed_charge: float = 0.0  # residential fixed component
    municipal_surcharge: float = 0.0
    fixed_charge: float = 0.0  # residential fixed + municipal
    wheeling_charge: float = 0.0
    wheeling_rate: float = 0.0

    # Duty / tax
    electricity_duty_percent: float = 0.0
    electricity_duty: float = 0.0
    duty_base: float = 0.0
    gst_percent: float = 0.0
    gst_amount: float = 0.0

    # Roll-up
    current_bill: float = 0.0
    interest: float = 0.0
    net_adjustment: float = 0.0
    net_amount: float = 0.0
    subtotal: float = 0.0  # alias of current_bill (pre-adjustment)
    total: float = 0.0  # rounded payable (पूर्णांक देयक)

    # Payable variants
    prompt_payment_discount: float = 0.0
    prompt_payable: float = 0.0
    after_due_payable: float = 0.0
    after_due_surcharge: float = 0.0
    digital_payment_discount: float = 0.0

    # Optional / footnote items
    security_deposit_arrears: float = 0.0
    security_deposit_held: float = 0.0
    security_deposit_interest: float = 0.0
    delayed_payment_charge: float = 0.0
    include_security_deposit_in_total: bool = False

    # Legacy alias
    @property
    def meter_rent(self) -> float:
        return 0.0

    @property
    def bill_period(self) -> str:
        """Human-readable bill month/year, e.g. 'May 2026'."""
        if not self.bill_month or not self.bill_year:
            return ""
        names = (
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        )
        if 1 <= self.bill_month <= 12:
            return f"{names[self.bill_month]} {self.bill_year}"
        return f"{self.bill_month}/{self.bill_year}"


def calculate_bill(
    customer_name: str,
    phone: str,
    units: int,
    connected_load_kw: float | None = None,
    include_security_deposit: bool | None = None,
    include_delayed_payment: bool | None = None,
    security_deposit_arrears: float | None = None,
    delayed_payment_charge: float | None = None,
    net_adjustment: float | None = None,
    bill_month: int | None = None,
    bill_year: int | None = None,
    bill_no: str = "",
) -> BillResult:
    """Calculate electricity bill using MSEDCL LT-I Residential rules."""
    if units < 0:
        raise ValueError("Units consumed cannot be negative")

    kw = DEFAULT_CONNECTED_LOAD_KW if connected_load_kw is None else float(connected_load_kw)
    if kw < 0:
        raise ValueError("Connected load (kW) cannot be negative")

    now = datetime.now()
    month = int(bill_month) if bill_month is not None else now.month
    year = int(bill_year) if bill_year is not None else now.year
    if month < 1 or month > 12:
        raise ValueError("Bill month must be between 1 and 12")
    if year < 2000 or year > 2100:
        raise ValueError("Bill year must be between 2000 and 2100")

    apply_sd = (
        INCLUDE_SECURITY_DEPOSIT_BY_DEFAULT
        if include_security_deposit is None
        else include_security_deposit
    )
    apply_dpc = (
        INCLUDE_DELAYED_PAYMENT_BY_DEFAULT
        if include_delayed_payment is None
        else include_delayed_payment
    )

    # Footnote SD arrears always come from config (or override); only optionally
    # added into the payable total when include_security_deposit is True.
    sd_footnote = (
        float(security_deposit_arrears)
        if security_deposit_arrears is not None
        else SECURITY_DEPOSIT_ARREARS
    )
    sd_in_total = round_money(sd_footnote) if apply_sd else 0.0

    dpc_amount = (
        float(delayed_payment_charge)
        if delayed_payment_charge is not None
        else (DELAYED_PAYMENT_CHARGE if apply_dpc else 0.0)
    )
    if not apply_dpc:
        dpc_amount = 0.0

    adj = (
        DEFAULT_NET_ADJUSTMENT
        if net_adjustment is None
        else float(net_adjustment)
    )

    residential_fixed = residential_fixed_component(kw)
    municipal = round_money(MUNICIPAL_SURCHARGE)
    total_fixed = round_money(residential_fixed + municipal)

    result = BillResult(
        customer_name=customer_name,
        phone=phone,
        units_consumed=units,
        bill_no=(bill_no or "").strip(),
        connected_load_kw=kw,
        bill_month=month,
        bill_year=year,
        bill_date=now.strftime("%d-%m-%Y"),
        prompt_due_date=(now + timedelta(days=PROMPT_DUE_DAYS)).strftime("%d-%m-%Y"),
        due_date=(now + timedelta(days=DUE_DAYS)).strftime("%d-%m-%Y"),
        tod_fixed_charge=residential_fixed,
        municipal_surcharge=municipal,
        fixed_charge=total_fixed,
        wheeling_rate=WHEELING_RATE_PER_UNIT,
        electricity_duty_percent=ELECTRICITY_DUTY_PERCENT,
        security_deposit_arrears=round_money(sd_footnote),
        security_deposit_held=round_money(SECURITY_DEPOSIT_HELD),
        security_deposit_interest=round_money(SECURITY_DEPOSIT_INTEREST),
        delayed_payment_charge=round_money(dpc_amount),
        include_security_deposit_in_total=apply_sd,
        digital_payment_discount=round_money(DIGITAL_PAYMENT_DISCOUNT),
        after_due_surcharge=round_money(AFTER_DUE_SURCHARGE),
        gst_percent=GST_PERCENT,
        net_adjustment=round_money(adj),
    )

    # ── Energy + FAC slabs ──────────────────────────────────────────────────
    remaining = units
    prev_upper = 0

    for up_to, energy_rate, fac_rate, _label in SLABS:
        if remaining <= 0:
            break

        if up_to is None:
            slab_units = remaining
            range_label = f"Above {prev_upper}"
        else:
            slab_capacity = up_to - prev_upper
            if slab_capacity <= 0:
                prev_upper = up_to
                continue
            slab_units = min(remaining, slab_capacity)
            range_label = f"{prev_upper + 1}-{up_to}" if prev_upper > 0 else f"0-{up_to}"
            prev_upper = up_to

        energy_amount = round_money(slab_units * energy_rate)
        fac_amount = round_money(slab_units * fac_rate)
        amount = round_money(energy_amount + fac_amount)
        display = (
            f"{range_label} units @ Rs.{energy_rate}/unit + FAC Rs.{fac_rate}/unit"
        )

        result.slab_details.append(
            SlabBreakdown(
                slab_label=display,
                units=slab_units,
                energy_rate=energy_rate,
                fac_rate=fac_rate,
                energy_amount=energy_amount,
                fac_amount=fac_amount,
                amount=amount,
            )
        )
        result.energy_charge += energy_amount
        result.fac_charge += fac_amount
        remaining -= slab_units

    result.energy_charge = round_money(result.energy_charge)
    result.fac_charge = round_money(result.fac_charge)

    # ── Direct / flat charges ───────────────────────────────────────────────
    result.wheeling_charge = round_money(units * WHEELING_RATE_PER_UNIT)
    result.duty_base = round_money(
        result.fixed_charge
        + result.energy_charge
        + result.wheeling_charge
        + result.fac_charge
    )
    result.electricity_duty = round_money(
        result.duty_base * ELECTRICITY_DUTY_PERCENT / 100.0
    )

    # ── Current bill roll-up ────────────────────────────────────────────────
    result.current_bill = round_money(
        result.duty_base
        + result.electricity_duty
        + result.delayed_payment_charge
    )
    if apply_sd and sd_in_total:
        result.current_bill = round_money(result.current_bill + sd_in_total)

    result.gst_amount = round_money(result.current_bill * GST_PERCENT / 100.0)
    result.current_bill = round_money(result.current_bill + result.gst_amount)
    result.subtotal = result.current_bill

    result.net_amount = round_money(
        result.current_bill + result.interest + result.net_adjustment
    )
    result.total = round_payable_rupee(result.net_amount)

    # ── Payable amounts on due dates ────────────────────────────────────────
    result.prompt_payment_discount = round_money(
        result.duty_base * PROMPT_PAYMENT_DISCOUNT_PERCENT / 100.0
    )
    result.prompt_payable = round_nearest_ten(
        result.total - result.prompt_payment_discount
    )
    result.after_due_payable = round_money(
        result.total + result.after_due_surcharge
    )

    return result
