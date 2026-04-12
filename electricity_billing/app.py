"""Streamlit frontend for the Electricity Bill Calculator & WhatsApp Billing System."""

import os
import base64
from datetime import datetime

import streamlit as st

from bill_calculator import calculate_bill, BillResult
from bill_generator import save_bill_txt, save_bill_pdf
from billing_config import (
    SLABS, DEFAULT_RATE, FIXED_CHARGE, METER_RENT,
    ELECTRICITY_DUTY_PERCENT, BILLS_DIR,
)
from database import get_all_bills, get_bill_stats, search_bills

st.set_page_config(
    page_title="Electricity Bill Calculator",
    page_icon="⚡",
    layout="wide",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
        border-left: 4px solid #667eea;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 0.8rem;
    }
    .metric-card .label { font-size: 0.85rem; color: #666; margin: 0; }
    .metric-card .value { font-size: 1.4rem; font-weight: 700; color: #1a1a2e; margin: 0; }

    .total-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
        background: #667eea; color: white; padding: 10px 14px;
        text-align: left; font-size: 0.9rem;
    }
    .slab-table th:first-child { border-radius: 8px 0 0 0; }
    .slab-table th:last-child  { border-radius: 0 8px 0 0; }
    .slab-table td { padding: 10px 14px; border-bottom: 1px solid #eee; font-size: 0.9rem; }
    .slab-table tr:last-child td { border-bottom: none; }
    .slab-table tr:hover td { background: #f5f3ff; }

    .rate-badge {
        display: inline-block;
        background: #e8e0ff;
        color: #5b21b6;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    .info-box {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #1e40af;
    }
</style>
""", unsafe_allow_html=True)


# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>⚡ Electricity Bill Calculator</h1>
    <p>2026 Residential Tariff &mdash; Generate &amp; Send Bills via WhatsApp</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar: Tariff Info ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 2026 Tariff Card")

    slab_rows = ""
    lower = 0
    for width, rate in SLABS:
        upper = lower + width
        slab_rows += f"<tr><td>{lower + 1} - {upper} kWh</td><td><span class='rate-badge'>₹{rate}</span></td></tr>"
        lower = upper
    slab_rows += f"<tr><td>Above {lower} kWh</td><td><span class='rate-badge'>₹{DEFAULT_RATE}</span></td></tr>"

    st.markdown(f"""
    <table class="slab-table">
        <tr><th>Slab Range</th><th>Rate / Unit</th></tr>
        {slab_rows}
    </table>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Other Charges**")
    st.markdown(f"""
    <div class="info-box">
        Fixed Charge: <b>₹{FIXED_CHARGE:.0f}/month</b><br>
        Meter Rent: <b>₹{METER_RENT:.0f}/month</b><br>
        Electricity Duty: <b>{ELECTRICITY_DUTY_PERCENT:.0f}%</b> on energy charges
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

        name = st.text_input("Customer Name", placeholder="e.g. Rahul Sharma")
        phone = st.text_input("Phone Number", placeholder="e.g. +919876543210")
        units = st.number_input(
            "Units Consumed (kWh)", min_value=0, max_value=99999, value=0, step=1
        )

        st.markdown("---")
        generate = st.button("⚡ Generate Bill", type="primary", use_container_width=True)

    with col_result:
        if generate:
            if not name:
                st.error("Please enter the customer name.")
            elif not phone:
                st.error("Please enter the phone number.")
            elif units <= 0:
                st.error("Units consumed must be greater than zero.")
            else:
                bill = calculate_bill(name, phone, units)

                st.markdown("### 📊 Bill Summary")

                # Slab breakdown
                slab_html = ""
                for s in bill.slab_details:
                    slab_html += (
                        f"<tr>"
                        f"<td>{s.slab_label}</td>"
                        f"<td style='text-align:center'>{s.units}</td>"
                        f"<td style='text-align:center'>₹{s.rate:.2f}</td>"
                        f"<td style='text-align:right'><b>₹{s.amount:.2f}</b></td>"
                        f"</tr>"
                    )

                st.markdown(f"""
                <table class="slab-table">
                    <tr><th>Slab</th><th>Units</th><th>Rate</th><th style="text-align:right">Amount</th></tr>
                    {slab_html}
                </table>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Charge cards
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">Energy Charge</p>
                        <p class="value">₹{bill.energy_charge:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">Fixed Charge</p>
                        <p class="value">₹{bill.fixed_charge:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)

                with c2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">Meter Rent</p>
                        <p class="value">₹{bill.meter_rent:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="metric-card">
                        <p class="label">Electricity Duty ({bill.electricity_duty_percent:.0f}%)</p>
                        <p class="value">₹{bill.electricity_duty:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)

                # Total + Due Date
                st.markdown(f"""
                <div class="total-card">
                    <p class="label">Total Amount Payable</p>
                    <p class="value">₹{bill.total:,.2f}</p>
                    <p style="margin-top:0.6rem;font-size:0.95rem;opacity:0.9;">
                        Due Date: <b>{bill.due_date}</b>
                    </p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Save files
                bill_no_txt, txt_path, bill_text = save_bill_txt(bill)
                try:
                    _, pdf_path = save_bill_pdf(bill, bill_no_txt)
                    pdf_generated = True
                except Exception:
                    pdf_generated = False
                    pdf_path = ""

                st.session_state["last_bill"] = bill
                st.session_state["last_bill_no"] = bill_no_txt

                # Download buttons
                dl1, dl2 = st.columns(2)
                with dl1:
                    st.download_button(
                        "📄 Download TXT",
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
                            "📑 Download PDF",
                            data=pdf_bytes,
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            use_container_width=True,
                        )

                st.success(f"Bill **{bill_no_txt}** generated for **{name}**")

                # WhatsApp section
                st.markdown("---")
                st.markdown("### 📲 Send via WhatsApp")

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
                        "📲 Send Bill + PDF on WhatsApp",
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
                                        bill, bill_no_txt, target_pdf,
                                    )
                                    st.success(f"WhatsApp message with PDF sent! {result}")
                                except Exception as exc:
                                    st.error(f"Twilio send failed: {exc}")
                else:
                    wa_url = get_whatsapp_url(bill, bill_no_txt)
                    st.markdown(
                        f'<a href="{wa_url}" target="_blank" style="'
                        f"display:inline-block;width:100%;text-align:center;"
                        f"background:#25D366;color:white;padding:0.75rem 1.5rem;"
                        f"border-radius:8px;font-size:1.1rem;font-weight:600;"
                        f'text-decoration:none;">📲 Send Bill on WhatsApp</a>',
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

    # Dashboard stats
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

        # Search
        search_col1, search_col2 = st.columns(2)
        with search_col1:
            search_name = st.text_input(
                "Search by customer name", placeholder="e.g. Rahul", key="search_name"
            )
        with search_col2:
            search_phone = st.text_input(
                "Search by phone", placeholder="e.g. 9876", key="search_phone"
            )

        if search_name or search_phone:
            bills = search_bills(customer_name=search_name, phone=search_phone)
            st.caption(f"Found **{len(bills)}** matching bill(s)")
        else:
            bills = get_all_bills()

        if bills:
            import pandas as pd
            df = pd.DataFrame(bills)
            display_cols = [
                "bill_no", "created_at", "due_date", "customer_name",
                "phone", "units_consumed", "energy_charge", "total",
                "whatsapp_sent",
            ]
            df_display = df[[c for c in display_cols if c in df.columns]].copy()
            df_display["whatsapp_sent"] = df_display["whatsapp_sent"].map(
                {1: "Yes", 0: "No"}
            )
            df_display.columns = [
                "Bill No", "Created", "Due Date", "Customer",
                "Phone", "Units (kWh)", "Energy (Rs.)", "Total (Rs.)",
                "WA Sent",
            ]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # Expandable detail for each bill
            st.markdown("---")
            st.markdown("#### Bill Details")
            for b in bills:
                wa_badge = " ✅" if b["whatsapp_sent"] else ""
                with st.expander(
                    f"📄 {b['bill_no']}  —  {b['customer_name']}  —  "
                    f"Rs.{b['total']:,.2f}{wa_badge}"
                ):
                    dc1, dc2, dc3 = st.columns(3)
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

                    st.markdown(
                        f"**Energy:** Rs.{b['energy_charge']:,.2f} &nbsp;|&nbsp; "
                        f"**Fixed:** Rs.{b['fixed_charge']:,.2f} &nbsp;|&nbsp; "
                        f"**Meter Rent:** Rs.{b['meter_rent']:,.2f} &nbsp;|&nbsp; "
                        f"**Elec. Duty:** Rs.{b['electricity_duty']:,.2f} &nbsp;|&nbsp; "
                        f"**Total: Rs.{b['total']:,.2f}**"
                    )

                    # Download buttons
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
