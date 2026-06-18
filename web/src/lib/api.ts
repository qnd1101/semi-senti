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

/**
 * 뉴스 기사 목록 (백엔드 신규 엔드포인트 — 계약 대기).
 * GET /api/news/{code}?limit=
 * 응답: { stock_code, analyzed_count, items:[{title,summary,source,url,
 *   published_at,sentiment_direction,keywords[]}] }
 */
export async function fetchNews(stockCode: string, limit = 100, days = 30) {
  const qs = new URLSearchParams({ limit: String(limit), days: String(days) }).toString();
  return apiFetch<import("./dashboard-c/adapt").NewsApiResponse>(
    `/api/news/${stockCode}?${qs}`
  );

}
/**
 * 반도체 시세 스크리너
 * GET /api/screener/semiconductor?sort=change|price|volume|w1|m1|y1&order=asc|desc
 */
export async function fetchScreener(
  sort: import('./dashboard-c/screener-types').ScreenerSortKey = 'change',
  order: import('./dashboard-c/screener-types').SortOrder = 'desc'
) {
  return apiFetch<import('./dashboard-c/screener-types').ScreenerRow[]>(
    `/api/screener/semiconductor?sort=${sort}&order=${order}`
  );
}

// ── Admin API ────────────────────────────────────────────────

export async function fetchAllStocks() {
  return apiFetch<import("./types").StockRow[]>("/api/stocks?include_inactive=true");
}

export async function createStock(body: { stock_code: string; name: string; market: string }) {
  return apiFetch<import("./types").StockRow>("/api/stocks", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateStock(
  stockCode: string,
  body: { name?: string; market?: string; is_active?: boolean }
) {
  return apiFetch<import("./types").StockRow>(`/api/stocks/${stockCode}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function toggleStock(stockCode: string, isActive: boolean) {
  return apiFetch<{ stock_code: string; is_active: boolean }>("/api/stocks/toggle", {
    method: "PATCH",
    body: JSON.stringify({ stock_code: stockCode, is_active: isActive }),
  });
}

export async function deleteStock(stockCode: string) {
  return apiFetch<{ deleted: string }>(`/api/stocks/${stockCode}`, { method: "DELETE" });
}

export async function fetchSystemStatus() {
  return apiFetch<import("./types").SystemStatus>("/api/system/status");
}

export async function refreshStock(
  stockCode: string,
  options: { run_signal?: boolean; run_sentiment?: boolean; run_cycle?: boolean; run_reasoning?: boolean } = {}
) {
  return apiFetch<import("./types").RefreshResult>("/api/refresh", {
    method: "POST",
    body: JSON.stringify({
      stock_code: stockCode,
      run_signal: options.run_signal ?? true,
      run_sentiment: options.run_sentiment ?? true,
      run_cycle: options.run_cycle ?? true,
      run_reasoning: options.run_reasoning ?? false,
    }),
  });
}

export async function syncStock(stockCode: string) {
  return apiFetch<Record<string, unknown>>(`/api/sync/${stockCode}`, { method: "POST" });
}
