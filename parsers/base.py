"""
Parser framework (Solution Doc Section 6).

Rules:
- One adapter per (institution, format), registered in ADAPTER_REGISTRY.
- Adapters normalise only. They NEVER write to the DB.
- Sign convention enforced here: outflow = negative, inflow = positive.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ParsedTransaction:
    txn_date: str          # ISO format: YYYY-MM-DD
    description: str       # cleaned narration
    raw_description: str   # original line, for audit/debug and dedup hashing
    amount: float          # SIGNED: negative = outflow, positive = inflow


class ParserAdapter(ABC):
    """Base class every statement parser must implement."""

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Sniff the file header/format. Used for auto-detection on import."""

    @abstractmethod
    def parse(self, file_path: str, password: str | None = None) -> list[ParsedTransaction]:
        """Return normalised transactions. Password from .env for locked PDFs."""


# ------------------------------------------------------------------
# Registry — maps accounts.parser_adapter (DB config) to a class.
# Adding a new source = new adapter file + one line here + config row.
# Import inside the function to avoid circular imports.
# ------------------------------------------------------------------
def get_adapter(key: str) -> ParserAdapter:
    from parsers.kotak_adapter import KotakCSVAdapter

    registry = {
        "kotak_csv": KotakCSVAdapter,
        # "bob_csv":     BoBCSVAdapter,      (Week 5)
        # "canara_csv":  CanaraCSVAdapter,   (Week 5)
        # "idfc_csv":    IDFCCSVAdapter,     (Week 5)
        # "hdfc_cc_pdf": HDFCCCPDFAdapter,   (Week 4)
    }

    if key not in registry:
        raise ValueError(
            f"No adapter registered for '{key}'. "
            f"Available: {list(registry.keys())}"
        )
    return registry[key]()