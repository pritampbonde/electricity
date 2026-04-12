"""Slab-based electricity bill calculation engine (2026 Residential Tariff)."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from billing_config import (
    SLABS, DEFAULT_RATE, FIXED_CHARGE, METER_RENT,
    ELECTRICITY_DUTY_PERCENT, GST_PERCENT,
)

DUE_DAYS = 15


@dataclass
class SlabBreakdown:
    slab_label: str
    units: int
    rate: float
    amount: float


@dataclass
class BillResult:
    customer_name: str
    phone: str
    units_consumed: int
    bill_date: str = ""
    due_date: str = ""
    slab_details: list[SlabBreakdown] = field(default_factory=list)
    energy_charge: float = 0.0
    fixed_charge: float = 0.0
    meter_rent: float = 0.0
    electricity_duty_percent: float = 0.0
    electricity_duty: float = 0.0
    gst_percent: float = 0.0
    gst_amount: float = 0.0
    subtotal: float = 0.0
    total: float = 0.0


def calculate_bill(
    customer_name: str,
    phone: str,
    units: int,
) -> BillResult:
    """Calculate electricity bill using 2026 residential slab rates."""
    if units < 0:
        raise ValueError("Units consumed cannot be negative")

    now = datetime.now()
    result = BillResult(
        customer_name=customer_name,
        phone=phone,
        units_consumed=units,
        bill_date=now.strftime("%d-%m-%Y"),
        due_date=(now + timedelta(days=DUE_DAYS)).strftime("%d-%m-%Y"),
        fixed_charge=FIXED_CHARGE,
        meter_rent=METER_RENT,
        electricity_duty_percent=ELECTRICITY_DUTY_PERCENT,
        gst_percent=GST_PERCENT,
    )

    remaining = units
    lower = 0

    for slab_width, rate in SLABS:
        if remaining <= 0:
            break
        slab_units = min(remaining, slab_width)
        upper = lower + slab_width
        label = f"{lower + 1}-{upper} units @ Rs.{rate}/unit"
        amount = round(slab_units * rate, 2)

        result.slab_details.append(
            SlabBreakdown(slab_label=label, units=slab_units, rate=rate, amount=amount)
        )
        result.energy_charge += amount
        remaining -= slab_units
        lower = upper

    if remaining > 0:
        label = f"Above {lower} units @ Rs.{DEFAULT_RATE}/unit"
        amount = round(remaining * DEFAULT_RATE, 2)
        result.slab_details.append(
            SlabBreakdown(slab_label=label, units=remaining, rate=DEFAULT_RATE, amount=amount)
        )
        result.energy_charge += amount

    result.energy_charge = round(result.energy_charge, 2)
    result.electricity_duty = round(result.energy_charge * ELECTRICITY_DUTY_PERCENT / 100, 2)
    result.subtotal = round(
        result.energy_charge + result.fixed_charge + result.meter_rent + result.electricity_duty, 2
    )
    result.gst_amount = round(result.subtotal * GST_PERCENT / 100, 2)
    result.total = round(result.subtotal + result.gst_amount, 2)

    return result
