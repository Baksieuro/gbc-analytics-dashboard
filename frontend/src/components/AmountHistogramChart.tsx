import { useId } from "react";
import type { HistogramBin } from "../lib/dashboardAnalytics";
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
  data: HistogramBin[];
  unit: string;
};

export function AmountHistogramChart({ data, unit }: Props) {
  const gradId = useId().replace(/[^a-zA-Z0-9_-]/g, "");

  return (
    <div style={{ width: "100%", height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 56 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-violet)" stopOpacity={0.9} />
              <stop offset="100%" stopColor="var(--chart-violet-dim)" stopOpacity={0.55} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.55} vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--muted)", fontSize: 10 }}
            interval={0}
            angle={-28}
            textAnchor="end"
            height={52}
            label={{
              value: `Сумма (${unit})`,
              position: "bottom",
              offset: 36,
              fill: "var(--muted)",
              fontSize: 11,
            }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "var(--muted)", fontSize: 11 }}
            width={40}
            label={{
              value: "Заказов",
              angle: -90,
              position: "insideLeft",
              style: { textAnchor: "middle", fill: "var(--muted)", fontSize: 12 },
            }}
          />
          <Tooltip
            cursor={{ fill: "rgba(167, 139, 250, 0.1)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) {
                return null;
              }
              const row = payload[0]?.payload as HistogramBin | undefined;
              if (!row) {
                return null;
              }
              return (
                <div className="chart-tooltip">
                  <div className="chart-tooltip__muted">Интервал суммы ({unit})</div>
                  <div>
                    {row.label}
                  </div>
                  <div style={{ marginTop: 6 }}>Заказов в интервале: {row.count}</div>
                </div>
              );
            }}
          />
          <Bar dataKey="count" name="Кол-во" radius={[4, 4, 0, 0]} maxBarSize={48} fill={`url(#${gradId})`} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
