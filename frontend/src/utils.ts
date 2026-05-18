export function money(paise: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
  }).format(paise / 100);
}

export function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}