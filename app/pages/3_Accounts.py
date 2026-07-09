import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.crud_service import get_accounts, update_account, add_account

st.set_page_config(page_title="Accounts", page_icon="🏦", layout="wide")
st.title("🏦 Accounts")

# ------------------------- View accounts -------------------------
show_inactive = st.toggle("Show archived accounts", value=False)
df = get_accounts(include_inactive=show_inactive)

banks = df[df["type"] == "bank"]
cards = df[df["type"] == "credit_card"]

st.subheader("Bank Accounts")
st.dataframe(
    banks[["name", "institution", "parser_adapter", "is_active"]],
    use_container_width=True, hide_index=True,
)

st.subheader("Credit Cards")
st.dataframe(
    cards[["name", "institution", "billing_day", "due_day", "is_active"]],
    use_container_width=True, hide_index=True,
)

st.divider()

# ------------------------- Edit account --------------------------
st.subheader("Edit an Account")

names = df["name"].tolist()
selected = st.selectbox("Select account", names)
row = df[df["name"] == selected].iloc[0]

with st.form("edit_account"):
    col1, col2 = st.columns(2)
    with col1:
        import pandas as pd
        billing = st.number_input(
            "Billing day (credit cards only)",
            min_value=0, max_value=31,
            value=int(row["billing_day"]) if pd.notna(row["billing_day"]) else 0,
            help="0 = not applicable",
        )
        due = st.number_input(
            "Due day (credit cards only)",
            min_value=0, max_value=31,
            value=int(row["due_day"]) if pd.notna(row["due_day"]) else 0,
        )
    with col2:
        adapter = st.text_input(
            "Parser adapter key",
            value=row["parser_adapter"] or "",
            help="e.g. kotak_csv — leave blank if no parser built yet",
        )
        active = st.checkbox("Active", value=bool(row["is_active"]))

    if st.form_submit_button("Save changes"):
        update_account(
            int(row["id"]),
            billing if billing > 0 else None,
            due if due > 0 else None,
            adapter.strip() or None,
            1 if active else 0,
        )
        st.success(f"Updated {selected}")
        st.rerun()

st.divider()

# ------------------------- Add account ---------------------------
with st.expander("➕ Add a new account"):
    with st.form("add_account"):
        n_name = st.text_input("Account name (e.g. 'HDFC Millennia')")
        n_type = st.selectbox("Type", ["bank", "credit_card"])
        n_inst = st.text_input("Institution (e.g. 'HDFC')")
        n_bill = st.number_input("Billing day (0 = N/A)", 0, 31, 0)
        n_due  = st.number_input("Due day (0 = N/A)", 0, 31, 0)

        if st.form_submit_button("Add account"):
            if n_name.strip():
                add_account(
                    n_name.strip(), n_type, n_inst.strip(),
                    None,
                    n_bill if n_bill > 0 else None,
                    n_due if n_due > 0 else None,
                )
                st.success(f"Added {n_name}")
                st.rerun()
            else:
                st.error("Account name is required")