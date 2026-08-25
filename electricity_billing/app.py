"""Streamlit frontend for the Electricity Bill Calculator & WhatsApp Billing System."""

from __future__ import annotations

import os

import streamlit as st

from bill_calculator import calculate_bill
from bill_generator import save_bill_txt, save_bill_pdf
from billing_config import (
    SLABS,
    TARIFF_NAME,
    TARIFF_ORDER,
    TARIFF_CONFIG_PATH,
    TOD_FIXED_PER_KW,
    TOD_FIXED_NOTE,
    DEFAULT_CONNECTED_LOAD_KW,
    MUNICIPAL_SURCHARGE,
    MUNICIPAL_SURCHARGE_NOTE,
    MUNICIPAL_SURCHARGE_EFFECTIVE_FROM,
    SECURITY_DEPOSIT_ARREARS,
    SECURITY_DEPOSIT_HELD,
    SECURITY_DEPOSIT_INTEREST,
    SECURITY_DEPOSIT_NOTE,
    DELAYED_PAYMENT_CHARGE,
    DELAYED_PAYMENT_CHARGE_AFTER,
    DELAYED_PAYMENT_EARLY_DEADLINE,
    DELAYED_PAYMENT_LATE_DEADLINE,
    DELAYED_PAYMENT_NOTE,
    INCLUDE_SECURITY_DEPOSIT_BY_DEFAULT,
    INCLUDE_DELAYED_PAYMENT_BY_DEFAULT,
)
from database import (
    bill_number_exists,
    get_all_bills,
    get_bill_by_no,
    get_bill_stats,
    search_bills,
    suggest_next_bill_number,
)

