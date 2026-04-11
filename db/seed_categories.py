from sqlalchemy.orm import Session
from db.schema import Category, get_engine, init_db

DEFAULT_CATEGORIES = [
    ("Food & Dining",   None,            "🍽️"),
    ("Restaurants",     "Food & Dining", "🍴"),
    ("Groceries",       "Food & Dining", "🛒"),
    ("Swiggy/Zomato",  "Food & Dining", "📱"),
    ("Transport",       None,            "🚗"),
    ("Cab/Auto",        "Transport",     "🚕"),
    ("Fuel",            "Transport",     "⛽"),
    ("Metro/Bus",       "Transport",     "🚇"),
    ("Shopping",        None,            "🛍️"),
    ("Clothing",        "Shopping",      "👕"),
    ("Electronics",     "Shopping",      "💻"),
    ("Entertainment",   None,            "🎬"),
    ("OTT/Streaming",  "Entertainment", "📺"),
    ("Movies",          "Entertainment", "🎥"),
    ("Health",          None,            "🏥"),
    ("Medical",         "Health",        "💊"),
    ("Gym/Fitness",     "Health",        "💪"),
    ("Utilities",       None,            "💡"),
    ("Mobile/Internet", "Utilities",     "📡"),
    ("Electricity",     "Utilities",     "⚡"),
    ("Rent",            None,            "🏠"),
    ("Investments",     None,            "📈"),
    ("Mutual Funds",    "Investments",   "💹"),
    ("Stocks",          "Investments",   "📊"),
    ("EMI/Loans",       None,            "🏦"),
    ("Transfers",       None,            "↔️"),
    ("Income",          None,            "💰"),
    ("Salary",          "Income",        "💼"),
    ("Other",           None,            "📦"),
]

def seed_categories():
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        if session.query(Category).count() > 0:
            print("Categories already seeded. Skipping.")
            return
        parent_map = {}
        for name, parent_name, icon in DEFAULT_CATEGORIES:
            cat = Category(
                name      = name,
                parent_id = parent_map.get(parent_name),
                icon      = icon
            )
            session.add(cat)
            session.flush()
            parent_map[name] = cat.id
        session.commit()
        print(f"Seeded {len(DEFAULT_CATEGORIES)} categories successfully")

if __name__ == "__main__":
    seed_categories()