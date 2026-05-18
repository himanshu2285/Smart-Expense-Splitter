# Architecture

## Product Shape

Smart Expense Splitter is a classic client/server app:

- React mobile-first frontend for group selection, expense entry, balances, history, natural-language parsing, and bill assignment.
- FastAPI REST backend with strict Pydantic request validation.
- PostgreSQL schema with normalized users, groups, memberships, expenses, and shares.
- Optional OpenAI integration for structured expense and bill parsing.

The frontend never saves an AI-generated expense directly. AI output becomes an editable draft, then the normal expense creation endpoint validates and persists it.

## Data Model

- `users`: profile records. The current app uses a user switcher, but IDs and email uniqueness are compatible with future auth.
- `groups`: named expense containers.
- `group_members`: many-to-many relationship between users and groups.
- `expenses`: payer, amount, currency, description, date, and split mode.
- `expense_shares`: the exact amount owed by each participant for an expense.

Money is stored as integer paise. No floats are used for persisted money or balance calculations.

## Split Validation

All expense creation goes through server validation:

1. Amount must be positive.
2. Currency must be three uppercase letters.
3. Payer must belong to the group.
4. Every share user must belong to the group.
5. Share amounts must be positive.
6. Shares must sum exactly to `amount_paise`.

The frontend also validates for responsiveness, but the backend is the source of truth.

## Balance Calculation

For each group, the backend computes a net balance per member:

```text
net[user] += amount paid by user
net[user] -= amount owed by user through shares
```

Positive net means the member should receive money. Negative net means the member owes money.

## Settle-Up Algorithm

The settle-up endpoint converts net balances into a minimal practical list of transactions using a greedy debtor/creditor matching algorithm:

1. Build two lists:
   - debtors: users with negative net balances
   - creditors: users with positive net balances
2. Sort debtors by amount owed and creditors by amount receivable, descending.
3. Match the largest debtor with the largest creditor.
4. Emit one transaction for `min(debt, credit)`.
5. Reduce both balances and continue until all balances are zero.

This produces at most `n - 1` transactions for the common case and is optimal for the standard expense-settlement problem where balances are already netted and there are no constraints on who can pay whom. It avoids graph cycles and minimizes redundant back-and-forth payments.

## AI Parsing

AI features are structured-output flows:

- Natural-language expense parsing returns payer, amount, description, date hint, participant names, adjustments, and confidence.
- Bill parsing returns merchant, line items, tax/service charges if detected, total, and confidence.

The backend maps names to group members where possible and returns warnings for ambiguity. If confidence is low, required fields are missing, or totals cannot be reconciled, the API returns a draft with warnings rather than saving anything.

OpenAI is used when `OPENAI_API_KEY` is configured. A deterministic fallback parser is included for demos and offline development, but production should use a real model with the JSON schema in `app/services/ai_service.py`.

## REST API

Important endpoints:

- `GET /api/users`
- `GET /api/groups`
- `POST /api/groups`
- `GET /api/groups/{group_id}`
- `POST /api/groups/{group_id}/members`
- `GET /api/groups/{group_id}/expenses`
- `POST /api/groups/{group_id}/expenses`
- `GET /api/groups/{group_id}/balances`
- `POST /api/groups/{group_id}/ai/parse-expense`
- `POST /api/groups/{group_id}/ai/parse-bill`

All endpoints are curl/Postman friendly and return appropriate HTTP status codes.