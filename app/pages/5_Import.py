import streamlit as st
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.crud_service import get_accounts
from services.import_service import import_statement
import sqlite3, os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/finance.db")

st.set_page_config(page_title="Import", page_icon="📥", layout="wide")
st.title("📥 Import Statements")

accounts = get_accounts()
importable = accounts[accounts["parser_adapter"].notna()]

if importable.empty:
    st.warning("No accounts have a parser configured yet.")
else:
    account_name = st.selectbox("Account", importable["name"].tolist())
    uploaded = st.file_uploader(
        "Upload statement (CSV now; PDF support arrives Week 4)",
        type=["csv", "pdf"],
    )

    if uploaded and st.button("Import", type="primary"):
        suffix = Path(uploaded.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = tmp.name
        try:
            result = import_statement(tmp_path, account_name)
            st.success(
                f"Done: {result['inserted']} new transactions, "
                f"{result['skipped']} duplicates skipped."
            )
        except Exception as e:
            st.error(f"Import failed: {e}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

st.divider()

# ---------------- import history ----------------
st.subheader("Import History")
with sqlite3.connect(DB_PATH) as c:
    import pandas as pd
    log = pd.read_sql_query(
        """SELECT s.imported_at, a.name AS account, s.file_name,
                  s.period_start, s.period_end, s.txn_count, s.status
           FROM statements s JOIN accounts a ON s.account_id = a.id
           ORDER BY s.imported_at DESC LIMIT 20""", c)
st.dataframe(log, use_container_width=True, hide_index=True)