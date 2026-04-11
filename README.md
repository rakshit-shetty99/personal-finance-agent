# 💰 Personal Finance Agent

> An AI-powered personal finance agent that automatically categorises expenses, tracks budgets, and surfaces spending insights — built with LangGraph, Claude API, and Streamlit.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green?style=flat-square)
![Claude API](https://img.shields.io/badge/Claude-API-orange?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-1.4+-red?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-Local--First-lightgrey?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen?style=flat-square)

---

## 📌 What This Project Does

Most people don't know where their money goes. This agent solves that by:

- **Ingesting** bank statements (CSV) and credit card statements (PDF) automatically
- **Categorising** every transaction using a LangGraph AI agent powered by Claude API
- **Tracking** budgets per category with real-time alerts
- **Surfacing** weekly and monthly spending insights without you having to ask
- **Visualising** everything in a clean, mobile-accessible Streamlit dashboard

All data stays **100% local** on your machine. Only anonymised, sanitised summaries are sent to the Claude API — never raw account numbers or transaction data.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Streamlit UI                      │
│  Dashboard │ Upload │ Expenses │ Budget │ AI Chat    │
└──────────────────────┬──────────────────────────────┘
                       │ queries / results
┌──────────────────────▼──────────────────────────────┐
│                  LangGraph Agents                    │
│  Categorisation │ Query │ Insights │ Budget Alerts   │
└──────────────────────┬──────────────────────────────┘
                       │ sanitised data only
┌──────────────────────▼──────────────────────────────┐
│              Claude API (Anthropic)                  │
│   Merchant categorisation │ NL→SQL │ Insights gen    │
│         🔒 PII stripped before every API call        │
└──────────────────────┬──────────────────────────────┘
                       │ normalised transactions
┌──────────────────────▼──────────────────────────────┐
│               Local SQLite Database                  │
│  transactions │ categories │ budgets │ accounts      │
└──────────────────────┬──────────────────────────────┘
                       │ raw parsing
┌──────────────────────▼──────────────────────────────┐
│                 Ingestion Layer                      │
│  Bank CSV Parser │ PDF Parser │ Deduplication Engine │
└─────────────────────────────────────────────────────┘
```

---

## ✨ Features

### ✅ Week 1 — Complete
- [x] Kotak Bank CSV parser with automatic column detection
- [x] Multi-format date parsing (handles timestamp suffixes)
- [x] Schema normaliser — unified transaction format across all bank sources
- [x] SQLite database with 5 tables (transactions, categories, budgets, accounts, insights cache)
- [x] Hash-based deduplication engine — safe to re-import overlapping statements
- [x] 29 default expense categories with parent-child hierarchy
- [x] 234 real transactions imported and verified

### 🔄 In Progress — Week 2
- [ ] LangGraph categorisation agent
- [ ] Merchant rules table (Swiggy → Food, Uber → Transport)
- [ ] Claude API batch categorisation (50 transactions per call)
- [ ] Confidence scoring + manual review flagging

### 📅 Upcoming
- [ ] Streamlit dashboard with expense charts
- [ ] Budget tracker with 80% threshold alerts
- [ ] Natural language query agent ("How much did I spend on food in March?")
- [ ] Credit card PDF parser
- [ ] Net worth tracker with Zerodha integration
- [ ] Weekly AI insights agent

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+ | Core |
| AI Agent Framework | LangGraph | Agent orchestration and state management |
| LLM | Claude API (Anthropic) | Categorisation, NL→SQL, insights |
| UI | Streamlit | Web dashboard — mobile accessible |
| Database | SQLite + SQLAlchemy | Local-first storage |
| Data Processing | pandas, pdfplumber | CSV and PDF parsing |
| Charts | Plotly | Interactive visualisations |
| Dev Environment | Cursor + VSCode | AI-assisted development |

**Monthly running cost:** ~₹250–350 (Claude API only. Everything else is free/open-source.)

---

## 🔒 Security & Privacy

This project was designed privacy-first from day one:

- **All financial data stays local** — stored in SQLite on your machine only
- **Sanitiser module** strips account numbers, card numbers, and IFSC codes before any data is sent to Claude API
- **What Claude API receives:** merchant name + amount + date only — never raw account details
- **What Claude API never receives:** account numbers, balances, IFSC codes, full transaction history
- `.env` file and `data/` folder are gitignored — your credentials and statements are never committed

---

## 📁 Project Structure

```
personal-finance-agent/
├── .env                        # API keys (gitignored)
├── .gitignore
├── requirements.txt
├── import_transactions.py      # Entry point — CSV to DB
├── verify_db.py                # DB health check
│
├── agents/
│   ├── categorisation.py       # LangGraph categorisation agent
│   ├── query.py                # Natural language → SQL agent
│   ├── insights.py             # Weekly insights agent
│   └── net_worth.py            # Net worth calculator
│
├── app/
│   ├── main.py                 # Streamlit entry point
│   └── pages/
│       ├── 1_dashboard.py
│       ├── 2_upload.py
│       ├── 3_expenses.py
│       ├── 4_budget.py
│       ├── 5_networth.py
│       └── 6_chat.py
│
├── parsers/
│   ├── normaliser.py           # Standard transaction schema
│   ├── kotak_parser.py         # Kotak Bank CSV parser
│   ├── pdf_parser.py           # Credit card PDF parser (Week 5)
│   └── zerodha_parser.py       # Zerodha portfolio parser (Week 7)
│
├── db/
│   ├── schema.py               # SQLAlchemy table definitions
│   ├── crud.py                 # DB read/write helpers
│   ├── deduplicator.py         # Hash-based duplicate prevention
│   └── seed_categories.py      # Default category setup
│
├── security/
│   └── sanitiser.py            # Strips PII before Claude API calls
│
├── data/                       # Gitignored — your real statements
│   └── raw/
│
└── demo/                       # Anonymised sample data for showcase
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- An Anthropic API key ([get one here](https://console.anthropic.com))
- Your bank statement exported as CSV (Kotak supported in v1)

### Installation

```bash
# Clone the repo
git clone https://github.com/rakshit-shetty99/personal-finance-agent.git
cd personal-finance-agent

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your-api-key-here
DB_PATH=data/finance.db
```

### First Run

```bash
# Initialise the database
python -m db.schema

# Seed default categories
python -m db.seed_categories

# Copy your Kotak CSV to data/raw/kotak_statement.csv
# Then import transactions
python import_transactions.py

# Verify import
python verify_db.py
```

---

## 📊 Database Schema

```
accounts          → bank accounts and credit cards (masked numbers only)
transactions      → all financial transactions with category + confidence score
categories        → hierarchical expense categories (Food > Restaurants)
budgets           → monthly budget limits per category
insights_cache    → cached AI-generated insights (avoids repeat API calls)
```

---

## 🗓️ Build Log

| Week | Focus | Status |
|---|---|---|
| Week 1 | Foundation — CSV parser, DB schema, deduplication | ✅ Complete |
| Week 2 | LangGraph categorisation agent | 🔄 In Progress |
| Week 3 | Streamlit dashboard v1 | 📅 Planned |
| Week 4 | Budget tracker + NL query agent | 📅 Planned |
| Week 5 | Credit card PDF parser | 📅 Planned |
| Week 6 | Insights agent (proactive AI analysis) | 📅 Planned |
| Week 7 | Net worth tracker + Zerodha integration | 📅 Planned |
| Week 8 | Polish, demo mode, full showcase | 📅 Planned |

---

## 🧠 Why I Built This

I work in financial operations and wanted a tool that gives me a complete, honest view of my personal finances — without using a third-party app that holds my data. This project also serves as a real-world implementation of agentic AI patterns (LangGraph stateful agents, tool use, batch processing) applied to a domain I understand deeply.

It's part of a larger series of AI agent projects I'm building to showcase practical LLM application development using the Anthropic Claude API and LangGraph framework.

---

## 🔗 Related Projects

- [Equity Research Analyst](https://github.com/rakshit-shetty99) — Claude-powered stock research assistant *(coming soon)*
- Stock & MF Analyst Agent — Autonomous screener with Zerodha integration *(planned)*

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Connect

Built by **Rakshit Shetty** — Financial Operations professional learning to build real-world AI agents.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat-square&logo=linkedin)](https://linkedin.com/in/rakshit-shetty99)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat-square&logo=github)](https://github.com/rakshit-shetty99)

---

> ⭐ If you find this useful or want to follow the build journey, star the repo — it helps others find it.
