# Smart Expense Splitter

A mobile-first Splitwise-style app for groups of friends, flatmates, and travel groups. It tracks shared expenses, validates splits server-side, calculates balances, minimises settle-up transactions, and offers AI-assisted expense and bill parsing with user confirmation before anything is saved.

## Tech Stack

- Backend: FastAPI, SQLAlchemy 2, Pydantic, PostgreSQL
- Frontend: React, TypeScript, Vite
- Database: PostgreSQL, viewable in DBeaver
- AI: OpenAI structured outputs by default, deterministic fallback parser for local demos

## Quick Start

### 1. Configure environment

Copy the backend env example:

```powershell
Copy-Item backend\.env.example backend\.env
```

Set `OPENAI_API_KEY` if you want live AI parsing. Without it, the backend uses a simple fallback parser so the product flow still works.

### 2. Start Postgres

```powershell
docker compose up -d db
```

Database connection:

- Host: `localhost`
- Port: `5432`
- Database: `smart_splitter`
- User: `splitter`
- Password: `splitter`

### 3. Run backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### 4. Run frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## Useful API Calls

```powershell
curl http://localhost:8000/api/groups
curl http://localhost:8000/api/groups/1/balances
curl "http://localhost:8000/api/groups/1/expenses?search=dinner"
```

Create an expense:

```json
{
  "payer_id": 1,
  "amount_paise": 240000,
  "currency": "INR",
  "description": "Dinner at Trupti",
  "expense_date": "2026-05-18",
  "split_mode": "equal_subset",
  "shares": [
    {"user_id": 1, "amount_paise": 80000},
    {"user_id": 2, "amount_paise": 80000},
    {"user_id": 3, "amount_paise": 80000}
  ]
}
```

## Notes

- Money is always stored as integer paise.
- Expense shares must sum exactly to the expense total.
- AI parsing always returns a draft. The user must review and confirm before saving.
- See [ARCHITECTURE.md](ARCHITECTURE.md) for the settle-up algorithm and design decisions.