from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, Date, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv
import os

load_dotenv()

Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"

    id             = Column(Integer, primary_key=True)
    name           = Column(String, nullable=False)
    account_type   = Column(String, nullable=False)   # savings / credit / investment
    bank           = Column(String, nullable=False)
    masked_number  = Column(String)                   # last 4 digits only
    created_at     = Column(DateTime, server_default=func.now())

    transactions   = relationship("Transaction", back_populates="account")


class Category(Base):
    __tablename__ = "categories"

    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False)
    parent_id   = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_custom   = Column(Integer, default=0)          # 0 = system, 1 = user-defined
    icon        = Column(String, default="💰")

    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id               = Column(Integer, primary_key=True)
    date             = Column(Date, nullable=False)
    description      = Column(String, nullable=False)
    raw_description  = Column(String)
    amount           = Column(Float, nullable=False)
    txn_type         = Column(String, nullable=False)  # debit / credit
    category_id      = Column(Integer, ForeignKey("categories.id"), nullable=True)
    account_id       = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    source           = Column(String)                  # kotak_csv / card_pdf
    confidence       = Column(Float, default=0.0)      # AI categorisation score
    is_verified      = Column(Integer, default=0)      # 1 = user confirmed category
    hash             = Column(String, unique=True)     # deduplication key
    created_at       = Column(DateTime, server_default=func.now())

    account          = relationship("Account", back_populates="transactions")
    category         = relationship("Category", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"

    id          = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    month       = Column(Integer, nullable=False)
    year        = Column(Integer, nullable=False)
    limit_amt   = Column(Float, nullable=False)
    created_at  = Column(DateTime, server_default=func.now())


class InsightCache(Base):
    __tablename__ = "insights_cache"

    id           = Column(Integer, primary_key=True)
    insight_type = Column(String)
    period       = Column(String)
    content_json = Column(Text)
    created_at   = Column(DateTime, server_default=func.now())


def get_engine():
    db_path = os.getenv("DB_PATH", "data/finance.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database initialised at:", os.getenv("DB_PATH", "data/finance.db"))
    return engine


if __name__ == "__main__":
    init_db()