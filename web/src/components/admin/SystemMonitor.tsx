"use client";

import type { SystemStatus } from "@/lib/types";

interface Props {
  status: SystemStatus | null;
  loading: boolean;
}

function freshnessBadge(dateStr: string | null): { label: string; cls: string } {
  if (!dateStr) return { label: "없음", cls: "text-zinc-600" };
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000 / 3600;
  if (diff < 1) return { label: "최신", cls: "text-emerald-400" };
  if (diff < 24) return { label: `${Math.floor(diff)}h 전`, cls: "text-yellow-400" };
  const days = Math.floor(diff / 24);
  return { label: `${days}일 전`, cls: "text-rose-400" };
}

export function SystemMonitor({ status, loading }: Props) {
  if (loading) {
    return <p className="text-xs text-zinc-500 animate-pulse">시스템 상태 로딩 중…</p>;
  }
  if (!status) {
    return <p className="text-xs text-zinc-500">데이터 없음</p>;
  }

  const tableCounts = Object.entries(status.table_counts);

  return (
    <div className="space-y-6">
      {/* 헤더 요약 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 glass-card">
          <p className="text-[10px] text-zinc-500 mb-1">생성 시각</p>
          <p className="text-xs tabular-nums text-zinc-300">{status.generated_at}</p>
        </div>
        <div className="p-4 glass-card">
          <p className="text-[10px] text-zinc-500 mb-1">알림 실패</p>
          <p className={`text-sm font-semibold ${status.failed_notifications > 0 ? "text-rose-400" : "text-zinc-300"}`}>
            {status.failed_notifications}
          </p>
        </div>
        <div className="p-4 glass-card">
          <p className="text-[10px] text-zinc-500 mb-1">DB</p>
          <p className="text-[10px] text-zinc-400 break-all">{status.db}</p>
        </div>
      </div>

      {/* 경고 */}
      {status.warnings.length > 0 && (
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <p className="text-xs font-medium text-yellow-400 mb-1">경고</p>
          {status.warnings.map((w, i) => (
            <p key={i} className="text-[11px] text-yellow-300">{w}</p>
          ))}
        </div>
      )}

      {/* 테이블 행 수 */}
      <div>
        <p className="text-xs font-medium text-zinc-400 mb-2">테이블 레코드 수</p>
        <div className="grid grid-cols-4 gap-2">
          {tableCounts.map(([table, cnt]) => (
            <div key={table} className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
              <p className="text-[10px] text-zinc-500 truncate">{table}</p>
              <p className={`text-sm font-semibold tabular-nums mt-1 ${cnt < 0 ? "text-rose-400" : "text-zinc-200"}`}>
                {cnt < 0 ? "오류" : cnt.toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* 종목별 데이터 신선도 */}
      <div>
        <p className="text-xs font-medium text-zinc-400 mb-2">종목별 데이터 신선도</p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left py-2 pr-4 font-medium">종목</th>
                <th className="text-center py-2 pr-4 font-medium">활성</th>
                <th className="text-center py-2 pr-4 font-medium">최근 주가</th>
                <th className="text-center py-2 pr-4 font-medium">최근 뉴스</th>
                <th className="text-center py-2 pr-4 font-medium">최근 시그널</th>
                <th className="text-center py-2 pr-4 font-medium">최근 감성</th>
                <th className="text-right py-2 pr-4 font-medium">뉴스수</th>
                <th className="text-right py-2 font-medium">시그널수</th>
              </tr>
            </thead>
            <tbody>
              {status.stocks.map((s) => {
                const price = freshnessBadge(s.last_price_at);
                const news = freshnessBadge(s.last_news_at);
                const signal = freshnessBadge(s.last_signal_at);
                const sent = freshnessBadge(s.last_sentiment_date);
                return (
                  <tr key={s.stock_code} className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition">
                    <td className="py-2.5 pr-4">
                      <span className="text-zinc-100">{s.name}</span>
                      <span className="ml-1 text-zinc-500 font-mono">{s.stock_code}</span>
                    </td>
                    <td className="py-2.5 pr-4 text-center">
                      <span className={`text-[10px] ${s.is_active ? "text-emerald-400" : "text-zinc-600"}`}>
                        {s.is_active ? "활성" : "비활성"}
                      </span>
                    </td>
                    <td className={`py-2.5 pr-4 text-center tabular-nums ${price.cls}`}>{price.label}</td>
                    <td className={`py-2.5 pr-4 text-center tabular-nums ${news.cls}`}>{news.label}</td>
                    <td className={`py-2.5 pr-4 text-center tabular-nums ${signal.cls}`}>{signal.label}</td>
                    <td className={`py-2.5 pr-4 text-center tabular-nums ${sent.cls}`}>{sent.label}</td>
                    <td className="py-2.5 pr-4 text-right tabular-nums text-zinc-400">{s.news_count}</td>
                    <td className="py-2.5 text-right tabular-nums text-zinc-400">{s.signal_count}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
