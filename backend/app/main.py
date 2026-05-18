from datetime import date

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import Base, engine, get_db
from app.models import Expense, ExpenseShare, Group, GroupMember, User
from app.schemas import (
    BalanceResponse,
    ExpenseCreate,
    ExpenseRead,
    GroupCreate,
    GroupRead,
    ParseBillRequest,
    ParseExpenseRequest,
    ParsedBillDraft,
    ParsedExpenseDraft,
    UserCreate,
    UserRead,
)
from app.services.ai_service import parse_bill, parse_expense
from app.services.balances import compute_group_balances, compute_settlements
from app.services.expense_service import create_expense, get_group_or_404, get_user_or_404, list_expenses

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Expense Splitter API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/users", response_model=list[UserRead])
def users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.name)))


@app.post("/api/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    user = User(name=payload.name, email=str(payload.email))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already exists") from exc
    db.refresh(user)
    return user


@app.get("/api/groups", response_model=list[GroupRead])
def groups(db: Session = Depends(get_db)) -> list[Group]:
    return list(
        db.scalars(
            select(Group)
            .options(selectinload(Group.members).selectinload(GroupMember.user))
            .order_by(Group.name)
        )
    )


@app.post("/api/groups", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, db: Session = Depends(get_db)) -> Group:
    group = Group(name=payload.name)
    db.add(group)
    db.flush()
    for user_id in dict.fromkeys(payload.member_ids):
        get_user_or_404(db, user_id)
        group.members.append(GroupMember(user_id=user_id))
    db.commit()
    return get_group_or_404(db, group.id)


@app.get("/api/groups/{group_id}", response_model=GroupRead)
def group_detail(group_id: int, db: Session = Depends(get_db)) -> Group:
    return get_group_or_404(db, group_id)


@app.post("/api/groups/{group_id}/members", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def add_member(group_id: int, user_id: int, db: Session = Depends(get_db)) -> Group:
    group = get_group_or_404(db, group_id)
    get_user_or_404(db, user_id)
    if user_id not in {member.user_id for member in group.members}:
        db.add(GroupMember(group_id=group_id, user_id=user_id))
        db.commit()
    return get_group_or_404(db, group_id)


@app.get("/api/groups/{group_id}/expenses", response_model=list[ExpenseRead])
def expenses(
    group_id: int,
    payer_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> list[Expense]:
    get_group_or_404(db, group_id)
    return list_expenses(db, group_id, payer_id=payer_id, date_from=date_from, date_to=date_to, search=search)


@app.post("/api/groups/{group_id}/expenses", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def add_expense(group_id: int, payload: ExpenseCreate, db: Session = Depends(get_db)) -> Expense:
    return create_expense(db, group_id, payload)


@app.get("/api/groups/{group_id}/balances", response_model=BalanceResponse)
def balances(group_id: int, db: Session = Depends(get_db)) -> BalanceResponse:
    group = get_group_or_404(db, group_id)
    member_balances = compute_group_balances(group)
    users = [membership.user for membership in group.members]
    return BalanceResponse(
        balances=member_balances,
        settlements=compute_settlements(users, member_balances),
    )


@app.post("/api/groups/{group_id}/ai/parse-expense", response_model=ParsedExpenseDraft)
def ai_parse_expense(group_id: int, payload: ParseExpenseRequest, db: Session = Depends(get_db)) -> ParsedExpenseDraft:
    group = get_group_or_404(db, group_id)
    return parse_expense(group, payload.text, payload.current_user_id)


@app.post("/api/groups/{group_id}/ai/parse-bill", response_model=ParsedBillDraft)
def ai_parse_bill(group_id: int, payload: ParseBillRequest, db: Session = Depends(get_db)) -> ParsedBillDraft:
    get_group_or_404(db, group_id)
    return parse_bill(payload.text)