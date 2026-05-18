export type User = {
  id: number;
  name: string;
  email: string;
};

export type GroupMember = {
  id: number;
  user: User;
};

export type Group = {
  id: number;
  name: string;
  members: GroupMember[];
};

export type ExpenseShare = {
  user: User;
  amount_paise: number;
};

export type Expense = {
  id: number;
  payer: User;
  amount_paise: number;
  currency: string;
  description: string;
  expense_date: string;
  split_mode: string;
  shares: ExpenseShare[];
};

export type Balance = {
  user: User;
  net_paise: number;
};

export type Settlement = {
  from_user: User;
  to_user: User;
  amount_paise: number;
};

export type BalanceResponse = {
  balances: Balance[];
  settlements: Settlement[];
};

export type ParsedExpense = {
  confidence: number;
  status: "ready" | "needs_review" | "failed";
  warnings: string[];
  payer_id: number | null;
  amount_paise: number | null;
  currency: string;
  description: string | null;
  expense_date: string | null;
  split_mode: string | null;
  shares: {
    user_id: number | null;
    name: string;
    amount_paise: number | null;
  }[];
};

export type ParsedBill = {
  confidence: number;
  status: "ready" | "needs_review" | "failed";
  warnings: string[];
  merchant: string | null;
  total_paise: number | null;
  line_items: {
    name: string;
    quantity: number;
    amount_paise: number;
    assigned_user_ids: number[];
  }[];
};

export type ExpenseFormState = {
  payer_id: string;
  amount_rupees: string;
  description: string;
  expense_date: string;
  split_mode: "equal_all" | "equal_subset";
  selected_user_ids: number[];
};
