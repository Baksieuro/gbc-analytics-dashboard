export type OrderRow = {
  id: string;
  retailcrm_id: number;
  total_amount: number | string;
  currency: string;
  ordered_at: string;
  updated_at?: string;
};

export type DayAggregate = {
  day: string;
  sumAmount: number;
  count: number;
};
