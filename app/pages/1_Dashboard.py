import streamlit as st
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.cashflow_engine import build_forecast

st.set_page_config(page_title="Dashboard", page_icon="💰", layout="wide")
st.title("💰 Dashboard")

fc = build_forecast(90)
today = date.today()

# ---------------- headline metrics ----------------
c1, c2, c3 = st.columns(3)

current_balance = fc.weeks[0].opening_balance if fc.weeks else 0
c1.metric("Cash in Hand (opening)", f"₹{current_balance:,.0f}",
          help="From Settings > opening balance. Update it there to keep this honest.")

c2.metric("Remaining Headroom This Cycle", f"₹{fc.headroom:,.0f}",
          help=f"Cycle {fc.cycle_start} → {fc.cycle_end}. "
               "Salary − remaining commitments − projected discretionary. "
               "Only future events count; past spends live in opening balance.")

next7_total = sum(
    w.committed_outflows for w in fc.weeks
    if w.week_start <= today + timedelta(days=7)
)
c3.metric("Committed in Next 7 Days", f"₹{next7_total:,.0f}")

# ---------------- crunch week alert ----------------
crunch = [w for w in fc.weeks if w.is_crunch]
if crunch:
    first = crunch[0]
    st.error(
        f"⚠️ Crunch week ahead: {first.week_start} → {first.week_end} — "
        f"closing balance projected at ₹{first.closing_balance:,.0f}, "
        f"below your ₹{float(fc.settings.get('balance_floor', 0)):,.0f} floor."
    )
else:
    st.success("✅ No crunch weeks in the next 90 days.")

st.divider()

# ---------------- upcoming commitments ----------------
st.subheader("📅 Next 14 Days")
upcoming = []
for w in fc.weeks:
    if w.week_start <= today + timedelta(days=14):
        upcoming.extend(w.items)

if upcoming:
    for item in upcoming:
        st.markdown(f"- {item}")
else:
    st.info("Nothing due in the next 14 days.")

st.caption(
    f"Salary anchor: day {fc.salary_day} · ~₹{fc.salary_amount:,.0f} · "
    f"auto-detected from transactions"
)