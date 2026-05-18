import json
import re
from datetime import date, timedelta
from typing import Any

from openai import OpenAI

from app.config import settings
from app.models import Group, SplitMode
from app.schemas import BillLineItem, ParsedBillDraft, ParsedExpenseDraft, ParsedShareDraft


def _money_to_paise(value: str) -> int:
    normalized = value.replace(",", "")
    return int(round(float(normalized) * 100))


def _name_map(group: Group) -> dict[str, int]:
    return {membership.user.name.lower(): membership.user_id for membership in group.members}


def _resolve_name(group: Group, name: str) -> int | None:
    lower = name.strip().lower()
    names = _name_map(group)
    if lower in names:
        return names[lower]
    for member_name, user_id in names.items():
        if lower and (lower in member_name or member_name in lower):
            return user_id
    return None


def _today_from_text(text: str) -> date:
    lower = text.lower()
    if "last night" in lower or "yesterday" in lower:
        return date.today() - timedelta(days=1)
    return date.today()


def fallback_parse_expense(group: Group, text: str, current_user_id: int | None) -> ParsedExpenseDraft:
    warnings: list[str] = []
    amount_match = re.search(r"(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
    amount_paise = _money_to_paise(amount_match.group(1)) if amount_match else None
    if amount_paise is None:
        warnings.append("Could not find a clear amount.")

    lower = text.lower()
    payer_id = current_user_id
    payer_name = None
    if "i paid" in lower and current_user_id:
        payer_name = next((m.user.name for m in group.members if m.user_id == current_user_id), None)
    else:
        for membership in group.members:
            if f"{membership.user.name.lower()} paid" in lower or f"paid by {membership.user.name.lower()}" in lower:
                payer_id = membership.user_id
                payer_name = membership.user.name
                break

    participant_ids: list[int] = []
    for membership in group.members:
        if membership.user.name.lower() in lower:
            participant_ids.append(membership.user_id)
    if " me" in f" {lower}" and current_user_id:
        participant_ids.append(current_user_id)
    participant_ids = list(dict.fromkeys(participant_ids))

    if not participant_ids:
        participant_ids = [membership.user_id for membership in group.members]
        warnings.append("No participants were detected, so all group members were selected.")

    shares: list[ParsedShareDraft] = []
    if amount_paise and participant_ids:
        base = amount_paise // len(participant_ids)
        remainder = amount_paise % len(participant_ids)
        for index, user_id in enumerate(participant_ids):
            user_name = next(m.user.name for m in group.members if m.user_id == user_id)
            shares.append(
                ParsedShareDraft(
                    user_id=user_id,
                    name=user_name,
                    amount_paise=base + (1 if index < remainder else 0),
                )
            )

    status = "ready" if amount_paise and payer_id and shares and not warnings else "needs_review"
    return ParsedExpenseDraft(
        confidence=0.55 if status == "ready" else 0.35,
        status=status,
        warnings=warnings,
        payer_id=payer_id,
        payer_name=payer_name,
        amount_paise=amount_paise,
        description=text[:80],
        expense_date=_today_from_text(text),
        split_mode=SplitMode.equal_subset if participant_ids else SplitMode.equal_all,
        shares=shares,
    )


def fallback_parse_bill(text: str) -> ParsedBillDraft:
    items: list[BillLineItem] = []
    total_paise: int | None = None
    merchant = text.strip().splitlines()[0][:80] if text.strip() else None

    for line in text.splitlines():
        match = re.search(r"(.+?)\s+([0-9][0-9,]*(?:\.[0-9]{1,2})?)$", line.strip())
        if not match:
            continue
        name = match.group(1).strip(" -:\t")
        amount = _money_to_paise(match.group(2))
        if name.lower() in {"total", "grand total", "amount due", "net amount"}:
            total_paise = amount
        elif amount > 0 and not re.search(r"subtotal|tax|gst|service", name, re.IGNORECASE):
            items.append(BillLineItem(name=name[:120], amount_paise=amount))

    if total_paise is None and items:
        total_paise = sum(item.amount_paise for item in items)

    warnings = []
    if not items:
        warnings.append("Could not detect itemized bill lines.")
    if total_paise is None:
        warnings.append("Could not detect bill total.")

    return ParsedBillDraft(
        confidence=0.6 if items and total_paise else 0.3,
        status="ready" if items and total_paise else "needs_review",
        warnings=warnings,
        merchant=merchant,
        total_paise=total_paise,
        line_items=items,
    )


def _openai_client() -> OpenAI | None:
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def _safe_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def parse_expense(group: Group, text: str, current_user_id: int | None) -> ParsedExpenseDraft:
    client = _openai_client()
    if not client:
        return fallback_parse_expense(group, text, current_user_id)

    members = [{"id": m.user_id, "name": m.user.name, "email": m.user.email} for m in group.members]
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract a shared expense as JSON. Money must be integer paise. "
                    "Return confidence 0-1, warnings, payer_id, amount_paise, currency, "
                    "description, expense_date YYYY-MM-DD, split_mode, and shares with user_id, name, amount_paise. "
                    "Use only provided member IDs. If unsure, add warnings and lower confidence."
                ),
            },
            {"role": "user", "content": json.dumps({"members": members, "current_user_id": current_user_id, "text": text})},
        ],
    )
    raw = _safe_json(response.choices[0].message.content or "{}")
    draft = ParsedExpenseDraft.model_validate(raw)
    if draft.confidence < 0.65:
        draft.status = "needs_review"
        draft.warnings.append("Low confidence parse. Please review before saving.")
    return draft


def parse_bill(text: str) -> ParsedBillDraft:
    client = _openai_client()
    if not client:
        return fallback_parse_bill(text)

    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Parse receipt text as JSON with confidence, status, warnings, merchant, currency, "
                    "total_paise, and line_items [{name, quantity, amount_paise}]. Do not invent missing totals."
                ),
            },
            {"role": "user", "content": text},
        ],
    )
    raw = _safe_json(response.choices[0].message.content or "{}")
    draft = ParsedBillDraft.model_validate(raw)
    if draft.confidence < 0.65:
        draft.status = "needs_review"
        draft.warnings.append("Low confidence bill parse. Please review the bill details.")
    return draft
