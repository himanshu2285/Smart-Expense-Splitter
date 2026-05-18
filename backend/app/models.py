from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SplitMode(StrEnum):
    equal_all = "equal_all"
    equal_subset = "equal_subset"
    custom_amounts = "custom_amounts"
    share_weights = "share_weights"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    memberships: Mapped[list["GroupMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    paid_expenses: Mapped[list["Expense"]] = relationship(back_populates="payer")


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["GroupMember"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped[Group] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    payer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    split_mode: Mapped[SplitMode] = mapped_column(Enum(SplitMode), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped[Group] = relationship(back_populates="expenses")
    payer: Mapped[User] = relationship(back_populates="paid_expenses")
    shares: Mapped[list["ExpenseShare"]] = relationship(back_populates="expense", cascade="all, delete-orphan")


class ExpenseShare(Base):
    __tablename__ = "expense_shares"
    __table_args__ = (UniqueConstraint("expense_id", "user_id", name="uq_expense_share_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)

    expense: Mapped[Expense] = relationship(back_populates="shares")
    user: Mapped[User] = relationship()