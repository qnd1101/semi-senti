"use client";

import { StockTable } from "@/components/admin/StockTable";
import { SystemMonitor } from "@/components/admin/SystemMonitor";
import { fetchAllStocks, fetchSystemStatus } from "@/lib/api";
import type { StockRow, SystemStatus } from "@/lib/types";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type Tab = "stocks" | "system";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("stocks");
  const [stocks, setStocks] = useState<StockRow[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loadingStocks, setLoadingStocks] = useState(false);
  const [loadingSystem, setLoadingSystem] = useState(false);
  const [stocksError, setStocksError] = useState<string | null>(null);
  const [systemError, setSystemError] = useState<string | null>(null);

  const loadStocks = useCallback(async () => {
    setLoadingStocks(true);
    setStocksError(null);
    try {
      const data = await fetchAllStocks();
      setStocks(data);
    } catch (e) {
      setStocksError(e instanceof Error ? e.message : "종목 조회 실패");
    } finally {
      setLoadingStocks(false);
    }
  }, []);

  const loadSystem = useCallback(async () => {
    setLoadingSystem(true);
    setSystemError(null);
    try {
      const data = await fetchSystemStatus();
      setSystemStatus(data);
    } catch (e) {
      setSystemError(e instanceof Error ? e.message : "시스템 상태 조회 실패");
    } finally {
      setLoadingSystem(false);
    }
  }, []);

  useEffect(() => {
    loadStocks();
  }, [loadStocks]);

  useEffect(() => {
    if (tab === "system") loadSystem();
  }, [tab, loadSystem]);

  return (
    <main className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col">
      {/* Topbar */}
      <header className="h-12 border-b border-zinc-800/60 flex items-center px-4 gap-4 flex-shrink-0">
        <Link href="/" className="text-sm font-semibold hover:text-zinc-300 transition">
          Semi Senti
        </Link>
        <span className="text-zinc-600">/</span>
        <span className="text-sm text-zinc-400">관리자</span>
        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/"
            className="text-xs px-3 py-1 border border-zinc-700 hover:border-zinc-500 rounded transition"
          >
            ← 대시보드
          </Link>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 p-6 max-w-5xl mx-auto w-full">
        {/* 탭 */}
        <div className="flex gap-1 mb-6 border-b border-zinc-800">
          {([["stocks", "종목 관리"], ["system", "시스템 상태"]] as [Tab, string][]).map(
            ([id, label]) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`px-4 py-2 text-sm transition border-b-2 -mb-px ${
                  tab === id
                    ? "border-blue-500 text-zinc-100"
                    : "border-transparent text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {label}
              </button>
            )
          )}
        </div>

        {/* 종목 관리 탭 */}
        {tab === "stocks" && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-zinc-300">종목 관리</h2>
              <button
                onClick={loadStocks}
                disabled={loadingStocks}
                className="text-xs text-zinc-500 hover:text-zinc-300 transition disabled:opacity-50"
              >
                {loadingStocks ? "로딩 중…" : "새로고침"}
              </button>
            </div>
            {stocksError && (
              <div className="mb-4 px-3 py-2 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded">
                ⚠ {stocksError}
              </div>
            )}
            {loadingStocks && stocks.length === 0 ? (
              <p className="text-xs text-zinc-500 animate-pulse">로딩 중…</p>
            ) : (
              <div className="glass-card p-4">
                <StockTable stocks={stocks} onChanged={loadStocks} />
              </div>
            )}
          </section>
        )}

        {/* 시스템 상태 탭 */}
        {tab === "system" && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-zinc-300">시스템 상태</h2>
              <button
                onClick={loadSystem}
                disabled={loadingSystem}
                className="text-xs text-zinc-500 hover:text-zinc-300 transition disabled:opacity-50"
              >
                {loadingSystem ? "로딩 중…" : "새로고침"}
              </button>
            </div>
            {systemError && (
              <div className="mb-4 px-3 py-2 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded">
                ⚠ {systemError}
              </div>
            )}
            <div className="glass-card p-4">
              <SystemMonitor status={systemStatus} loading={loadingSystem && !systemStatus} />
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
