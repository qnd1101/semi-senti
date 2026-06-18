/** 스크리너 전용 타입 */
export interface ScreenerRow {
  stock_code: string;
  name: string;
  price: number | null;
  change_pct: number | null;
  volume: number | null;
  return_1w: number | null;
  return_1m: number | null;
  return_1y: number | null;
  is_tracked: boolean;
}

export type ScreenerSortKey =
  | "change"
  | "price"
  | "volume"
  | "w1"
  | "m1"
  | "y1"
  | "name";

export type SortOrder = "asc" | "desc";
