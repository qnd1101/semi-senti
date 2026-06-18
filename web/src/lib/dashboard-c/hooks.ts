"use client";

import useSWR from "swr";
import { fetchStocks, fetchSnapshot, fetchCandles, fetchNews } from "@/lib/api";
import type { DashboardSnapshot, CandleData } from "@/lib/types";
import type { NewsApiResponse } from "./adapt";

const AUTO_REFRESH_MS =
  parseInt(process.env.NEXT_PUBLIC_AUTO_REFRESH_SECONDS || "60", 10) * 1000;

export function useStocks() {
  return useSWR("stocks", fetchStocks, {
    revalidateOnFocus: false,
  });
}

export function useSnapshot(code: string | null) {
  return useSWR<DashboardSnapshot>(code ? ["snapshot", code] : null, () => fetchSnapshot(code as string), {
    refreshInterval: AUTO_REFRESH_MS,
    revalidateOnFocus: false,
    keepPreviousData: true,
  });
}

export function useCandles(code: string | null, interval = "1d") {
  return useSWR<{ candles: CandleData[] }>(
    code ? ["candles", code, interval] : null,
    () => fetchCandles(code as string, interval),
    { refreshInterval: AUTO_REFRESH_MS, revalidateOnFocus: false, keepPreviousData: true }
  );
}

/**
 * 뉴스 기사 목록 SWR — 백엔드 GET /api/news/{code} 완료 후 활성화.
 * enabled=false 면 호출하지 않고 자리만 잡아둔다(현재 기본 비활성).
 */
export function useNews(code: string | null, enabled: boolean, days = 30) {
  return useSWR<NewsApiResponse>(
    enabled && code ? ["news", code, days] : null,
    () => fetchNews(code as string, 100, days),
    { refreshInterval: AUTO_REFRESH_MS, revalidateOnFocus: false }
  );
}

import { fetchScreener } from '@/lib/api';
import type { ScreenerRow, ScreenerSortKey, SortOrder } from './screener-types';

export function useScreener(sort: ScreenerSortKey = 'change', order: SortOrder = 'desc') {
  return useSWR<ScreenerRow[]>(
    ['screener', sort, order],
    () => fetchScreener(sort, order),
    {
      refreshInterval: AUTO_REFRESH_MS,
      revalidateOnFocus: false,
      keepPreviousData: true,
    }
  );
}


