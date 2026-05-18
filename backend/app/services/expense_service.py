from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Expense, ExpenseShare, Group, GroupMember, User
from app.schemas import ExpenseCreate


def get_group_or_404(db: Session, group_id: int) -> Group:
    group = db.scalar(
        select(Group)
        .where(Group.id == group_id)
        .options(
            selectinload(Group.members).selectinload(GroupMember.user),
            selectinload(Group.expenses).selectinload(Expense.payer),
            selectinload(Group.expenses).selectinload(Expense.shares).selectinload(ExpenseShare.user),
        )
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="group not found")
    return group


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


def create_expense(db: Session, group_id: int, payload: ExpenseCreate) -> Expense:
    group = get_group_or_404(db, group_id)
    member_ids = {membership.user_id for membership in group.members}

    if payload.payer_id not in member_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payer must belong to group")

    invalid_share_users = [share.user_id for share in payload.shares if share.user_id not in member_ids]
    if invalid_share_users:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"share users must belong to group: {invalid_share_users}",
        )

    expense = Expense(
        group_id=group_id,
        payer_id=payload.payer_id,
        amount_paise=payload.amount_paise,
        currency=payload.currency,
        description=payload.description,
        expense_date=payload.expense_date,
        split_mode=payload.split_mode,
        shares=[
            ExpenseShare(user_id=share.user_id, amount_paise=share.amount_paise)
            for share in payload.shares
        ],
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return db.scalar(
        select(Expense)
        .where(Expense.id == expense.id)
        .options(selectinload(Expense.payer), selectinload(Expense.shares).selectinload(ExpenseShare.user))
    )


def list_expenses(
    db: Session,
    group_id: int,
    payer_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
) -> list[Expense]:
    query = (
        select(Expense)
        .where(Expense.group_id == group_id)
        .options(selectinload(Expense.payer), selectinload(Expense.shares).selectinload(ExpenseShare.user))
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
    )
    if payer_id:
        query = query.where(Expense.payer_id == payer_id)
    if date_from:
        query = query.where(Expense.expense_date >= date_from)
    if date_to:
        query = query.where(Expense.expense_date <= date_to)
    if search:
        query = query.where(Expense.description.ilike(f"%{search}%"))
    return list(db.scalars(query))
