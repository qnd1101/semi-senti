"use client";

import * as React from "react";
import { Activity, Database, Bell, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface SystemStatus {
  generated_at: string;
  table_counts: Record<string, number>;
  failed_notifications: number;
  stocks: Array<{
    stock_code: string;
    name: string;
    market: string | null;
    is_active: boolean;
    last_price_at: string | null;
    last_signal_at: string | null;
    news_count: number;
  }>;
}

interface SystemMonitorProps {
  className?: string;
}

const MESSAGES = {
  title: "시스템 상태",
  refresh: "갱신",
  tables: "테이블 행 수",
  failedNotifs: "실패 알림",
  stockStatus: "종목별 수집 상태",
  noData: "데이터를 불러올 수 없습니다",
  lastPrice: "최근 가격",
  lastSignal: "최근 시그널",
  news: "뉴스 수",
} as const;

export function SystemMonitor({ className }: SystemMonitorProps) {
  const [status, setStatus] = React.useState<SystemStatus | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchStatus = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/system");
      if (res.ok) {
        setStatus(await res.json());
      } else {
        setError("API 응답 실패");
      }
    } catch {
      setError("네트워크 오류");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  if (loading) {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        로딩 중...
      </p>
    );
  }

  if (error || !status) {
    return (
      <p className={cn("text-sm text-destructive", className)}>
        {error ?? MESSAGES.noData}
      </p>
    );
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{MESSAGES.title}</h2>
        <Button variant="outline" size="sm" onClick={fetchStatus} className="gap-1">
          <RefreshCw className="h-3.5 w-3.5" />
          {MESSAGES.refresh}
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Database className="h-3.5 w-3.5" />
              {MESSAGES.tables}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-xs">
            {Object.entries(status.table_counts).map(([table, count]) => (
              <div key={table} className="flex justify-between">
                <span className="text-muted-foreground">{table}</span>
                <span className="font-mono">{count.toLocaleString()}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Bell className="h-3.5 w-3.5" />
              {MESSAGES.failedNotifs}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span
              className={cn(
                "text-2xl font-bold tabular-nums",
                status.failed_notifications > 0 && "text-destructive"
              )}
            >
              {status.failed_notifications}
            </span>
          </CardContent>
        </Card>

        <Card className="col-span-2">
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Activity className="h-3.5 w-3.5" />
              {MESSAGES.stockStatus}
            </CardTitle>
          </CardHeader>
          <CardContent className="max-h-48 overflow-y-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="py-1 text-left">종목</th>
                  <th className="py-1 text-left">{MESSAGES.lastPrice}</th>
                  <th className="py-1 text-left">{MESSAGES.lastSignal}</th>
                  <th className="py-1 text-right">{MESSAGES.news}</th>
                </tr>
              </thead>
              <tbody>
                {status.stocks.map((s) => (
                  <tr key={s.stock_code} className="border-b border-border/50 last:border-0">
                    <td className="py-1">
                      <div className="flex items-center gap-1">
                        <span>{s.name}</span>
                        {!s.is_active && (
                          <Badge variant="secondary" className="text-[9px]">off</Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-1 text-muted-foreground">
                      {s.last_price_at?.slice(0, 10) ?? "-"}
                    </td>
                    <td className="py-1 text-muted-foreground">
                      {s.last_signal_at?.slice(0, 10) ?? "-"}
                    </td>
                    <td className="py-1 text-right tabular-nums">{s.news_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      {/* Timestamp */}
      <p className="text-right text-xs text-muted-foreground">
        {new Date(status.generated_at).toLocaleString("ko-KR")}
      </p>
    </div>
  );
}
