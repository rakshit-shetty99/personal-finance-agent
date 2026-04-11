import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from parsers.normaliser import NormalisedTransaction

# ------------------------------------------------------------------
# Column names exactly as they appear in your Kotak CSV
# ------------------------------------------------------------------
COL_DATE        = "Transaction Date"
COL_DESCRIPTION = "Description"
COL_AMOUNT      = "Amount"
COL_DIRECTION   = "Dr / Cr"     # First occurrence = transaction direction
COL_BALANCE     = "Balance"

DEBIT_MARKERS   = ["dr", "d", "debit", "withdrawal"]
CREDIT_MARKERS  = ["cr", "c", "credit", "deposit"]


def _clean_amount(value) -> float:
    """
    Converts '1,234.56' or '₹ 1,234.56' to float 1234.56.
    Always returns a positive number — direction is handled separately.
    """
    if pd.isna(value) or str(value).strip() in ("", "-", "nan"):
        return 0.0
    cleaned = (
        str(value)
        .replace(",", "")
        .replace("₹", "")
        .replace(" ", "")
        .strip()
    )
    try:
        return abs(float(cleaned))
    except ValueError:
        return 0.0


def _parse_direction(value) -> str:
    """
    Reads the Dr / Cr column and returns 'debit' or 'credit'.
    Handles Dr, DR, dr, D, Debit, Cr, CR, cr, C, Credit.
    """
    raw = str(value).strip().lower()
    if any(raw == m or raw.startswith(m) for m in DEBIT_MARKERS):
        return "debit"
    if any(raw == m or raw.startswith(m) for m in CREDIT_MARKERS):
        return "credit"
    return "unknown"


def _clean_description(text: str) -> str:
    """
    Removes reference numbers and extra whitespace from Kotak narrations.
    Keeps the meaningful merchant/purpose text.
    Example: 'UPI/123456789/Swiggy' -> 'UPI/Swiggy'
    """
    text = str(text).strip()
    text = re.sub(r'/\d{6,}', '', text)   # Remove long numeric ref numbers
    text = re.sub(r'\s+', ' ', text)       # Collapse multiple spaces
    return text.strip()


