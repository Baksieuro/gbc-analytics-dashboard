import { useId } from "react";
import type { DayAggregate } from "../types/order";
import { currencySymbol } from "../lib/currencySymbol";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Props = {
  data: DayAggregate[];
  currencyCode: string;
};

type TooltipRenderProps = {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: unknown }>;
  label?: string;
};

function formatSum(v: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 0,
  }).format(v);
}

function OrdersTooltip({
  active,
  payload,
  label,
  unit,
}: TooltipRenderProps & { unit: string }) {
  if (!active || !payload?.length) {
    return null;
  }
  const row = payload[0]?.payload as DayAggregate | undefined;
  if (!row) {
    return null;
  }
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "0.65rem 0.85rem",
        color: "var(--text)",
      }}
    >
      <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 4 }}>
        Дата: {label}
      </div>
      <div style={{ fontSize: 14 }}>
        {formatSum(row.sumAmount)} {unit} · заказов: {row.count}
      </div>
    </div>
  );
}

export function OrdersTrendChart({ data, currencyCode }: Props) {
  const unit = currencySymbol(currencyCode);
  const gradId = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  return (
    <div style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
        >
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-stroke)" stopOpacity={0.45} />
              <stop offset="100%" stopColor="var(--chart-stroke)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.6} />
          <XAxis
            dataKey="day"
            tick={{ fill: "var(--muted)", fontSize: 11 }}
            tickMargin={8}
            label={{
              value: "Дата (UTC)",
              position: "insideBottom",
              offset: -4,
              fill: "var(--muted)",
              fontSize: 12,
            }}
          />
          <YAxis
            tick={{ fill: "var(--muted)", fontSize: 11 }}
            tickFormatter={(v) => formatSum(Number(v))}
            width={72}
            label={{
              value: `Сумма заказов, ${unit}`,
              angle: -90,
              position: "insideLeft",
              style: { textAnchor: "middle", fill: "var(--muted)", fontSize: 12 },
            }}
          />
          <Tooltip content={(p) => <OrdersTooltip {...p} unit={unit} />} />
          <Area
            type="monotone"
            dataKey="sumAmount"
            name="sumAmount"
            stroke="var(--chart-stroke)"
            strokeWidth={2}
            fill={`url(#${gradId})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
