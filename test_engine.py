"""Terminal test for the cashflow engine — run before building any UI."""

from services.cashflow_engine import build_forecast, detect_salary

salary = detect_salary()
print("=== SALARY DETECTION ===")
print(f"Detected: {salary['detected']} | Day: {salary['day']} | "
      f"Amount: Rs.{salary['amount']:,.2f}\n")

fc = build_forecast(90)

print("=== CURRENT CYCLE ===")
print(f"{fc.cycle_start} -> {fc.cycle_end}")
print(f"Headroom this cycle: Rs.{fc.headroom:,.2f}\n")

print("=== 90-DAY WEEKLY FORECAST ===")
print(f"{'Week':<24} {'In':>10} {'Committed':>11} {'Disc.':>9} {'Close':>12}")
print("-" * 72)
for w in fc.weeks:
    flag = "  << CRUNCH" if w.is_crunch else ""
    print(f"{str(w.week_start)} - {str(w.week_end)}  "
          f"{w.inflows:>10,.0f} {w.committed_outflows:>11,.0f} "
          f"{w.projected_discretionary:>9,.0f} {w.closing_balance:>12,.0f}{flag}")

print("\n=== WEEK DETAILS (non-empty) ===")
for w in fc.weeks:
    if w.items:
        print(f"\n{w.week_start}:")
        for item in w.items:
            print(f"  {item}")