import type { DayAggregate, OrderRow } from "../types/order";

export function toNumber(value: number | string): number {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }
  const n = Number.parseFloat(String(value).replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}

function dayKeyUtc(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "invalid";
  }
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function aggregateOrdersByDay(rows: OrderRow[]): DayAggregate[] {
  const map = new Map<string, { sum: number; count: number }>();
  for (const row of rows) {
    const key = dayKeyUtc(row.ordered_at);
    if (key === "invalid") {
      continue;
    }
    const prev = map.get(key) ?? { sum: 0, count: 0 };
    prev.sum += toNumber(row.total_amount);
    prev.count += 1;
    map.set(key, prev);
  }
  return [...map.entries()]
    .map(([day, { sum, count }]) => ({ day, sumAmount: sum, count }))
    .sort((a, b) => a.day.localeCompare(b.day));
}
