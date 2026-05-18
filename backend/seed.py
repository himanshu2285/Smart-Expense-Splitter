from datetime import date, timedelta

from app.database import Base, SessionLocal, engine
from app.models import Expense, ExpenseShare, Group, GroupMember, SplitMode, User


USERS = [
    ("Aarav Mehta", "aarav@example.com"),
    ("Aman Sharma", "aman@example.com"),
    ("Priya Nair", "priya@example.com"),
    ("Neha Kapoor", "neha@example.com"),
    ("Kabir Khan", "kabir@example.com"),
    ("Riya Sen", "riya@example.com"),
    ("Dev Patel", "dev@example.com"),
    ("Isha Rao", "isha@example.com"),
]

GROUPS = {
    "Goa Weekend": [0, 1, 2, 3, 4],
    "Indiranagar Flat": [1, 2, 5, 6],
    "Dinner Club": [0, 2, 3, 4, 5, 6, 7],
}

EXPENSES = [
    ("Goa Weekend", 0, 1250000, "Beach villa booking", [0, 1, 2, 3, 4]),
    ("Goa Weekend", 1, 240000, "Dinner at Fisherman's Wharf", [0, 1, 2]),
    ("Goa Weekend", 2, 180000, "Scooter rentals", [0, 1, 2, 3]),
    ("Goa Weekend", 3, 95000, "Airport cab", [0, 1, 2, 3, 4]),
    ("Goa Weekend", 4, 320000, "Shack lunch and drinks", [0, 1, 2, 3, 4]),
    ("Goa Weekend", 1, 76000, "Breakfast supplies", [1, 2, 3]),
    ("Goa Weekend", 0, 210000, "Water sports booking", [0, 2, 4]),
    ("Indiranagar Flat", 1, 420000, "Monthly groceries", [1, 2, 5, 6]),
    ("Indiranagar Flat", 2, 180000, "Internet bill", [1, 2, 5, 6]),
    ("Indiranagar Flat", 5, 260000, "House cleaning", [1, 2, 5, 6]),
    ("Indiranagar Flat", 6, 90000, "Gas cylinder", [1, 2, 5, 6]),
    ("Indiranagar Flat", 1, 150000, "Electricity bill", [1, 2, 5, 6]),
    ("Indiranagar Flat", 2, 60000, "Milk and bread", [2, 5]),
    ("Dinner Club", 0, 185000, "Trupti dinner", [0, 1, 2]),
    ("Dinner Club", 2, 310000, "Sushi night", [0, 2, 3, 4, 5]),
    ("Dinner Club", 3, 125000, "Coffee and dessert", [2, 3, 7]),
    ("Dinner Club", 4, 560000, "Birthday dinner", [0, 2, 3, 4, 5, 6, 7]),
    ("Dinner Club", 5, 98000, "Movie snacks", [3, 5, 6]),
    ("Dinner Club", 6, 220000, "Sunday brunch", [0, 2, 6, 7]),
    ("Dinner Club", 7, 145000, "Late night biryani", [2, 4, 7]),
    ("Goa Weekend", 2, 88000, "Pharmacy run", [2, 3]),
    ("Indiranagar Flat", 5, 340000, "Kitchen repairs", [1, 2, 5, 6]),
    ("Dinner Club", 3, 275000, "Rooftop dinner", [0, 3, 4, 5, 7]),
]


def split_equal(total: int, user_ids: list[int]) -> list[ExpenseShare]:
    base = total // len(user_ids)
    remainder = total % len(user_ids)
    return [
        ExpenseShare(user_id=user_id + 1, amount_paise=base + (1 if index < remainder else 0))
        for index, user_id in enumerate(user_ids)
    ]


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        users = [User(name=name, email=email) for name, email in USERS]
        db.add_all(users)
        db.flush()

        groups: dict[str, Group] = {}
        for group_name, member_indexes in GROUPS.items():
            group = Group(name=group_name)
            db.add(group)
            db.flush()
            for user_index in member_indexes:
                db.add(GroupMember(group_id=group.id, user_id=users[user_index].id))
            groups[group_name] = group

        start = date.today() - timedelta(days=28)
        for index, (group_name, payer_index, amount, description, share_indexes) in enumerate(EXPENSES):
            expense = Expense(
                group_id=groups[group_name].id,
                payer_id=users[payer_index].id,
                amount_paise=amount,
                currency="INR",
                description=description,
                expense_date=start + timedelta(days=index),
                split_mode=SplitMode.equal_subset,
                shares=split_equal(amount, share_indexes),
            )
            db.add(expense)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
