"use client";

import useSWR from "swr";

import type { Stock } from "@/lib/types";

async function fetcherStocks(url: string): Promise<Stock[]> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`fetch_failed_${res.status}`);
  }
  const data = await res.json();
  if (Array.isArray(data)) return data as Stock[];
  if (data && Array.isArray(data.stocks)) return data.stocks as Stock[];
  return [];
}

export function useStocks() {
  return useSWR<Stock[]>("/api/stocks", fetcherStocks, {
    revalidateOnFocus: true,
    dedupingInterval: 10_000,
  });
}
