/**
 * FastAPI 백엔드 API 클라이언트
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    next: { revalidate: 0 },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${path} → ${res.status}: ${text}`);
  }
  return res.json();
}

export async function fetchStocks() {
  return apiFetch<{ stock_code: string; name: string; market: string; is_active: number }[]>(
    "/api/stocks"
  );
}

export async function fetchSnapshot(stockCode: string, runReasoning = false) {
  return apiFetch<import("./types").DashboardSnapshot>(
    `/api/snapshot/${stockCode}?run_reasoning=${runReasoning}`
  );
}

export async function fetchCandles(stockCode: string, interval = "1d") {
  return apiFetch<import("./types").ChartCandles>(
    `/api/chart/${stockCode}/candles?interval=${interval}`
  );
}

export async function fetchHealth() {
  return apiFetch<{ status: string; version: string; db: string }>("/health");
}
