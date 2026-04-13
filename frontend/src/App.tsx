import { useEffect, useMemo, useState } from "react";
import { fetchOrdersForChart } from "./api/fetchOrders";
import { AmountHistogramChart } from "./components/AmountHistogramChart";
import { DashboardKpis } from "./components/DashboardKpis";
import { OrdersPerOrderBarChart } from "./components/OrdersPerOrderBarChart";
import { OrdersTrendChart } from "./components/OrdersTrendChart";
import { aggregateOrdersByDay } from "./lib/aggregateOrdersByDay";
import {
  amountHistogram,
  computeOrderKpis,
  isDenseSameDayCluster,
  preparePerOrderBars,
  shouldShowDailyTrend,
} from "./lib/dashboardAnalytics";
import { currencySymbol } from "./lib/currencySymbol";
import { createOrdersClient } from "./lib/supabase";
import type { OrderRow } from "./types/order";
import "./App.css";

type LoadState =
  | { status: "idle" | "loading" }
  | { status: "error"; message: string }
  | { status: "ready" };

export default function App() {
  const [load, setLoad] = useState<LoadState>({ status: "idle" });
  const [rows, setRows] = useState<OrderRow[]>([]);

  const client = useMemo(() => createOrdersClient(), []);

  const daily = useMemo(() => aggregateOrdersByDay(rows), [rows]);
  const denseSameDay = useMemo(() => isDenseSameDayCluster(rows), [rows]);
  const kpis = useMemo(() => computeOrderKpis(rows), [rows]);
  const perOrder = useMemo(
    () => preparePerOrderBars(rows, kpis?.currency),
    [rows, kpis?.currency],
  );
  const histogram = useMemo(() => amountHistogram(rows, 12), [rows]);
  const showDaily = useMemo(() => shouldShowDailyTrend(daily), [daily]);
  const amountUnit = useMemo(
    () => currencySymbol(kpis?.currency ?? "KZT"),
    [kpis?.currency],
  );

  useEffect(() => {
    if (!client) {
      setLoad({
        status: "error",
        message: "Подключение не настроено: задайте URL и ключ Supabase в переменных окружения.",
      });
      return;
    }

    let cancelled = false;
    setLoad({ status: "loading" });

    void (async () => {
      const { rows: fetched, errorMessage } = await fetchOrdersForChart(client);
      if (cancelled) {
        return;
      }
      if (errorMessage) {
        setLoad({ status: "error", message: errorMessage });
        setRows([]);
        return;
      }
      setRows(fetched);
      setLoad({ status: "ready" });
    })();

    return () => {
      cancelled = true;
    };
  }, [client]);

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">Дашборд заказов</h1>
        <p className="app__subtitle">
          Сводка по заказам.{" "}
          {load.status === "loading" && <span>Загрузка…</span>}
          {load.status === "ready" && rows.length === 0 && <span>Заказов пока нет.</span>}
        </p>
      </header>

      {load.status === "error" && (
        <div className="banner banner--error" style={{ marginBottom: "1rem" }}>
          {load.message}
        </div>
      )}

      {load.status === "ready" && rows.length > 0 && kpis && (
        <>
          <DashboardKpis kpis={kpis} />

          {perOrder.length > 0 && (rows.length <= 60 || denseSameDay) && (
            <section className="card" style={{ marginBottom: "1.25rem" }}>
              <h2 className="card__title">Каждый заказ по сумме</h2>
              <OrdersPerOrderBarChart data={perOrder} unit={amountUnit} />
            </section>
          )}

          {histogram.length > 0 && (
            <section className="card" style={{ marginBottom: "1.25rem" }}>
              <h2 className="card__title">Распределение сумм заказов</h2>
              <p className="card__lead">Число заказов по диапазонам суммы ({amountUnit}).</p>
              <AmountHistogramChart data={histogram} unit={amountUnit} />
            </section>
          )}

          {showDaily && daily.length > 0 && (
            <section className="card">
              <h2 className="card__title">Сумма по календарным дням (UTC)</h2>
              <OrdersTrendChart data={daily} currencyCode={kpis.currency} />
            </section>
          )}

          {!showDaily && daily.length === 1 && (
            <section className="card">
              <h2 className="card__title">Итого за сутки (UTC)</h2>
              <p className="card__lead">
                <strong>{daily[0].day}</strong>: {daily[0].count} заказов,{" "}
                {new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(daily[0].sumAmount)}{" "}
                {amountUnit}
              </p>
            </section>
          )}
        </>
      )}
    </div>
  );
}
