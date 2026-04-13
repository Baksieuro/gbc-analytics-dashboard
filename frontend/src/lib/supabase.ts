import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export type OrdersSupabaseClient = SupabaseClient;

export function getSupabaseEnv(): { url: string; anonKey: string } | null {
  const url = import.meta.env.VITE_SUPABASE_URL?.trim();
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim();
  if (!url || !anonKey) {
    return null;
  }
  return { url, anonKey };
}

export function createOrdersClient(): OrdersSupabaseClient | null {
  const env = getSupabaseEnv();
  if (!env) {
    return null;
  }
  return createClient(env.url, env.anonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}
