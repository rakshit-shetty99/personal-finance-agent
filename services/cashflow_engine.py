"""
Cashflow Engine — Solution Doc Section 7.

Computes:
  1. Salary anchor      — auto-detected from Kotak data (largest recurring credit),
                          with manual override via settings.salary_day
  2. Financial month    — salary date to salary date, NOT calendar month
  3. 90-day forecast    — weekly buckets (due dates scatter across the month:
                          2nd, 3rd, 4th, 9-10th, 12th, 21st, 23rd)
  4. CC bill estimation — parsed bill if available (Week 4+), else trailing
                          3-month average spend on that card, flagged 'estimated'
  5. Headroom           — residual method:
                          salary - committed - projected_discretionary
"""

import sqlite3
import os
from datetime import date, timedelta
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/finance.db")


# ----------------------------- data shapes -----------------------------

@dataclass
class WeekBucket:
    week_start: date
    week_end: date
    inflows: float = 0.0
    committed_outflows: float = 0.0
    projected_discretionary: float = 0.0
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    is_crunch: bool = False
    items: list = field(default_factory=list)   # human-readable line items


@dataclass
class CashflowForecast:
    weeks: list                    # list[WeekBucket]
    salary_day: int
    salary_amount: float
    cycle_start: date
    cycle_end: date
    headroom: float
    largest_committed_week: float
    settings: dict


# ----------------------------- helpers ---------------------------------

def _conn():
    return sqlite3.connect(DB_PATH)


def get_settings() -> dict:
    with _conn() as c:
        return dict(c.execute("SELECT key, value FROM settings").fetchall())


def set_setting(key: str, value: str):
    with _conn() as c:
        c.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        c.commit()


# ----------------------- salary detection ------------------------------