st.set_page_config(
    page_title="Electricity Bill Calculator",
    page_icon="⚡",
    layout="wide",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .main-header h1 { margin: 0; font-size: 2.2rem; }
    .main-header p  { margin: 0.5rem 0 0; opacity: 0.9; font-size: 1.1rem; }

    .metric-card {
        background: #f8f9fa;
        border-left: 4px solid #0f766e;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 0.8rem;
    }
    .metric-card .label { font-size: 0.85rem; color: #666; margin: 0; }
    .metric-card .value { font-size: 1.4rem; font-weight: 700; color: #1a1a2e; margin: 0; }

    .total-card {
        background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        color: white;
        margin-top: 1rem;
    }
    .total-card .label { font-size: 1rem; opacity: 0.9; margin: 0; }
    .total-card .value { font-size: 2.2rem; font-weight: 700; margin: 0.3rem 0 0; }

    .slab-table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
    .slab-table th {
        background: #0f766e; color: white; padding: 10px 14px;
        text-align: left; font-size: 0.85rem;
    }
    .slab-table th:first-child { border-radius: 8px 0 0 0; }
    .slab-table th:last-child  { border-radius: 0 8px 0 0; }
    .slab-table td { padding: 10px 14px; border-bottom: 1px solid #eee; font-size: 0.85rem; }
    .slab-table tr:last-child td { border-bottom: none; }
    .slab-table tr:hover td { background: #f0fdfa; }

    .rate-badge {
        display: inline-block;
        background: #ccfbf1;
        color: #115e59;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
    }

    .info-box {
        background: #f0fdfa;
        border: 1px solid #99f6e4;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        font-size: 0.85rem;
        color: #134e4a;
    }
    .note-line { font-size: 0.75rem; color: #64748b; margin: 0.15rem 0 0.6rem; }
</style>
""", unsafe_allow_html=True)


# ── Header ──────────────────────────────────────────────────────────────────────
order_line = f" &mdash; {TARIFF_ORDER}" if TARIFF_ORDER else ""
st.markdown(f"""
<div class="main-header">
    <h1>⚡ Electricity Bill Calculator</h1>
    <p>{TARIFF_NAME}{order_line}</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar: Tariff Info ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 📋 Tariff Card — {TARIFF_NAME}")
    st.caption(os.path.basename(TARIFF_CONFIG_PATH))

    slab_rows = ""
    for up_to, energy_rate, fac_rate, label in SLABS:
        range_txt = label if up_to is None else label
        slab_rows += (
            f"<tr>"
            f"<td>{range_txt}</td>"
            f"<td><span class='rate-badge'>₹{energy_rate:.2f}</span></td>"
            f"<td><span class='rate-badge'>₹{fac_rate:.3f}</span></td>"
            f"</tr>"
        )

    st.markdown(f"""
    <table class="slab-table">
        <tr><th>Units slab</th><th>Energy ₹/unit</th><th>FAC ₹/unit</th></tr>
        {slab_rows}
    </table>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Fixed Charges** *(not linked to consumption)*")
    total_fixed_default = TOD_FIXED_PER_KW * DEFAULT_CONNECTED_LOAD_KW + MUNICIPAL_SURCHARGE
    st.markdown(f"""
    <div class="info-box">
        Fixed charge (TOD): <b>₹{TOD_FIXED_PER_KW:.2f}/kW/month</b><br>
        <span class="note-line">{TOD_FIXED_NOTE}</span><br>
        Municipal corporation surcharge: <b>₹{MUNICIPAL_SURCHARGE:.2f}/month</b><br>
        <span class="note-line">{MUNICIPAL_SURCHARGE_NOTE}</span>
        {f'<br>Effective from: <b>{MUNICIPAL_SURCHARGE_EFFECTIVE_FROM}</b><br>' if MUNICIPAL_SURCHARGE_EFFECTIVE_FROM else '<br>'}
        Total fixed (at {DEFAULT_CONNECTED_LOAD_KW:g} kW): <b>₹{total_fixed_default:.2f}</b><br>
        <span class="note-line">Payable even at zero consumption</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Other Charges**")
    st.markdown(f"""
    <div class="info-box">
        Security deposit arrears: <b>₹{SECURITY_DEPOSIT_ARREARS:,.2f}</b><br>
        <span class="note-line">{SECURITY_DEPOSIT_NOTE or f'Outstanding SD (₹{SECURITY_DEPOSIT_HELD:,.2f} held); interest ₹{SECURITY_DEPOSIT_INTEREST:.2f}'}</span><br>
        Delayed payment charge: <b>₹{DELAYED_PAYMENT_CHARGE:.2f}</b>
        {f' → ₹{DELAYED_PAYMENT_CHARGE_AFTER:.2f} after {DELAYED_PAYMENT_LATE_DEADLINE}' if DELAYED_PAYMENT_CHARGE_AFTER else ''}<br>
        <span class="note-line">{DELAYED_PAYMENT_NOTE or (f'₹{DELAYED_PAYMENT_CHARGE:.0f} by {DELAYED_PAYMENT_EARLY_DEADLINE}' if DELAYED_PAYMENT_EARLY_DEADLINE else '')}</span>
    </div>
    """, unsafe_allow_html=True)


# ── Tabs ────────────────────────────────────────────────────────────────────────
tab_calc, tab_history = st.tabs(["🧮 Calculate Bill", "📂 Bill History"])

# ────────────────────────────────────────────────────────────────────────────────
# TAB 1: Calculator
# ────────────────────────────────────────────────────────────────────────────────
with tab_calc:
    col_form, col_result = st.columns([1, 1.4], gap="large")

    with col_form:
        st.markdown("### 📝 Customer Details")

        # Apply next suggested number after a successful save (must run before widget)
        if "_pending_bill_no" in st.session_state:
            st.session_state["bill_no_input"] = st.session_state.pop("_pending_bill_no")
        if "bill_no_input" not in st.session_state:
            st.session_state["bill_no_input"] = suggest_next_bill_number()

        bill_no_input = st.text_input(
            "Bill Number",
            help="Pre-filled from the database sequence. Change it if needed — must be unique.",
            key="bill_no_input",
        )
        if bill_no_input.strip():
            if bill_number_exists(bill_no_input.strip()):
                existing = get_bill_by_no(bill_no_input.strip())
                st.warning(
                    f"Bill **{bill_no_input.strip()}** already exists in DB"
                    + (
                        f" for **{existing['customer_name']}**"
                        f" (₹{existing['total']:,.2f})"
                        if existing
                        else ""
                    )
                    + ". Choose a different number."
                )
            else:
                st.caption("Available — will be saved against this bill in the database.")

        name = st.text_input("Customer Name", placeholder="e.g. Rahul Sharma")
        phone = st.text_input("Phone Number", placeholder="e.g. +919876543210")
        units = st.number_input(
            "Units Consumed (kWh)", min_value=0, max_value=99999, value=0, step=1
        )
        connected_kw = st.number_input(
            "Connected Load (kW)",
            min_value=0.0,
            max_value=100.0,
            value=float(DEFAULT_CONNECTED_LOAD_KW),
            step=0.5,
            help=f"TOD fixed = ₹{TOD_FIXED_PER_KW:.0f} × connected load (kW)",
        )

        st.markdown("#### Optional bill items")
        include_sd = st.checkbox(
            f"Include Security Deposit Arrears (₹{SECURITY_DEPOSIT_ARREARS:,.2f})",
            value=INCLUDE_SECURITY_DEPOSIT_BY_DEFAULT,
        )
        include_dpc = st.checkbox(
            f"Include Delayed Payment Charge (₹{DELAYED_PAYMENT_CHARGE:.2f})",
            value=INCLUDE_DELAYED_PAYMENT_BY_DEFAULT,
        )

        st.markdown("---")
        generate = st.button("⚡ Generate Bill", type="primary", use_container_width=True)

    with col_result:
        if generate:
            entered_bill_no = (bill_no_input or "").strip()
            if not entered_bill_no:
                st.error("Please enter a bill number.")
            elif bill_number_exists(entered_bill_no):
                st.error(
                    f"Bill number **{entered_bill_no}** already exists in the database. "
                    "Enter a unique bill number."
                )
            elif not name:
                st.error("Please enter the customer name.")
            elif not phone:
                st.error("Please enter the phone number.")
            elif units < 0:
                st.error("Units consumed cannot be negative.")
            else:
                bill = calculate_bill(
                    name,
                    phone,
                    units,
                    connected_load_kw=connected_kw,
                    include_security_deposit=include_sd,
                    include_delayed_payment=include_dpc,
                    bill_no=entered_bill_no,
                )

                st.markdown(f"### 📊 Bill Summary — `{bill.bill_no}`")

                slab_html = ""
                for s in bill.slab_details:
                    slab_html += (
                        f"<tr>"
                        f"<td>{s.slab_label.split(' @ ')[0]}</td>"
                        f"<td style='text-align:center'>{s.units}</td>"
                        f"<td style='text-align:center'>₹{s.energy_rate:.2f}</td>"
                        f"<td style='text-align:center'>₹{s.fac_rate:.3f}</td>"
                        f"<td style='text-align:right'><b>₹{s.amount:.2f}</b></td>"
                        f"</tr>"
                    )

                st.markdown(f"""
                <table class="slab-table">
                    <tr>
                        <th>Slab</th><th>Units</th>
                        <th>Energy</th><th>FAC</th>
                        <th style="text-align:right">Amount</th>
                    </tr>
                    {slab_html}
                </table>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">Bill Number</p>
                        <p class="value" style="font-size:1.1rem">{bill.bill_no}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">Energy Charge</p>
                        <p class="value">₹{bill.energy_charge:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">FAC Charge</p>
                        <p class="value">₹{bill.fac_charge:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">Fixed Charge (TOD)</p>
                        <p class="value">₹{bill.tod_fixed_charge:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)

                with c2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">Municipal Surcharge</p>
                        <p class="value">₹{bill.municipal_surcharge:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">Total Fixed Charge</p>
                        <p class="value">₹{bill.fixed_charge:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if bill.security_deposit_arrears > 0:
                        st.markdown(f"""
                        <div class="metric-card">
                            <p class="label">Security Deposit Arrears</p>
                            <p class="value">₹{bill.security_deposit_arrears:,.2f}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    if bill.delayed_payment_charge > 0:
                        st.markdown(f"""
                        <div class="metric-card">
                            <p class="label">Delayed Payment Charge</p>
                            <p class="value">₹{bill.delayed_payment_charge:,.2f}</p>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="total-card">
                    <p class="label">Total Amount Payable</p>
                    <p class="value">₹{bill.total:,.2f}</p>
                    <p style="margin-top:0.6rem;font-size:0.95rem;opacity:0.9;">
                        Bill No: <b>{bill.bill_no}</b>
                        &nbsp;|&nbsp; Due Date: <b>{bill.due_date}</b>
                        &nbsp;|&nbsp; Load: <b>{bill.connected_load_kw:g} kW</b>
                    </p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                try:
                    bill_no_txt, txt_path, bill_text = save_bill_txt(
                        bill, bill_no=bill.bill_no
                    )
                except ValueError as exc:
                    st.error(str(exc))
                    st.stop()

                try:
                    _, pdf_path = save_bill_pdf(bill, bill_no=bill.bill_no)
                    pdf_generated = True
                except Exception as exc:
                    pdf_generated = False
                    pdf_path = ""
                    st.warning(f"PDF generation skipped: {exc}")

                st.session_state["last_bill"] = bill
                st.session_state["last_bill_no"] = bill.bill_no
                st.session_state["_pending_bill_no"] = suggest_next_bill_number()

                dl1, dl2 = st.columns(2)
                with dl1:
                    st.download_button(
                        f"📄 Download TXT ({bill.bill_no})",
                        data=bill_text,
                        file_name=f"{bill_no_txt}.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
                with dl2:
                    if pdf_generated:
                        with open(pdf_path, "rb") as pf:
                            pdf_bytes = pf.read()
                        st.download_button(
                            f"📑 Download PDF ({bill.bill_no})",
                            data=pdf_bytes,
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            use_container_width=True,
                        )

                st.success(
                    f"Bill **{bill.bill_no}** saved to database for **{name}**"
                )

                st.markdown("---")
                st.markdown(f"### 📲 Send via WhatsApp — Bill `{bill.bill_no}`")

                from whatsapp_sender import (
                    is_twilio_configured, send_bill_twilio,
                    get_whatsapp_url,
                )

                if is_twilio_configured():
                    st.markdown(
                        '<div class="info-box">Twilio is configured — '
                        "the PDF bill will be sent as an attachment.</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        f"📲 Send Bill {bill.bill_no} + PDF on WhatsApp",
                        type="primary",
                        use_container_width=True,
                    ):
                        target_pdf = pdf_path if pdf_generated else ""
                        if not target_pdf:
                            st.error("PDF was not generated. Cannot attach.")
                        else:
                            with st.spinner("Uploading PDF & sending via Twilio..."):
                                try:
                                    result = send_bill_twilio(
                                        bill, bill.bill_no, target_pdf,
                                    )
                                    st.success(f"WhatsApp message with PDF sent! {result}")
                                except Exception as exc:
                                    st.error(f"Twilio send failed: {exc}")
                else:
                    wa_url = get_whatsapp_url(bill, bill.bill_no)
                    st.markdown(
                        f'<a href="{wa_url}" target="_blank" style="'
                        f"display:inline-block;width:100%;text-align:center;"
                        f"background:#25D366;color:white;padding:0.75rem 1.5rem;"
                        f"border-radius:8px;font-size:1.1rem;font-weight:600;"
                        f'text-decoration:none;">'
                        f"📲 Send Bill {bill.bill_no} on WhatsApp</a>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        "This opens WhatsApp Web with the text message pre-filled. "
                        "To send the **PDF as an attachment**, configure Twilio "
                        "credentials in `billing_config.py`."
                    )
        else:
            st.markdown("""
            <div style="text-align:center; padding:4rem 2rem; color:#999;">
                <p style="font-size:3rem;">⚡</p>
                <p style="font-size:1.1rem;">Enter customer details and click <b>Generate Bill</b> to see the breakdown.</p>
            </div>
            """, unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────────────────────
# TAB 2: Bill History (from SQLite database)
# ────────────────────────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📂 Bill History (Database)")

    stats = get_bill_stats()
    if stats["total_bills"] == 0:
        st.info("No bills generated yet. Create your first bill above.")
    else:
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.metric("Total Bills", stats["total_bills"])
        with s2:
            st.metric("Total Revenue", f"₹{stats['total_revenue']:,.2f}")
        with s3:
            st.metric("Avg Bill", f"₹{stats['avg_bill']:,.2f}")
        with s4:
            st.metric("Total Units Sold", f"{stats['total_units']:,} kWh")

        st.markdown("---")

        search_col1, search_col2, search_col3 = st.columns(3)
        with search_col1:
            search_bill_no = st.text_input(
                "Search by bill number",
                placeholder="e.g. EB-20260825",
                key="search_bill_no",
            )
        with search_col2:
            search_name = st.text_input(
                "Search by customer name", placeholder="e.g. Rahul", key="search_name"
            )
        with search_col3:
            search_phone = st.text_input(
                "Search by phone", placeholder="e.g. 9876", key="search_phone"
            )

        if search_bill_no or search_name or search_phone:
            bills = search_bills(
                customer_name=search_name,
                phone=search_phone,
                bill_no=search_bill_no,
            )
            st.caption(f"Found **{len(bills)}** matching bill(s)")
        else:
            bills = get_all_bills()

        # Exact bill-number lookup panel
        if search_bill_no and search_bill_no.strip():
            exact = get_bill_by_no(search_bill_no.strip())
            if exact:
                st.info(
                    f"Exact DB match: **{exact['bill_no']}** — "
                    f"{exact['customer_name']} — ₹{exact['total']:,.2f} "
                    f"(due {exact['due_date']})"
                )

        if bills:
            import pandas as pd
            df = pd.DataFrame(bills)
            display_cols = [
                "bill_no", "created_at", "due_date", "customer_name",
                "phone", "units_consumed", "energy_charge", "fac_charge",
                "fixed_charge", "total", "whatsapp_sent",
            ]
            df_display = df[[c for c in display_cols if c in df.columns]].copy()
            df_display["whatsapp_sent"] = df_display["whatsapp_sent"].map(
                {1: "Yes", 0: "No"}
            )
            rename = {
                "bill_no": "Bill No",
                "created_at": "Created",
                "due_date": "Due Date",
                "customer_name": "Customer",
                "phone": "Phone",
                "units_consumed": "Units (kWh)",
                "energy_charge": "Energy (Rs.)",
                "fac_charge": "FAC (Rs.)",
                "fixed_charge": "Fixed (Rs.)",
                "total": "Total (Rs.)",
                "whatsapp_sent": "WA Sent",
            }
            df_display = df_display.rename(columns=rename)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### Bill Details")
            for b in bills:
                wa_badge = " ✅" if b["whatsapp_sent"] else ""
                with st.expander(
                    f"📄 {b['bill_no']}  —  {b['customer_name']}  —  "
                    f"Rs.{b['total']:,.2f}{wa_badge}"
                ):
                    dc0, dc1, dc2, dc3 = st.columns(4)
                    with dc0:
                        st.markdown(f"""
                        <div class="metric-card">
                            <p class="label">Bill Number</p>
                            <p class="value" style="font-size:1rem">{b['bill_no']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with dc1:
                        st.markdown(f"""
                        <div class="metric-card">
                            <p class="label">Created</p>
                            <p class="value" style="font-size:1rem">{b['created_at']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with dc2:
                        st.markdown(f"""
                        <div class="metric-card">
                            <p class="label">Due Date</p>
                            <p class="value" style="font-size:1rem">{b['due_date']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with dc3:
                        st.markdown(f"""
                        <div class="metric-card">
                            <p class="label">Units Consumed</p>
                            <p class="value">{b['units_consumed']} kWh</p>
                        </div>
                        """, unsafe_allow_html=True)

                    fac = b.get("fac_charge") or 0
                    tod = b.get("tod_fixed_charge") or 0
                    muni = b.get("municipal_surcharge") or 0
                    sd = b.get("security_deposit_arrears") or 0
                    dpc = b.get("delayed_payment_charge") or 0
                    st.markdown(
                        f"**Energy:** Rs.{b['energy_charge']:,.2f} &nbsp;|&nbsp; "
                        f"**FAC:** Rs.{fac:,.2f} &nbsp;|&nbsp; "
                        f"**TOD Fixed:** Rs.{tod:,.2f} &nbsp;|&nbsp; "
                        f"**Municipal:** Rs.{muni:,.2f} &nbsp;|&nbsp; "
                        f"**SD Arrears:** Rs.{sd:,.2f} &nbsp;|&nbsp; "
                        f"**DPC:** Rs.{dpc:,.2f} &nbsp;|&nbsp; "
                        f"**Total: Rs.{b['total']:,.2f}**"
                    )

                    fdl1, fdl2 = st.columns(2)
                    with fdl1:
                        if b["txt_path"] and os.path.exists(b["txt_path"]):
                            with open(b["txt_path"], encoding="utf-8") as tf:
                                st.download_button(
                                    "📄 Download TXT",
                                    data=tf.read(),
                                    file_name=os.path.basename(b["txt_path"]),
                                    mime="text/plain",
                                    key=f"db_txt_{b['bill_no']}",
                                )
                    with fdl2:
                        if b["pdf_path"] and os.path.exists(b["pdf_path"]):
                            with open(b["pdf_path"], "rb") as pf:
                                st.download_button(
                                    "📑 Download PDF",
                                    data=pf.read(),
                                    file_name=os.path.basename(b["pdf_path"]),
                                    mime="application/pdf",
                                    key=f"db_pdf_{b['bill_no']}",
                                )
