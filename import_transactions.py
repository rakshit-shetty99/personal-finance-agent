from parsers.kotak_parser import parse_kotak_csv
from db.crud import insert_transactions
from db.schema import init_db

if __name__ == "__main__":
    init_db()

    csv_path = "data/raw/kotak_statement.csv"

    print("Parsing CSV...")
    transactions = parse_kotak_csv(csv_path)

    print("\nInserting into database...")
    result = insert_transactions(
        transactions,
        bank         = "Kotak",
        account_type = "savings"
    )

    print(f"\nDone. {result['inserted']} transactions now in your database.")