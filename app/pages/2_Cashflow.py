import streamlit as st
import sys
from pathlib import Path
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.cashflow_engine import build_forecast

st.set_page_config(page_title="Cashflow", page_icon="📈", layout="wide")
st.title("📈 Cashflow Forecast")

horizon = st.radio("Horizon", [30, 90, 180], index=1, horizontal=True,
                   format_func=lambda d: f"{d} days")

fc = build_forecast(horizon)
floor = float(fc.settings.get("balance_floor", 0))

# ---------------- weekly timeline chart ----------------
labels  = [f"{w.week_start.strftime('%d %b')}" for w in fc.weeks]
inflow  = [w.inflows for w in fc.weeks]
outflow = [-(w.committed_outflows + w.projected_discretionary) for w in fc.weeks]
closing = [w.closing_balance for w in fc.weeks]

fig = go.Figure()
fig.add_bar(x=labels, y=inflow, name="Inflows", marker_color="#2E7D32")
fig.add_bar(x=labels, y=outflow, name="Outflows (committed + discretionary)",
            marker_color="#C62828")
fig.add_scatter(x=labels, y=closing, name="Closing balance",
                mode="lines+markers", line=dict(color="#1565C0", width=3))
fig.add_hline(y=floor, line_dash="dot", line_color="orange",
              annotation_text=f"Floor ₹{floor:,.0f}")
fig.update_layout(
    barmode="relative", height=450,
    legend=dict(orientation="h", y=1.1),
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig, use_container_width=True)

# ---------------- week drill-down ----------------
st.subheader("Week-by-Week Detail")
for w in fc.weeks:
    flag = " ⚠️ CRUNCH" if w.is_crunch else ""
    header = (f"{w.week_start} → {w.week_end}  ·  "
              f"close ₹{w.closing_balance:,.0f}{flag}")
    with st.expander(header):
        cols = st.columns(3)
        cols[0].metric("Inflows", f"₹{w.inflows:,.0f}")
        cols[1].metric("Committed", f"₹{w.committed_outflows:,.0f}")
        cols[2].metric("Discretionary (proj.)",
                       f"₹{w.projected_discretionary:,.0f}")
        if w.items:
            for item in w.items:
                st.markdown(f"- {item}")
        else:
            st.caption("No commitment events this week.")