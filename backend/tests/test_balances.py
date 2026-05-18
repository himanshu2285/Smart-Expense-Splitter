from app.models import User
from app.schemas import MemberBalance, UserRead
from app.services.balances import compute_settlements


def test_compute_settlements_minimises_transactions() -> None:
    users = [
        User(id=1, name="Aman", email="aman@example.com"),
        User(id=2, name="Priya", email="priya@example.com"),
        User(id=3, name="Neha", email="neha@example.com"),
    ]
    balances = [
        MemberBalance(user=UserRead(id=1, name="Aman", email="aman@example.com"), net_paise=-5000),
        MemberBalance(user=UserRead(id=2, name="Priya", email="priya@example.com"), net_paise=-3000),
        MemberBalance(user=UserRead(id=3, name="Neha", email="neha@example.com"), net_paise=8000),
    ]

    settlements = compute_settlements(users, balances)

    assert len(settlements) == 2
    assert sum(transaction.amount_paise for transaction in settlements) == 8000
    assert {transaction.to_user.name for transaction in settlements} == {"Neha"}