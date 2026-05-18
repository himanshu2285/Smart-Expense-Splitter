from app.models import Group, User
from app.schemas import MemberBalance, SettlementTransaction, UserRead


def compute_group_balances(group: Group) -> list[MemberBalance]:
    users = [membership.user for membership in group.members]
    nets = {user.id: 0 for user in users}

    for expense in group.expenses:
        nets[expense.payer_id] += expense.amount_paise
        for share in expense.shares:
            nets[share.user_id] -= share.amount_paise

    users_by_id = {user.id: user for user in users}
    return [
        MemberBalance(user=UserRead.model_validate(users_by_id[user_id]), net_paise=net)
        for user_id, net in sorted(nets.items(), key=lambda item: users_by_id[item[0]].name)
    ]


def compute_settlements(users: list[User], balances: list[MemberBalance]) -> list[SettlementTransaction]:
    users_by_id = {user.id: user for user in users}
    debtors = [
        {"user_id": balance.user.id, "amount": -balance.net_paise}
        for balance in balances
        if balance.net_paise < 0
    ]
    creditors = [
        {"user_id": balance.user.id, "amount": balance.net_paise}
        for balance in balances
        if balance.net_paise > 0
    ]

    debtors.sort(key=lambda item: item["amount"], reverse=True)
    creditors.sort(key=lambda item: item["amount"], reverse=True)

    transactions: list[SettlementTransaction] = []
    debtor_index = 0
    creditor_index = 0

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor = debtors[debtor_index]
        creditor = creditors[creditor_index]
        amount = min(debtor["amount"], creditor["amount"])

        if amount > 0:
            transactions.append(
                SettlementTransaction(
                    from_user=UserRead.model_validate(users_by_id[debtor["user_id"]]),
                    to_user=UserRead.model_validate(users_by_id[creditor["user_id"]]),
                    amount_paise=amount,
                )
            )

        debtor["amount"] -= amount
        creditor["amount"] -= amount

        if debtor["amount"] == 0:
            debtor_index += 1
        if creditor["amount"] == 0:
            creditor_index += 1

    return transactions
