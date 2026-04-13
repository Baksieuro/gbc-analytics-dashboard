export function currencySymbol(code: string): string {
  const c = code.trim().toUpperCase();
  switch (c) {
    case "KZT":
      return "₸";
    case "USD":
      return "$";
    case "EUR":
      return "€";
    case "RUB":
      return "₽";
    default:
      return c || "—";
  }
}
