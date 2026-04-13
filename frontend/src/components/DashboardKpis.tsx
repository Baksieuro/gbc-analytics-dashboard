import type { OrderKpis } from "../lib/dashboardAnalytics";
import { currencySymbol } from "../lib/currencySymbol";

function fmt(n: number, fraction = 0): string {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: fraction }).format(n);
}

type Props = {
  kpis: OrderKpis;
};

export function DashboardKpis({ kpis }: Props) {
  const sym = currencySymbol(kpis.currency);
  return (
    <div className="kpi-grid">
      <div className="kpi-card">
        <div className="kpi-card__label">Заказов</div>
        <div className="kpi-card__value">{fmt(kpis.count)}</div>
      </div>
      <div className="kpi-card">
        <div className="kpi-card__label">Сумма</div>
        <div className="kpi-card__value">
          {fmt(kpis.sum)} {sym}
        </div>
      </div>
      <div className="kpi-card">
        <div className="kpi-card__label">Средний чек</div>
        <div className="kpi-card__value">
          {fmt(kpis.avg)} {sym}
        </div>
      </div>
      <div className="kpi-card">
        <div className="kpi-card__label">Мин. / макс.</div>
        <div className="kpi-card__value kpi-card__value--stack">
          <span>
            {fmt(kpis.min)} {sym}
          </span>
          <span className="kpi-card__sep">—</span>
          <span>
            {fmt(kpis.max)} {sym}
          </span>
        </div>
      </div>
    </div>
  );
}
