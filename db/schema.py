from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text
)
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"

    id             = Column(Integer, primary_key=True)
    name           = Column(String, nullable=False)   # "Kotak Savings", "HDFC Regalia Gold"
    type           = Column(String, nullable=False)   # 'bank' | 'credit_card'
    institution    = Column(String)                   # "Kotak", "HDFC"
    parser_adapter = Column(String)                   # registry key, e.g. 'kotak_csv'
    billing_day    = Column(Integer)                  # CC only
    due_day        = Column(Integer)                  # CC only
    is_active      = Column(Integer, default=1)
    created_at     = Column(String)


class Transaction(Base):
    __tablename__ = "transactions"

    id              = Column(Integer, primary_key=True)
    account_id      = Column(Integer)
    txn_date        = Column(String, nullable=False)  # ISO date string
    description     = Column(String)
    raw_description = Column(String)                  # original narration, audit trail
    amount          = Column(Float, nullable=False)   # SIGNED: negative = outflow
    category        = Column(String)                  # plain text, driven by category_rules
    source_file     = Column(String)
    dedup_hash      = Column(String, unique=True)
    created_at      = Column(String)


class Commitment(Base):
    __tablename__ = "commitments"

    id                = Column(Integer, primary_key=True)
    name              = Column(String, nullable=False)  # "Home Loan EMI", "Netflix"
    type              = Column(String, nullable=False)  # emi|rent|cc_bill|subscription|adhoc
    amount            = Column(Float)                    # NULL = variable (cc_bill)
    frequency         = Column(String, nullable=False)   # monthly|annual|one_time
    due_day           = Column(Integer)
    due_date          = Column(String)
    start_date        = Column(String)
    end_date          = Column(String)
    source_account_id = Column(Integer)
    linked_card_id    = Column(Integer)
    is_active         = Column(Integer, default=1)
    notes             = Column(Text)


class Statement(Base):
    __tablename__ = "statements"

    id           = Column(Integer, primary_key=True)
    account_id   = Column(Integer)
    file_name    = Column(String)
    period_start = Column(String)
    period_end   = Column(String)
    txn_count    = Column(Integer)
    imported_at  = Column(String)
    status       = Column(String)   # imported | failed | partial


class CategoryRule(Base):
    __tablename__ = "category_rules"

    id            = Column(Integer, primary_key=True)
    match_pattern = Column(String, nullable=False)
    category      = Column(String, nullable=False)
    priority      = Column(Integer, default=100)
    is_active     = Column(Integer, default=1)


def get_engine():
    db_path = os.getenv("DB_PATH", "data/finance.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)