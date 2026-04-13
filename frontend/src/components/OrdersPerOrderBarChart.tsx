import { useId } from "react";
import type { PerOrderBarPoint } from "../lib/dashboardAnalytics";
import { currencySymbol } from "../lib/currencySymbol";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Props = {
  data: PerOrderBarPoint[];
  unit: string;
};

function formatSum(v: number): string {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(v);
}

export function OrdersPerOrderBarChart({ data, unit }: Props) {
  const gradId = useId().replace(/[^a-zA-Z0-9_-]/g, "");

  return (
    <div className="chart-scroll chart-scroll--center">
      <div className="chart-scroll__inner" style={{ width: `${Math.max(640, data.length * 14)}px`, height: 360 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 16, right: 20, left: 8, bottom: 72 }}>
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--chart-accent)" stopOpacity={0.95} />
                <stop offset="100%" stopColor="var(--chart-accent-dim)" stopOpacity={0.65} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.55} vertical={false} />
            <XAxis
              dataKey="shortLabel"
              name="Порядковый номер"
              tick={{ fill: "var(--muted)", fontSize: 10 }}
              minTickGap={22}
              angle={-50}
              textAnchor="end"
              height={52}
              label={{
                value: "№ заказа (по дате UTC)",
                position: "bottom",
                offset: 48,
                fill: "var(--muted)",
                fontSize: 12,
              }}
            />
            <YAxis
              name="Сумма"
              tick={{ fill: "var(--muted)", fontSize: 11 }}
              tickFormatter={(v) => formatSum(Number(v))}
              width={80}
              label={{
                value: `Сумма, ${unit}`,
                angle: -90,
                position: "insideLeft",
                style: { textAnchor: "middle", fill: "var(--muted)", fontSize: 12 },
              }}
            />
            <Tooltip
              cursor={{ fill: "rgba(96, 165, 250, 0.08)" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) {
                  return null;
                }
                const row = payload[0]?.payload as PerOrderBarPoint | undefined;
                if (!row) {
                  return null;
                }
                return (
                  <div className="chart-tooltip">
                    <div className="chart-tooltip__muted">Заказ по порядку №{row.seq}</div>
                    <div>
                      CRM id: <strong>{row.retailcrm_id}</strong>
                    </div>
                    <div className="chart-tooltip__muted">Дата (UTC): {row.dayUtc}</div>
                    <div className="chart-tooltip__muted" style={{ fontSize: 11 }}>
                      {new Date(row.ordered_at).toISOString().replace("T", " ").slice(0, 19)}
                    </div>
                    <div style={{ marginTop: 6 }}>
                      {formatSum(row.amount)} {currencySymbol(row.currency)}
                    </div>
                  </div>
                );
              }}
            />
            <Bar dataKey="amount" name="Сумма" radius={[3, 3, 0, 0]} maxBarSize={28} fill={`url(#${gradId})`} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
