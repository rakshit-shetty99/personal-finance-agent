import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.crud_service import (
    get_commitments, add_commitment, update_commitment, get_accounts
)

st.set_page_config(page_title="Commitments", page_icon="📋", layout="wide")
st.title("📋 Commitments")
st.caption("Every rupee you're committed to — EMIs, rent, subscriptions, one-time plans")

accounts = get_accounts()
banks = accounts[accounts["type"] == "bank"]
cards = accounts[accounts["type"] == "credit_card"]

# ------------------------- View ----------------------------------
df = get_commitments()

if df.empty:
    st.info("No commitments yet. Add your first one below — start with rent and EMIs.")
else:
    total_monthly = df[df["frequency"] == "monthly"]["amount"].fillna(0).sum()
    st.metric("Total Monthly Committed", f"₹{total_monthly:,.0f}")
    st.dataframe(
        df[["name", "type", "amount", "frequency", "due_day",
            "due_date", "end_date", "paid_from", "linked_card"]],
        use_container_width=True, hide_index=True,
    )

st.divider()

# ------------------------- Add -----------------------------------
st.subheader("➕ Add a Commitment")

ctype = st.selectbox(
    "Type",
    ["emi", "rent", "subscription", "cc_bill", "adhoc"],
    format_func=lambda x: {
        "emi": "EMI (loan repayment)",
        "rent": "Rent",
        "subscription": "Subscription (Netflix, gym...)",
        "cc_bill": "Credit card bill",
        "adhoc": "One-time commitment (travel, purchase...)",
    }[x],
)

with st.form("add_commitment", clear_on_submit=True):
    name = st.text_input("Name (e.g. 'Home Loan EMI', 'Netflix')")

    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Amount (₹) — leave 0 if variable", min_value=0.0, step=100.0)
        frequency = st.selectbox(
            "Frequency",
            ["monthly", "annual", "one_time"],
            index=2 if ctype == "adhoc" else 0,
        )
    with col2:
        due_day = st.number_input("Due day of month (recurring; 0 = N/A)", 0, 31, 0)
        due_date = st.date_input("Exact due date (one-time/annual)", value=None)

    col3, col4 = st.columns(2)
    with col3:
        end_date = st.date_input("End date (EMI tenure end; blank = ongoing)", value=None)
        src = st.selectbox(
            "Paid from bank account (leave — if charged to a card)",
            ["—"] + banks["name"].tolist(),
        )
    with col4:
        linked = (
            st.selectbox(
                "Charged to card (if paid via credit card)",
                ["—"] + cards["name"].tolist(),
                help="For cc_bill: which card's bill this is. For subscriptions/adhoc: "
                     "which card it's charged to. Leave — if paid directly from bank.",
            )
            if ctype in ("cc_bill", "subscription", "adhoc") else "—"
        )
        notes = st.text_input("Notes (optional)")

    if st.form_submit_button("Add commitment"):
        if not name.strip():
            st.error("Name is required")
        else:
            src_id = (
                int(banks[banks["name"] == src]["id"].iloc[0]) if src != "—" else None
            )
            card_id = (
                int(cards[cards["name"] == linked]["id"].iloc[0]) if linked != "—" else None
            )
            add_commitment(
                name.strip(), ctype,
                amount if amount > 0 else None,
                frequency,
                due_day if due_day > 0 else None,
                due_date.isoformat() if due_date else None,
                None,
                end_date.isoformat() if end_date else None,
                src_id, card_id,
                notes.strip() or None,
            )
            st.success(f"Added: {name}")
            st.rerun()

st.divider()

# ------------------------- Edit ----------------------------------
if not df.empty:
    with st.expander("✏️ Edit / deactivate a commitment"):
        sel = st.selectbox("Select commitment", df["name"].tolist())
        row = df[df["name"] == sel].iloc[0]

        with st.form("edit_commitment"):
            e_amount = st.number_input(
                "Amount (₹)", min_value=0.0,
                value=float(row["amount"]) if row["amount"] else 0.0, step=100.0,
            )
            e_due = st.number_input(
                "Due day", 0, 31,
                value=int(row["due_day"]) if row["due_day"] else 0,
            )
            e_end = st.text_input(
                "End date (YYYY-MM-DD, blank = ongoing)",
                value=row["end_date"] or "",
            )
            e_active = st.checkbox("Active", value=bool(row["is_active"]))
            e_notes = st.text_input("Notes", value=row["notes"] or "")

            if st.form_submit_button("Save"):
                update_commitment(
                    int(row["id"]),
                    e_amount if e_amount > 0 else None,
                    e_due if e_due > 0 else None,
                    e_end.strip() or None,
                    1 if e_active else 0,
                    e_notes.strip() or None,
                )
                st.success(f"Updated {sel}")
                st.rerun()