"use client";

import useSWR from "swr";

import type { DashboardSnapshot } from "@/lib/types";

async function fetcherJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`fetch_failed_${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function useSnapshot(
  stockCode: string | null | undefined,
  refreshIntervalMs: number
) {
  const key =
    stockCode && stockCode.length > 0
      ? `/api/snapshot/${encodeURIComponent(stockCode)}`
      : null;

  return useSWR<DashboardSnapshot>(key, fetcherJson, {
    refreshInterval: refreshIntervalMs,
    revalidateOnFocus: true,
    dedupingInterval: 2000,
  });
}
