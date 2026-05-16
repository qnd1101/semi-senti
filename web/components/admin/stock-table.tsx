"use client";

import * as React from "react";
import { Trash2, ToggleLeft, ToggleRight, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface StockRow {
  stock_code: string;
  name: string;
  market: string | null;
  is_active: number;
  created_at?: string | null;
}

interface StockTableProps {
  className?: string;
}

const MESSAGES = {
  title: "등록 종목 관리",
  addTitle: "종목 추가",
  code: "종목 코드 (6자리)",
  name: "종목명",
  market: "시장",
  add: "등록",
  active: "활성",
  inactive: "비활성",
  delete: "삭제",
  noStocks: "등록된 종목이 없습니다",
  confirmDelete: "정말 삭제하시겠습니까? 관련 데이터도 모두 삭제됩니다.",
} as const;

export function StockTable({ className }: StockTableProps) {
  const [stocks, setStocks] = React.useState<StockRow[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [newCode, setNewCode] = React.useState("");
  const [newName, setNewName] = React.useState("");
  const [newMarket, setNewMarket] = React.useState("KOSPI");
  const [error, setError] = React.useState<string | null>(null);

  const fetchStocks = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/stocks");
      if (res.ok) setStocks(await res.json());
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchStocks();
  }, [fetchStocks]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!newCode || !newName) {
      setError("종목 코드와 이름은 필수입니다.");
      return;
    }
    const res = await fetch("/api/admin/stocks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stock_code: newCode,
        name: newName,
        market: newMarket,
      }),
    });
    if (res.ok) {
      setNewCode("");
      setNewName("");
      fetchStocks();
    } else {
      const data = await res.json();
      setError(data.error ?? "등록 실패");
    }
  };

  const handleToggle = async (code: string, current: number) => {
    await fetch("/api/admin/stocks", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stock_code: code, is_active: current ? 0 : 1 }),
    });
    fetchStocks();
  };

  const handleDelete = async (code: string) => {
    if (!confirm(MESSAGES.confirmDelete)) return;
    await fetch("/api/admin/stocks", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stock_code: code }),
    });
    fetchStocks();
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Add Form */}
      <form onSubmit={handleAdd} className="space-y-3">
        <h3 className="text-sm font-medium">{MESSAGES.addTitle}</h3>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder={MESSAGES.code}
            value={newCode}
            onChange={(e) => setNewCode(e.target.value)}
            className="h-9 w-28 rounded-md border border-input bg-background px-3 text-sm"
            maxLength={6}
          />
          <input
            type="text"
            placeholder={MESSAGES.name}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm"
          />
          <select
            value={newMarket}
            onChange={(e) => setNewMarket(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          >
            <option value="KOSPI">KOSPI</option>
            <option value="KOSDAQ">KOSDAQ</option>
          </select>
          <Button type="submit" size="sm" className="gap-1">
            <Plus className="h-4 w-4" />
            {MESSAGES.add}
          </Button>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </form>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left font-medium">코드</th>
              <th className="px-3 py-2 text-left font-medium">종목명</th>
              <th className="px-3 py-2 text-left font-medium">시장</th>
              <th className="px-3 py-2 text-center font-medium">상태</th>
              <th className="px-3 py-2 text-center font-medium">작업</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  로딩 중...
                </td>
              </tr>
            ) : stocks.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  {MESSAGES.noStocks}
                </td>
              </tr>
            ) : (
              stocks.map((s) => (
                <tr key={s.stock_code} className="border-b border-border last:border-0">
                  <td className="px-3 py-2 font-mono text-xs">{s.stock_code}</td>
                  <td className="px-3 py-2">{s.name}</td>
                  <td className="px-3 py-2 text-muted-foreground">{s.market}</td>
                  <td className="px-3 py-2 text-center">
                    <Badge variant={s.is_active ? "buy" : "secondary"}>
                      {s.is_active ? MESSAGES.active : MESSAGES.inactive}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleToggle(s.stock_code, s.is_active)}
                        title={s.is_active ? "비활성화" : "활성화"}
                      >
                        {s.is_active ? (
                          <ToggleRight className="h-4 w-4 text-signal-buy" />
                        ) : (
                          <ToggleLeft className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive"
                        onClick={() => handleDelete(s.stock_code)}
                        title={MESSAGES.delete}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
