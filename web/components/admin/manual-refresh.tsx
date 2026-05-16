"use client";

import * as React from "react";
import { Play, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface RefreshResult {
  stock_code: string;
  ok: boolean;
  started_at: string;
  finished_at: string;
  steps: Record<string, { ok: boolean; error?: string; [k: string]: unknown }>;
  errors: string[];
}

interface ManualRefreshProps {
  className?: string;
}

const MESSAGES = {
  title: "수동 갱신 (Python 엔진)",
  description: "FastAPI 서버 (/py-api) 경유로 분석 파이프라인 실행",
  code: "종목 코드",
  market: "시장",
  run: "갱신 실행",
  running: "실행 중...",
  noServer: "Python API 서버가 응답하지 않습니다. uvicorn 실행 확인 필요.",
} as const;

export function ManualRefresh({ className }: ManualRefreshProps) {
  const [code, setCode] = React.useState("");
  const [market, setMarket] = React.useState("KOSPI");
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<RefreshResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const handleRefresh = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/py-api/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stock_code: code.trim(), market }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="text-sm">{MESSAGES.title}</CardTitle>
        <p className="text-xs text-muted-foreground">{MESSAGES.description}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={handleRefresh} className="flex gap-2">
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={MESSAGES.code}
            className="h-9 w-28 rounded-md border border-input bg-background px-3 text-sm"
            maxLength={6}
          />
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          >
            <option value="KOSPI">KOSPI</option>
            <option value="KOSDAQ">KOSDAQ</option>
          </select>
          <Button type="submit" size="sm" disabled={loading} className="gap-1">
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {loading ? MESSAGES.running : MESSAGES.run}
          </Button>
        </form>

        {error && (
          <p className="text-xs text-destructive">{error}</p>
        )}

        {result && (
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              {result.ok ? (
                <CheckCircle className="h-4 w-4 text-signal-buy" />
              ) : (
                <XCircle className="h-4 w-4 text-destructive" />
              )}
              <span className="font-mono">{result.stock_code}</span>
              <Badge variant={result.ok ? "buy" : "sell"}>
                {result.ok ? "성공" : "일부 실패"}
              </Badge>
            </div>
            <div className="space-y-1 rounded-md bg-muted/50 p-2">
              {Object.entries(result.steps).map(([step, info]) => (
                <div key={step} className="flex items-center justify-between">
                  <span className="capitalize">{step}</span>
                  <Badge variant={info.ok ? "buy" : "sell"} className="text-[9px]">
                    {info.ok ? "OK" : info.error?.slice(0, 40) ?? "FAIL"}
                  </Badge>
                </div>
              ))}
            </div>
            <p className="text-muted-foreground">
              {result.started_at} ~ {result.finished_at}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
