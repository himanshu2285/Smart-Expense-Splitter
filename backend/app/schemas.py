from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import SplitMode


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    member_ids: list[int] = Field(default_factory=list)


class GroupMemberRead(BaseModel):
    id: int
    user: UserRead

    model_config = ConfigDict(from_attributes=True)


class GroupRead(BaseModel):
    id: int
    name: str
    members: list[GroupMemberRead]

    model_config = ConfigDict(from_attributes=True)


class ExpenseShareIn(BaseModel):
    user_id: int
    amount_paise: int = Field(gt=0)


class ExpenseShareRead(BaseModel):
    user: UserRead
    amount_paise: int

    model_config = ConfigDict(from_attributes=True)


class ExpenseCreate(BaseModel):
    payer_id: int
    amount_paise: int = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    description: str = Field(min_length=1, max_length=255)
    expense_date: date
    split_mode: SplitMode
    shares: list[ExpenseShareIn] = Field(min_length=1)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        upper = value.upper()
        if not upper.isalpha():
            raise ValueError("currency must be a three-letter code")
        return upper

    @model_validator(mode="after")
    def shares_sum_to_total(self) -> "ExpenseCreate":
        if sum(share.amount_paise for share in self.shares) != self.amount_paise:
            raise ValueError("shares must sum exactly to amount_paise")
        if len({share.user_id for share in self.shares}) != len(self.shares):
            raise ValueError("duplicate users are not allowed in shares")
        return self


class ExpenseRead(BaseModel):
    id: int
    payer: UserRead
    amount_paise: int
    currency: str
    description: str
    expense_date: date
    split_mode: SplitMode
    created_at: datetime
    shares: list[ExpenseShareRead]

    model_config = ConfigDict(from_attributes=True)


class MemberBalance(BaseModel):
    user: UserRead
    net_paise: int


class SettlementTransaction(BaseModel):
    from_user: UserRead
    to_user: UserRead
    amount_paise: int


class BalanceResponse(BaseModel):
    balances: list[MemberBalance]
    settlements: list[SettlementTransaction]


class ParseExpenseRequest(BaseModel):
    text: str = Field(min_length=3, max_length=4000)
    current_user_id: int | None = None


class ParsedShareDraft(BaseModel):
    user_id: int | None = None
    name: str
    amount_paise: int | None = None
    weight: int | None = None


class ParsedExpenseDraft(BaseModel):
    confidence: float = Field(ge=0, le=1)
    status: Literal["ready", "needs_review", "failed"]
    warnings: list[str] = Field(default_factory=list)
    payer_id: int | None = None
    payer_name: str | None = None
    amount_paise: int | None = None
    currency: str = "INR"
    description: str | None = None
    expense_date: date | None = None
    split_mode: SplitMode | None = None
    shares: list[ParsedShareDraft] = Field(default_factory=list)


class ParseBillRequest(BaseModel):
    text: str = Field(min_length=3, max_length=8000)


class BillLineItem(BaseModel):
    name: str
    quantity: int = Field(default=1, ge=1)
    amount_paise: int = Field(ge=0)
    assigned_user_ids: list[int] = Field(default_factory=list)


class ParsedBillDraft(BaseModel):
    confidence: float = Field(ge=0, le=1)
    status: Literal["ready", "needs_review", "failed"]
    warnings: list[str] = Field(default_factory=list)
    merchant: str | None = None
    currency: str = "INR"
    total_paise: int | None = None
    line_items: list[BillLineItem] = Field(default_factory=list)