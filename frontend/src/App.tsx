import { useEffect, useMemo, useState } from "react";
import { Calendar, Check, IndianRupee, Plus, ReceiptText, Search, Sparkles, Users } from "lucide-react";
import { api } from "./api";
import type { BalanceResponse, Expense, ExpenseFormState, Group, ParsedBill, ParsedExpense, User } from "./types";
import { money, todayIsoDate } from "./utils";
import "./App.css";

const defaultExpenseText = "I paid 2400 for dinner last night, split equally between me, Aman and Priya";
const defaultBillText = [
  "Trupti Restaurant",
  "Paneer tikka 420",
  "Masala dosa 260",
  "Fresh lime soda 180",
  "Dessert 300",
  "GST 58",
  "Total 1218",
].join("\n");

const initialForm: ExpenseFormState = {
  payer_id: "",
  amount_rupees: "",
  description: "",
  expense_date: todayIsoDate(),
  split_mode: "equal_all",
  selected_user_ids: [],
};

export default function App() {
  const [users, setUsers] = useState<User[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [balances, setBalances] = useState<BalanceResponse>({ balances: [], settlements: [] });
  const [search, setSearch] = useState("");
  const [payerFilter, setPayerFilter] = useState("");
  const [error, setError] = useState("");
  const [nlText, setNlText] = useState(defaultExpenseText);
  const [billText, setBillText] = useState(defaultBillText);
  const [parsedExpense, setParsedExpense] = useState<ParsedExpense | null>(null);
  const [parsedBill, setParsedBill] = useState<ParsedBill | null>(null);
  const [form, setForm] = useState<ExpenseFormState>(initialForm);

  const selectedGroup = groups.find((group: Group) => group.id === selectedGroupId) ?? null;
  const members = selectedGroup?.members.map((member: any) => member.user) ?? [];

  async function loadBase() {
    const [loadedUsers, loadedGroups] = await Promise.all([api<User[]>("/users"), api<Group[]>("/groups")]);
    setUsers(loadedUsers);
    setGroups(loadedGroups);
    setCurrentUserId(loadedUsers[0]?.id ?? null);
    setSelectedGroupId(loadedGroups[0]?.id ?? null);
  }

  async function loadGroupData(groupId: number) {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (payerFilter) params.set("payer_id", payerFilter);

    const [loadedExpenses, loadedBalances] = await Promise.all([
      api<Expense[]>(`/groups/${groupId}/expenses?${params}`),
      api<BalanceResponse>(`/groups/${groupId}/balances`),
    ]);

    setExpenses(loadedExpenses);
    setBalances(loadedBalances);
  }

  useEffect(() => {
    loadBase().catch((caught: Error) => setError(caught.message));
  }, []);

  useEffect(() => {
    if (selectedGroupId) {
      loadGroupData(selectedGroupId).catch((caught: Error) => setError(caught.message));
    }
  }, [selectedGroupId, search, payerFilter]);

  useEffect(() => {
    if (selectedGroup && members.length) {
      setForm((previous: ExpenseFormState) => ({
        ...previous,
        payer_id: String(previous.payer_id || currentUserId || members[0].id),
        selected_user_ids: members.map((member: User) => member.id),
      }));
    }
  }, [selectedGroupId, currentUserId]);

  const splitPreview = useMemo(() => {
    const amountPaise = Math.round(Number(form.amount_rupees || 0) * 100);
    const selectedIds = form.split_mode === "equal_all" ? members.map((member: User) => member.id) : form.selected_user_ids;

    if (!amountPaise || !selectedIds.length) return [];

    const base = Math.floor(amountPaise / selectedIds.length);
    const remainder = amountPaise % selectedIds.length;

    return selectedIds.map((userId: number, index: number) => ({
      user_id: userId,
      amount_paise: base + (index < remainder ? 1 : 0),
    }));
  }, [form, members]);

  async function saveExpense() {
    if (!selectedGroupId) return;

    await api(`/groups/${selectedGroupId}/expenses`, {
      method: "POST",
      body: JSON.stringify({
        payer_id: Number(form.payer_id),
        amount_paise: Math.round(Number(form.amount_rupees) * 100),
        currency: "INR",
        description: form.description,
        expense_date: form.expense_date,
        split_mode: form.split_mode,
        shares: splitPreview,
      }),
    });

    setForm((previous: ExpenseFormState) => ({ ...previous, amount_rupees: "", description: "" }));
    await loadGroupData(selectedGroupId);
  }

  async function parseNaturalLanguage() {
    if (!selectedGroupId) return;

    const draft = await api<ParsedExpense>(`/groups/${selectedGroupId}/ai/parse-expense`, {
      method: "POST",
      body: JSON.stringify({ text: nlText, current_user_id: currentUserId }),
    });

    setParsedExpense(draft);

    if (draft.amount_paise && draft.payer_id && draft.shares.length) {
      setForm({
        payer_id: String(draft.payer_id),
        amount_rupees: String(draft.amount_paise / 100),
        description: draft.description ?? "",
        expense_date: draft.expense_date ?? todayIsoDate(),
        split_mode: "equal_subset",
        selected_user_ids: draft.shares.flatMap((share: any) => (share.user_id ? [share.user_id] : [])),
      });
    }
  }

  async function parseBill() {
    if (!selectedGroupId) return;

    setParsedBill(
      await api<ParsedBill>(`/groups/${selectedGroupId}/ai/parse-bill`, {
        method: "POST",
        body: JSON.stringify({ text: billText }),
      }),
    );
  }

  function toggleFormMember(userId: number) {
    setForm((previous: ExpenseFormState) => ({
      ...previous,
      selected_user_ids: previous.selected_user_ids.includes(userId)
        ? previous.selected_user_ids.filter((id: number) => id !== userId)
        : [...previous.selected_user_ids, userId],
    }));
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Smart Expense Splitter</p>
          <h1>{selectedGroup?.name ?? "Groups"}</h1>
        </div>
        <select value={currentUserId ?? ""} onChange={(event) => setCurrentUserId(Number(event.target.value))}>
          {users.map((user: User) => (
            <option key={user.id} value={user.id}>
              {user.name}
            </option>
          ))}
        </select>
      </header>

      {error && <div className="notice danger">{error}</div>}

      <nav className="group-tabs">
        {groups.map((group: Group) => (
          <button className={group.id === selectedGroupId ? "active" : ""} key={group.id} onClick={() => setSelectedGroupId(group.id)}>
            <Users size={16} />
            {group.name}
          </button>
        ))}
      </nav>

      <section className="grid">
        <div className="panel balance-panel">
          <div className="panel-title">
            <IndianRupee size={18} />
            <h2>Balances</h2>
          </div>
          <div className="balances">
            {balances.balances.map((balance: any) => (
              <div className="balance-row" key={balance.user.id}>
                <span>{balance.user.name}</span>
                <strong className={balance.net_paise >= 0 ? "positive" : "negative"}>{money(balance.net_paise)}</strong>
              </div>
            ))}
          </div>
          <h3>Settle up</h3>
          {balances.settlements.length === 0 && <p className="muted">Everyone is settled.</p>}
          {balances.settlements.map((settlement: any, index: number) => (
            <div className="settlement" key={`${settlement.from_user.id}-${settlement.to_user.id}-${index}`}>
              <span>{settlement.from_user.name}</span>
              <span>pays</span>
              <strong>{settlement.to_user.name}</strong>
              <b>{money(settlement.amount_paise)}</b>
            </div>
          ))}
        </div>

        <div className="panel">
          <div className="panel-title">
            <Plus size={18} />
            <h2>Add expense</h2>
          </div>
          <div className="form-grid">
            <label>
              Payer
              <select value={form.payer_id} onChange={(event) => setForm({ ...form, payer_id: event.target.value })}>
                {members.map((member: User) => (
                  <option key={member.id} value={member.id}>
                    {member.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Amount
              <input inputMode="decimal" value={form.amount_rupees} onChange={(event) => setForm({ ...form, amount_rupees: event.target.value })} />
            </label>
            <label className="wide">
              Description
              <input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
            </label>
            <label>
              Date
              <input type="date" value={form.expense_date} onChange={(event) => setForm({ ...form, expense_date: event.target.value })} />
            </label>
            <label>
              Split
              <select value={form.split_mode} onChange={(event) => setForm({ ...form, split_mode: event.target.value as ExpenseFormState["split_mode"] })}>
                <option value="equal_all">Equal all</option>
                <option value="equal_subset">Equal subset</option>
              </select>
            </label>
          </div>
          <div className="chips">
            {members.map((member: User) => (
              <button
                disabled={form.split_mode === "equal_all"}
                className={form.selected_user_ids.includes(member.id) ? "chip selected" : "chip"}
                key={member.id}
                onClick={() => toggleFormMember(member.id)}
              >
                {member.name}
              </button>
            ))}
          </div>
          <button className="primary" onClick={() => saveExpense().catch((caught: Error) => setError(caught.message))}>
            <Check size={18} />
            Save expense
          </button>
        </div>
      </section>

      <section className="ai-grid">
        <div className="panel">
          <div className="panel-title">
            <Sparkles size={18} />
            <h2>Natural language</h2>
          </div>
          <textarea value={nlText} onChange={(event) => setNlText(event.target.value)} />
          <button className="secondary" onClick={() => parseNaturalLanguage().catch((caught: Error) => setError(caught.message))}>
            Parse draft
          </button>
          {parsedExpense && (
            <div className="draft">
              <b>{parsedExpense.status}</b>
              <span>{Math.round(parsedExpense.confidence * 100)}% confidence</span>
              {parsedExpense.warnings.map((warning: string) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-title">
            <ReceiptText size={18} />
            <h2>Bill parser</h2>
          </div>
          <textarea value={billText} onChange={(event) => setBillText(event.target.value)} />
          <button className="secondary" onClick={() => parseBill().catch((caught: Error) => setError(caught.message))}>
            Parse bill
          </button>
          {parsedBill && (
            <div className="bill-items">
              <b>{parsedBill.merchant ?? "Bill"}</b>
              {parsedBill.line_items.map((item: any) => (
                <div key={item.name}>
                  <span>{item.name}</span>
                  <strong>{money(item.amount_paise)}</strong>
                </div>
              ))}
              {parsedBill.total_paise && <strong>Total {money(parsedBill.total_paise)}</strong>}
            </div>
          )}
        </div>
      </section>

      <section className="panel history">
        <div className="history-head">
          <div className="panel-title">
            <Calendar size={18} />
            <h2>Expense history</h2>
          </div>
          <label className="search">
            <Search size={16} />
            <input placeholder="Search" value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <select value={payerFilter} onChange={(event) => setPayerFilter(event.target.value)}>
            <option value="">All payers</option>
            {members.map((member: User) => (
              <option key={member.id} value={member.id}>
                {member.name}
              </option>
            ))}
          </select>
        </div>
        <div className="expense-list">
          {expenses.map((expense: Expense) => (
            <article key={expense.id} className="expense-card">
              <div>
                <h3>{expense.description}</h3>
                <p>
                  {expense.payer.name} paid {money(expense.amount_paise)} on {expense.expense_date}
                </p>
              </div>
              <div className="share-list">
                {expense.shares.map((share: any) => (
                  <span key={share.user.id}>
                    {share.user.name}: {money(share.amount_paise)}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