def _parse_date(raw_date: str):
    """
    Tries all date formats Kotak is known to use.
    Returns a date object or None if the format is unrecognised.
    """
    raw_date = str(raw_date).strip()
    for fmt in ("%d-%m-%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw_date, fmt).date()
        except ValueError:
            continue
    return None


def parse_kotak_csv(file_path: str) -> list[NormalisedTransaction]:
    """
    Reads your Kotak Bank CSV and returns NormalisedTransaction objects.

    Your confirmed CSV format:
    Sl. No. | Transaction Date | Value Date | Description |
    Chq / Ref No. | Amount | Dr / Cr | Balance | Dr / Cr

    Important: The CSV has TWO 'Dr / Cr' columns.
    - First one (index position 6) = transaction direction  <- we use this
    - Second one (last column)     = balance direction      <- we ignore this
    pandas auto-renames the second duplicate to 'Dr / Cr.1'
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}\n"
            f"Make sure your CSV is saved at data/raw/kotak_statement.csv"
        )

    # ------------------------------------------------------------------
    # Read CSV — try skipping rows in case Kotak adds bank info before headers
    # Also handle encoding differences (utf-8 vs latin-1)
    # ------------------------------------------------------------------
    df = None
    for skip_rows in range(0, 15):
        try:
            temp = pd.read_csv(
                file_path,
                skiprows=skip_rows,
                encoding="utf-8",
                dtype=str           # Read everything as string first — safer
            )
        except UnicodeDecodeError:
            temp = pd.read_csv(
                file_path,
                skiprows=skip_rows,
                encoding="latin-1",
                dtype=str
            )

        # Strip whitespace from all column names
        temp.columns = [str(c).strip() for c in temp.columns]

        # This is the real header row if these two columns exist
        if COL_DATE in temp.columns and COL_AMOUNT in temp.columns:
            df = temp
            if skip_rows > 0:
                print(f"Note: Skipped {skip_rows} non-data row(s) before headers")
            break

    if df is None:
        raise ValueError(
            f"Could not find columns '{COL_DATE}' and '{COL_AMOUNT}' in your CSV.\n"
            f"First row of your file: {pd.read_csv(file_path, nrows=1).columns.tolist()}\n"
            f"Paste this output here and we will fix the column mapping."
        )

    print(f"Columns found     : {list(df.columns)}")
    print(f"Total rows in CSV : {len(df)}")

    # ------------------------------------------------------------------
    # Handle the duplicate Dr / Cr column
    # pandas renames: first = 'Dr / Cr', second = 'Dr / Cr.1'
    # We want the FIRST one which is the transaction direction
    # ------------------------------------------------------------------
    if COL_DIRECTION not in df.columns:
        raise ValueError(
            f"Direction column '{COL_DIRECTION}' not found.\n"
            f"Available columns: {list(df.columns)}"
        )

    # ------------------------------------------------------------------
    # Parse each row
    # ------------------------------------------------------------------
    transactions = []
    skipped      = 0
    warnings     = []

    for idx, row in df.iterrows():

        # Skip rows with empty date — these are summary or footer rows
        raw_date_val = str(row.get(COL_DATE, "")).strip()
        if not raw_date_val or raw_date_val.lower() in ("nan", "", "transaction date"):
            skipped += 1
            continue

        # Parse date
        txn_date = _parse_date(raw_date_val)
        if txn_date is None:
            warnings.append(f"Row {idx + 2}: Unknown date '{raw_date_val}' — skipped")
            skipped += 1
            continue

        # Parse amount
        amount = _clean_amount(row.get(COL_AMOUNT, ""))
        if amount == 0.0:
            skipped += 1
            continue

        # Parse direction (debit / credit)
        direction_raw = row.get(COL_DIRECTION, "")
        direction     = _parse_direction(direction_raw)
        if direction == "unknown":
            warnings.append(
                f"Row {idx + 2}: Unrecognised Dr/Cr value '{direction_raw}' "
                f"— defaulting to debit"
            )
            direction = "debit"

        # Parse description
        raw_desc = str(row.get(COL_DESCRIPTION, "")).strip()
        if not raw_desc or raw_desc.lower() == "nan":
            raw_desc = f"Transaction on {txn_date}"

        # Parse balance
        balance = _clean_amount(row.get(COL_BALANCE, 0))

        transactions.append(NormalisedTransaction(
            date            = txn_date,
            description     = _clean_description(raw_desc),
            raw_description = raw_desc,
            amount          = amount,
            txn_type        = direction,
            source          = "kotak_csv",
            balance         = balance,
        ))

    # ------------------------------------------------------------------
    # Print results summary
    # ------------------------------------------------------------------
    print(f"\nTransactions extracted : {len(transactions)}")
    print(f"Rows skipped           : {skipped}")

    if warnings:
        print(f"\nWarnings ({len(warnings)} non-critical):")
        for w in warnings[:5]:
            print(f"  {w}")
        if len(warnings) > 5:
            print(f"  ... and {len(warnings) - 5} more")

    return transactions


# ------------------------------------------------------------------
# Dry-run validator — run this BEFORE importing to DB
# Usage: python parsers/kotak_parser.py data/raw/kotak_statement.csv
# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    csv_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/raw/kotak_statement.csv"
    )

    print(f"Testing parser on: {csv_path}\n")

    try:
        txns = parse_kotak_csv(csv_path)

        if txns:
            print(f"\nFirst 5 transactions:")
            print(f"{'Date':<12} {'Type':<7} {'Amount':>12}  Description")
            print("-" * 65)
            for t in txns[:5]:
                print(
                    f"{str(t.date):<12} {t.txn_type:<7} "
                    f"Rs.{t.amount:>10,.2f}  {t.description[:35]}"
                )

            print(f"\nLast 5 transactions:")
            print(f"{'Date':<12} {'Type':<7} {'Amount':>12}  Description")
            print("-" * 65)
            for t in txns[-5:]:
                print(
                    f"{str(t.date):<12} {t.txn_type:<7} "
                    f"Rs.{t.amount:>10,.2f}  {t.description[:35]}"
                )

            debits  = sum(t.amount for t in txns if t.txn_type == "debit")
            credits = sum(t.amount for t in txns if t.txn_type == "credit")

            print(f"\nSummary across {len(txns)} transactions:")
            print(f"  Total debits  : Rs.{debits:>12,.2f}")
            print(f"  Total credits : Rs.{credits:>12,.2f}")
            print(f"  Date range    : {txns[-1].date}  to  {txns[0].date}")
            print(f"\nParser working correctly. Safe to run import_transactions.py")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")