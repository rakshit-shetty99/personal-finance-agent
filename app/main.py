import streamlit as st
import sys
from pathlib import Path

# Make project root importable when Streamlit runs from app/
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.crud_service import get_db_summary

st.set_page_config(
    page_title="Personal Finance Agent",
    page_icon="💰",
    layout="wide",
)

st.title("💰 Personal Finance Agent")
st.caption("Local-first · Privacy-first · Salary-cycle aware")

s = get_db_summary()

c1, c2, c3, c4 = st.columns(2) + st.columns(2) if False else st.columns(4)
c1.metric("Active Accounts", s["accounts"])
c2.metric("Transactions", s["transactions"])
c3.metric("Active Commitments", s["commitments"])
c4.metric("Monthly Committed", f"₹{s['monthly_committed']:,.0f}")

st.divider()
st.markdown("""
**Use the sidebar to navigate:**
- **Accounts** — manage your banks and credit cards
- **Commitments** — enter EMIs, rent, subscriptions, ad hoc commitments

*Cashflow forecast dashboard arrives in Week 3.*
""")