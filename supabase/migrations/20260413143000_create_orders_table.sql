-- Orders storage for RetailCRM → Supabase sync and Vite dashboard.
-- Apply in Supabase: SQL Editor → New query → paste → Run
-- (or: supabase db push / linked project migrations)
--
-- Writes: use SUPABASE_SERVICE_ROLE_KEY from Python only (bypasses RLS).
-- Reads from browser: VITE_SUPABASE_ANON_KEY — only listed columns are granted to anon.

-- gen_random_uuid() — встроен в PostgreSQL 13+ (Supabase PG15).

CREATE TABLE IF NOT EXISTS public.orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  retailcrm_id integer NOT NULL,
  total_amount numeric(18, 2) NOT NULL,
  currency text NOT NULL DEFAULT 'KZT',
  ordered_at timestamptz NOT NULL,
  raw_payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT orders_retailcrm_id_key UNIQUE (retailcrm_id)
);

COMMENT ON TABLE public.orders IS 'Synced RetailCRM orders; upsert on retailcrm_id from Python (service_role).';

COMMENT ON COLUMN public.orders.retailcrm_id IS 'RetailCRM order id (external stable key for upsert).';

COMMENT ON COLUMN public.orders.total_amount IS 'Order total for chart / thresholds (e.g. > 50_000 KZT).';

COMMENT ON COLUMN public.orders.currency IS 'ISO-like code, default KZT (₸).';

COMMENT ON COLUMN public.orders.ordered_at IS 'Order datetime for time-series chart.';

COMMENT ON COLUMN public.orders.raw_payload IS 'Optional full CRM payload; not exposed to anon.';

CREATE INDEX IF NOT EXISTS orders_ordered_at_idx ON public.orders (ordered_at);

CREATE OR REPLACE FUNCTION public.set_orders_updated_at()
  RETURNS TRIGGER
  LANGUAGE plpgsql
  AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS orders_set_updated_at ON public.orders;

CREATE TRIGGER orders_set_updated_at
  BEFORE UPDATE ON public.orders
  FOR EACH ROW
  EXECUTE PROCEDURE public.set_orders_updated_at();

ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;

-- No INSERT/UPDATE/DELETE policies for anon/authenticated → only service_role can write via API.

DROP POLICY IF EXISTS "anon_select_orders" ON public.orders;

DROP POLICY IF EXISTS "authenticated_select_orders" ON public.orders;

CREATE POLICY "anon_select_orders"
  ON public.orders
  FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "authenticated_select_orders"
  ON public.orders
  FOR SELECT
  TO authenticated
  USING (true);

-- Tighten privileges: dashboard reads only columns needed for the chart (exclude raw_payload).
REVOKE ALL ON TABLE public.orders
FROM anon;

REVOKE ALL ON TABLE public.orders
FROM authenticated;

GRANT SELECT (
  id,
  retailcrm_id,
  total_amount,
  currency,
  ordered_at,
  created_at,
  updated_at
) ON TABLE public.orders TO anon;

GRANT SELECT (
  id,
  retailcrm_id,
  total_amount,
  currency,
  ordered_at,
  created_at,
  updated_at
) ON TABLE public.orders TO authenticated;

-- service_role: read + upsert from Python ETL (bypasses RLS; explicit grants for clarity).
GRANT SELECT,
INSERT,
UPDATE ON TABLE public.orders TO service_role;
