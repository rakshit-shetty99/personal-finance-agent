"""
Kotak Bank CSV adapter.

Confirmed CSV format:
Sl. No. | Transaction Date | Value Date | Description |
Chq / Ref No. | Amount | Dr / Cr | Balance | Dr / Cr

Notes carried over from Week 1 debugging:
- Transaction Date includes a timestamp suffix: 'DD-MM-YYYY HH:MM'
- Single Amount column; direction comes from the FIRST 'Dr / Cr' column
- Second 'Dr / Cr' (balance direction) is auto-renamed 'Dr / Cr.1' by pandas — ignored
"""

import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from parsers.base import ParserAdapter, ParsedTransaction

COL_DATE      = "Transaction Date"
COL_DESC      = "Description"
COL_AMOUNT    = "Amount"
COL_DIRECTION = "Dr / Cr"

DEBIT_MARKERS  = ("dr", "d", "debit", "withdrawal")
CREDIT_MARKERS = ("cr", "c", "credit", "deposit")

DATE_FORMATS = (
    "%d-%m-%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y",
    "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y",
)


class KotakCSVAdapter(ParserAdapter):

    def can_parse(self, file_path: str) -> bool:
        """Kotak CSV is identified by its distinctive header columns."""
        if not str(file_path).lower().endswith(".csv"):
            return False
        try:
            df = self._read_with_header_detection(file_path, probe_only=True)
            return df is not None
        except Exception:
            return False

    def parse(self, file_path: str, password: str | None = None) -> list[ParsedTransaction]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        df = self._read_with_header_detection(file_path)
        if df is None:
            raise ValueError(
                f"Could not find columns '{COL_DATE}' and '{COL_AMOUNT}' in {file_path}"
            )

        transactions = []
        for _, row in df.iterrows():
            raw_date = str(row.get(COL_DATE, "")).strip()
            if not raw_date or raw_date.lower() in ("nan", "", "transaction date"):
                continue

            txn_date = self._parse_date(raw_date)
            if txn_date is None:
                continue

            amount = self._clean_amount(row.get(COL_AMOUNT, ""))
            if amount == 0.0:
                continue

            # Sign convention: debit -> negative (outflow)
            direction = str(row.get(COL_DIRECTION, "")).strip().lower()
            if any(direction.startswith(m) for m in DEBIT_MARKERS):
                amount = -abs(amount)
            elif any(direction.startswith(m) for m in CREDIT_MARKERS):
                amount = abs(amount)
            else:
                amount = -abs(amount)   # unknown direction: assume outflow (conservative)

            raw_desc = str(row.get(COL_DESC, "")).strip()
            if not raw_desc or raw_desc.lower() == "nan":
                raw_desc = f"Transaction on {txn_date}"

            transactions.append(ParsedTransaction(
                txn_date        = txn_date,
                description     = self._clean_description(raw_desc),
                raw_description = raw_desc,
                amount          = round(amount, 2),
            ))

        return transactions

    # ------------------------- helpers -------------------------

    def _read_with_header_detection(self, file_path: str, probe_only: bool = False):
        """Kotak sometimes prepends bank-info rows before the header row."""
        for skip in range(0, 15):
            try:
                df = pd.read_csv(file_path, skiprows=skip, encoding="utf-8", dtype=str)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, skiprows=skip, encoding="latin-1", dtype=str)
            except Exception:
                return None
            df.columns = [str(c).strip() for c in df.columns]
            if COL_DATE in df.columns and COL_AMOUNT in df.columns:
                return True if probe_only else df
        return None

    @staticmethod
    def _parse_date(raw: str) -> str | None:
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(raw.strip(), fmt).date().isoformat()
            except ValueError:
                continue
        return None

    @staticmethod
    def _clean_amount(value) -> float:
        if pd.isna(value) or str(value).strip() in ("", "-", "nan"):
            return 0.0
        cleaned = str(value).replace(",", "").replace("₹", "").replace(" ", "").strip()
        try:
            return abs(float(cleaned))
        except ValueError:
            return 0.0

    @staticmethod
    def _clean_description(text: str) -> str:
        text = re.sub(r"/\d{6,}", "", str(text).strip())
        text = re.sub(r"\s+", " ", text)
        return text.strip()