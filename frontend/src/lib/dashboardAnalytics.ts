import type { DayAggregate, OrderRow } from "../types/order";
import { aggregateOrdersByDay, toNumber } from "./aggregateOrdersByDay";

export type PerOrderBarPoint = {
  seq: number;
  shortLabel: string;
  retailcrm_id: number;
  currency: string;
  amount: number;
  ordered_at: string;
  dayUtc: string;
};

export type HistogramBin = {
  label: string;
  count: number;
  binStart: number;
  binEnd: number;
};

export type OrderKpis = {
  count: number;
  sum: number;
  avg: number;
  min: number;
  max: number;
  currency: string;
};

function dominantCurrency(rows: OrderRow[]): string {
  const counts = new Map<string, number>();
  for (const r of rows) {
    const c = (r.currency ?? "").trim().toUpperCase() || "KZT";
    counts.set(c, (counts.get(c) ?? 0) + 1);
  }
  let best = "KZT";
  let max = 0;
  for (const [code, n] of counts) {
    if (n > max) {
      max = n;
      best = code;
    }
  }
  return best;
}

function dayKeyUtc(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "—";
  }
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function isDenseSameDayCluster(rows: OrderRow[]): boolean {
  if (rows.length === 0) {
    return false;
  }
  const agg = aggregateOrdersByDay(rows);
  if (agg.length <= 1) {
    return true;
  }
  const maxCount = Math.max(...agg.map((a) => a.count));
  return maxCount / rows.length >= 0.45;
}

export function preparePerOrderBars(rows: OrderRow[]): PerOrderBarPoint[] {
  const sorted = [...rows].sort((a, b) => {
    const ta = new Date(a.ordered_at).getTime();
    const tb = new Date(b.ordered_at).getTime();
    if (ta !== tb) {
      return ta - tb;
    }
    return a.retailcrm_id - b.retailcrm_id;
  });
  return sorted.map((row, i) => ({
    seq: i + 1,
    shortLabel: String(i + 1),
    retailcrm_id: row.retailcrm_id,
    currency: (row.currency ?? "").trim().toUpperCase() || "KZT",
    amount: toNumber(row.total_amount),
    ordered_at: row.ordered_at,
    dayUtc: dayKeyUtc(row.ordered_at),
  }));
}

export function amountHistogram(rows: OrderRow[], binCount = 12): HistogramBin[] {
  const amounts = rows.map((r) => toNumber(r.total_amount)).filter((n) => Number.isFinite(n));
  if (amounts.length === 0) {
    return [];
  }
  const minA = Math.min(...amounts);
  const maxA = Math.max(...amounts);
  if (minA === maxA) {
    return [
      {
        label: formatBinLabel(minA, maxA),
        count: amounts.length,
        binStart: minA,
        binEnd: maxA,
      },
    ];
  }
  const step = (maxA - minA) / binCount;
  const bins = Array.from({ length: binCount }, (_, i) => ({
    binStart: minA + i * step,
    binEnd: minA + (i + 1) * step,
    count: 0,
    label: "",
  }));
  for (const a of amounts) {
    let idx = Math.floor((a - minA) / step);
    if (idx >= binCount) {
      idx = binCount - 1;
    }
    if (idx < 0) {
      idx = 0;
    }
    bins[idx].count += 1;
  }
  return bins.map((b) => ({
    ...b,
    label: formatBinLabel(b.binStart, b.binEnd),
  }));
}

function formatBinLabel(start: number, end: number): string {
  const fmt = (n: number) =>
    new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(Math.round(n));
  return `${fmt(start)}–${fmt(end)}`;
}

export function computeOrderKpis(rows: OrderRow[]): OrderKpis | null {
  if (rows.length === 0) {
    return null;
  }
  const amounts = rows.map((r) => toNumber(r.total_amount));
  const sum = amounts.reduce((a, b) => a + b, 0);
  return {
    count: rows.length,
    sum,
    avg: sum / amounts.length,
    min: Math.min(...amounts),
    max: Math.max(...amounts),
    currency: dominantCurrency(rows),
  };
}

export function shouldShowDailyTrend(agg: DayAggregate[]): boolean {
  return agg.length >= 2;
}
