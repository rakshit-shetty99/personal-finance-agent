import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.cashflow_engine import get_settings, set_setting, detect_salary

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings")

s = get_settings()
detected = detect_salary()

with st.form("settings"):
    opening = st.number_input(
        "Opening balance (₹) — total current cash across your bank accounts",
        min_value=0.0, value=float(s.get("opening_balance", 0)), step=1000.0,
        help="The forecast's anchor. Update this whenever it drifts from reality.",
    )
    floor = st.number_input(
        "Balance floor (₹) — weeks below this get a crunch flag",
        min_value=0.0, value=float(s.get("balance_floor", 10000)), step=1000.0,
    )
    salary_day = st.number_input(
        f"Salary day override (auto-detected: day {detected['day']})",
        min_value=1, max_value=28, value=int(s.get("salary_day", 25)),
        help="Detection uses your transaction history; this is the fallback.",
    )

    if st.form_submit_button("Save settings"):
        set_setting("opening_balance", opening)
        set_setting("balance_floor", floor)
        set_setting("salary_day", salary_day)
        st.success("Saved. Dashboard and Cashflow now use these values.")

st.caption(
    f"Salary detection status: {'✅ detected from data' if detected['detected'] else '⚠️ using fallback'} "
    f"· day {detected['day']} · ~₹{detected['amount']:,.0f}"
)