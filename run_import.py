"""
CLI entry point for statement imports.

Usage:
  python run_import.py data/raw/kotak_statement.csv "Kotak Savings"
"""

import sys
from services.import_service import import_statement

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python run_import.py <file_path> "<Account Name>"')
        sys.exit(1)

    file_path    = sys.argv[1]
    account_name = sys.argv[2]

    print(f"Importing '{file_path}' into account '{account_name}'...")
    result = import_statement(file_path, account_name)
    print(f"Done. Status: {result['status']}")