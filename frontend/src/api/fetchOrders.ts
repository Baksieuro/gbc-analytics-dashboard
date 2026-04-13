import type { SupabaseClient } from "@supabase/supabase-js";
import type { OrderRow } from "../types/order";

const ORDER_COLUMNS =
  "id, retailcrm_id, total_amount, currency, ordered_at, updated_at" as const;

export async function fetchOrdersForChart(
  client: SupabaseClient,
): Promise<{ rows: OrderRow[]; errorMessage: string | null }> {
  const { data, error } = await client
    .from("orders")
    .select(ORDER_COLUMNS)
    .order("ordered_at", { ascending: true });

  if (error) {
    return { rows: [], errorMessage: error.message };
  }
  const rows = (data ?? []) as OrderRow[];
  return { rows, errorMessage: null };
}
