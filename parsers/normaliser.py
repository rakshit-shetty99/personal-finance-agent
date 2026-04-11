from dataclasses import dataclass
from datetime import date


@dataclass
class NormalisedTransaction:
    """
    Standard transaction format all parsers must output.
    No matter which bank the CSV comes from — Kotak, HDFC, Axis —
    the parser converts it to this shape before writing to DB.
    """
    date:            date
    description:     str        # cleaned merchant name
    raw_description: str        # original text from bank statement
    amount:          float      # always positive
    txn_type:        str        # "debit" or "credit"
    source:          str        # "kotak_csv", "hdfc_csv", "card_pdf"
    balance:         float = 0.0