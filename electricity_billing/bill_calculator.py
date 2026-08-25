"""Slab-based electricity bill calculation engine (LT-I Residential Tariff)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from billing_config import (
    SLABS,
    TOD_FIXED_PER_KW,
    DEFAULT_CONNECTED_LOAD_KW,
    MUNICIPAL_SURCHARGE,
    SECURITY_DEPOSIT_ARREARS,
    DELAYED_PAYMENT_CHARGE,
    INCLUDE_SECURITY_DEPOSIT_BY_DEFAULT,
    INCLUDE_DELAYED_PAYMENT_BY_DEFAULT,
    GST_PERCENT,
    DUE_DAYS,
)


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
    bill_date: str = ""
    due_date: str = ""
    slab_details: list[SlabBreakdown] = field(default_factory=list)
    energy_charge: float = 0.0
    fac_charge: float = 0.0
    tod_fixed_charge: float = 0.0
    municipal_surcharge: float = 0.0
    fixed_charge: float = 0.0  # tod + municipal
    security_deposit_arrears: float = 0.0
    delayed_payment_charge: float = 0.0
    gst_percent: float = 0.0
    gst_amount: float = 0.0
    subtotal: float = 0.0
    total: float = 0.0

    # Legacy aliases kept for older DB / display code paths
    @property
    def meter_rent(self) -> float:
        return 0.0

    @property
    def electricity_duty_percent(self) -> float:
        return 0.0

    @property
    def electricity_duty(self) -> float:
        return 0.0


def calculate_bill(
    customer_name: str,
    phone: str,
    units: int,
    connected_load_kw: float | None = None,
    include_security_deposit: bool | None = None,
    include_delayed_payment: bool | None = None,
    security_deposit_arrears: float | None = None,
    delayed_payment_charge: float | None = None,
    bill_no: str = "",
) -> BillResult:
    """Calculate electricity bill using LT-I Residential slab rates + FAC."""
    if units < 0:
        raise ValueError("Units consumed cannot be negative")

    kw = DEFAULT_CONNECTED_LOAD_KW if connected_load_kw is None else float(connected_load_kw)
    if kw < 0:
        raise ValueError("Connected load (kW) cannot be negative")

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

    sd_amount = (
        float(security_deposit_arrears)
        if security_deposit_arrears is not None
        else (SECURITY_DEPOSIT_ARREARS if apply_sd else 0.0)
    )
    if not apply_sd:
        sd_amount = 0.0

    dpc_amount = (
        float(delayed_payment_charge)
        if delayed_payment_charge is not None
        else (DELAYED_PAYMENT_CHARGE if apply_dpc else 0.0)
    )
    if not apply_dpc:
        dpc_amount = 0.0

    now = datetime.now()
    tod_fixed = round(TOD_FIXED_PER_KW * kw, 2)
    municipal = round(MUNICIPAL_SURCHARGE, 2)
    total_fixed = round(tod_fixed + municipal, 2)

    result = BillResult(
        customer_name=customer_name,
        phone=phone,
        units_consumed=units,
        bill_no=(bill_no or "").strip(),
        connected_load_kw=kw,
        bill_date=now.strftime("%d-%m-%Y"),
        due_date=(now + timedelta(days=DUE_DAYS)).strftime("%d-%m-%Y"),
        tod_fixed_charge=tod_fixed,
        municipal_surcharge=municipal,
        fixed_charge=total_fixed,
        security_deposit_arrears=round(sd_amount, 2),
        delayed_payment_charge=round(dpc_amount, 2),
        gst_percent=GST_PERCENT,
    )

    remaining = units
    prev_upper = 0

    for up_to, energy_rate, fac_rate, label in SLABS:
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

        energy_amount = round(slab_units * energy_rate, 2)
        fac_amount = round(slab_units * fac_rate, 2)
        amount = round(energy_amount + fac_amount, 2)
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

    result.energy_charge = round(result.energy_charge, 2)
    result.fac_charge = round(result.fac_charge, 2)
    result.subtotal = round(
        result.energy_charge
        + result.fac_charge
        + result.fixed_charge
        + result.security_deposit_arrears
        + result.delayed_payment_charge,
        2,
    )
    result.gst_amount = round(result.subtotal * GST_PERCENT / 100, 2)
    result.total = round(result.subtotal + result.gst_amount, 2)

    return result