def detect_salary(min_amount: float = 50000) -> dict:
    """
    Finds the salary pattern in transactions: large credits (>= min_amount)
    recurring in a similar day-of-month window. Returns detected day + average
    amount. Falls back to settings if detection is inconclusive.

    Why auto-detect: the salary anchor drives the entire financial-month
    logic; hardcoding it breaks the moment payday shifts.
    """
    with _conn() as c:
        rows = c.execute(
            """SELECT txn_date, amount FROM transactions
               WHERE amount >= ? ORDER BY txn_date""",
            (min_amount,),
        ).fetchall()

    settings = get_settings()
    fallback_day = int(settings.get("salary_day", 25))

    if len(rows) < 2:
        return {"day": fallback_day, "amount": rows[0][1] if rows else 0.0,
                "detected": False}

    days = [date.fromisoformat(d).day for d, _ in rows]
    amounts = [a for _, a in rows]

    # Median day is robust to one-off large credits (refunds, transfers in)
    days.sort()
    median_day = days[len(days) // 2]
    avg_amount = sum(amounts) / len(amounts)

    return {"day": median_day, "amount": round(avg_amount, 2), "detected": True}


# ----------------------- financial month -------------------------------

def current_cycle(salary_day: int, today: date | None = None) -> tuple[date, date]:
    """
    Financial month = salary date to salary date.
    If today is Jul 9 and salary_day is 25: cycle = Jun 25 -> Jul 24.
    """
    today = today or date.today()
    if today.day >= salary_day:
        start = today.replace(day=salary_day)
    else:
        prev = (today.replace(day=1) - timedelta(days=1))
        start = prev.replace(day=min(salary_day, 28))
    # Cycle end = day before next salary
    nxt = (start.replace(day=28) + timedelta(days=7)).replace(day=salary_day)
    return start, nxt - timedelta(days=1)


# ----------------------- CC bill estimation ----------------------------

def estimate_cc_bills() -> list[dict]:
    """
    For each active credit card, produce next bill estimate:
    - If a cc_bill commitment with an amount exists -> use it ('known')
    - Else -> trailing 3-month average of that card's transactions ('estimated')
      (Until Week 4 PDF parsing, cards with no imported txns estimate at 0 —
       enter a cc_bill commitment manually for realistic numbers.)
    """
    today = date.today()
    bills = []
    with _conn() as c:
        cards = c.execute(
            """SELECT id, name, due_day FROM accounts
               WHERE type='credit_card' AND is_active=1"""
        ).fetchall()

        for card_id, name, due_day in cards:
            known = c.execute(
                """SELECT amount FROM commitments
                   WHERE type='cc_bill' AND linked_card_id=? AND is_active=1
                   AND amount IS NOT NULL""",
                (card_id,),
            ).fetchone()

            if known:
                amount, status = known[0], "known"
            else:
                cutoff = (today - timedelta(days=90)).isoformat()
                spend = c.execute(
                    """SELECT COALESCE(SUM(ABS(amount)),0) FROM transactions
                       WHERE account_id=? AND amount<0 AND txn_date>=?""",
                    (card_id, cutoff),
                ).fetchone()[0]
                amount, status = round(spend / 3, 2), "estimated"

            if not due_day:
                continue

            # Next due date from today
            due = today.replace(day=min(due_day, 28))
            if due <= today:
                due = (due.replace(day=1) + timedelta(days=32)).replace(day=min(due_day, 28))

            if amount > 0:
                bills.append({"name": f"{name} bill", "amount": amount,
                              "due": due, "status": status})
    return bills


# ----------------------- discretionary projection ----------------------

# Categories whose outflows are NOT discretionary spending.
# CC payments are excluded because card spend enters the forecast via
# CC bill estimates/commitments — counting both would double-count.
NON_DISCRETIONARY_CATEGORIES = {
    "CC Payment", "Investments", "Transfers", "EMI/Loans", "Rent", "Salary", "Income",
}


def projected_weekly_discretionary() -> float:
    """
    Average weekly discretionary spend over the trailing 90 days.
    Discretionary = bank outflows EXCLUDING:
      1. Anything matching a category_rules pattern whose category is
         non-discretionary (CC payments, investments, transfers, EMIs)
      2. Outflows matching an active commitment amount (+-5%) — catches
         commitments paid in ways the rules don't cover (e.g. rent via IMPS)
    """
    from datetime import date, timedelta
    today = date.today()
    cutoff = (today - timedelta(days=90)).isoformat()

    with _conn() as c:
        exclusion_patterns = [
            p.upper() for (p,) in c.execute(
                """SELECT match_pattern FROM category_rules
                   WHERE is_active = 1 AND category IN ({})""".format(
                    ",".join("?" * len(NON_DISCRETIONARY_CATEGORIES))
                ),
                tuple(NON_DISCRETIONARY_CATEGORIES),
            ).fetchall()
        ]

        outflows = c.execute(
            """SELECT ABS(t.amount), COALESCE(t.raw_description, t.description, '')
               FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               WHERE a.type='bank' AND t.amount < 0 AND t.txn_date >= ?""",
            (cutoff,),
        ).fetchall()

        commitment_amounts = [
            r[0] for r in c.execute(
                "SELECT amount FROM commitments WHERE is_active=1 AND amount IS NOT NULL"
            ).fetchall()
        ]

    def excluded(amt: float, desc: str) -> bool:
        d = desc.upper()
        if any(p in d for p in exclusion_patterns):
            return True
        return any(abs(amt - ca) <= ca * 0.05 for ca in commitment_amounts)

    disc = [amt for amt, desc in outflows if not excluded(amt, desc)]
    return round(sum(disc) / (90 / 7), 2)


# ----------------------- the forecast ----------------------------------

def build_forecast(horizon_days: int = 90) -> CashflowForecast:
    settings = get_settings()
    salary = detect_salary()
    salary_day = salary["day"]
    salary_amount = salary["amount"]

    opening = float(settings.get("opening_balance", 0))
    floor = float(settings.get("balance_floor", 0))
    weekly_disc = projected_weekly_discretionary()

    today = date.today()
    end = today + timedelta(days=horizon_days)

    # ---- collect commitment events in horizon (bank-paid only!) ----
    # Card-charged subscriptions are INSIDE the card's bill -> counting them
    # here would double-count (the linked_card fix from Week 2).
    events = []
    with _conn() as c:
        rows = c.execute(
            """SELECT name, amount, frequency, due_day, due_date, end_date
               FROM commitments
               WHERE is_active=1 AND type != 'cc_bill'
               AND linked_card_id IS NULL AND amount IS NOT NULL"""
        ).fetchall()

    for name, amount, freq, due_day, due_date_s, end_date_s in rows:
        commit_end = date.fromisoformat(end_date_s) if end_date_s else None
        if freq == "one_time" and due_date_s:
            d = date.fromisoformat(due_date_s)
            if today <= d <= end:
                events.append({"name": name, "amount": amount, "due": d})
        elif freq == "monthly" and due_day:
            d = today.replace(day=1)
            while d <= end:
                due = d.replace(day=min(due_day, 28))
                if today <= due <= end and (not commit_end or due <= commit_end):
                    events.append({"name": name, "amount": amount, "due": due})
                d = (d + timedelta(days=32)).replace(day=1)
        elif freq == "annual" and due_date_s:
            d = date.fromisoformat(due_date_s)
            if today <= d <= end:
                events.append({"name": name, "amount": amount, "due": d})

    # ---- CC bills as events ----
    for bill in estimate_cc_bills():
        if today <= bill["due"] <= end:
            tag = "" if bill["status"] == "known" else " (est.)"
            events.append({"name": bill["name"] + tag,
                           "amount": bill["amount"], "due": bill["due"]})

    # ---- salary inflows in horizon ----
    inflow_events = []
    d = today.replace(day=1)
    while d <= end:
        pay = d.replace(day=min(salary_day, 28))
        if today <= pay <= end:
            inflow_events.append({"name": "Salary", "amount": salary_amount, "due": pay})
        d = (d + timedelta(days=32)).replace(day=1)

    # ---- build weekly buckets ----
    weeks = []
    balance = opening
    n_weeks = (horizon_days // 7) + 1
    for i in range(n_weeks):
        ws = today + timedelta(days=i * 7)
        we = ws + timedelta(days=6)
        wk = WeekBucket(week_start=ws, week_end=we, opening_balance=round(balance, 2))

        for ev in inflow_events:
            if ws <= ev["due"] <= we:
                wk.inflows += ev["amount"]
                wk.items.append(f"+ {ev['name']}: Rs.{ev['amount']:,.0f} ({ev['due']})")
        for ev in events:
            if ws <= ev["due"] <= we:
                wk.committed_outflows += ev["amount"]
                wk.items.append(f"- {ev['name']}: Rs.{ev['amount']:,.0f} ({ev['due']})")

        wk.projected_discretionary = weekly_disc
        balance = balance + wk.inflows - wk.committed_outflows - weekly_disc
        wk.closing_balance = round(balance, 2)
        wk.is_crunch = wk.closing_balance < floor
        weeks.append(wk)

    # ---- headroom for current cycle (residual method) ----
    cyc_start, cyc_end = current_cycle(salary_day)
    cyc_committed = sum(
        ev["amount"] for ev in events if cyc_start <= ev["due"] <= cyc_end
    )
    cyc_disc = weekly_disc * ((cyc_end - cyc_start).days / 7)
    headroom = round(salary_amount - cyc_committed - cyc_disc, 2)

    return CashflowForecast(
        weeks=weeks,
        salary_day=salary_day,
        salary_amount=salary_amount,
        cycle_start=cyc_start,
        cycle_end=cyc_end,
        headroom=headroom,
        largest_committed_week=max((w.committed_outflows for w in weeks), default=0),
        settings=settings,
    )