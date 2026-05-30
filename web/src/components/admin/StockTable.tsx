"use client";

import { createStock, deleteStock, refreshStock, toggleStock } from "@/lib/api";
import type { StockRow } from "@/lib/types";
import { useCallback, useState } from "react";

interface Props {
  stocks: StockRow[];
  onChanged: () => void;
}

export function StockTable({ stocks, onChanged }: Props) {
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ stock_code: "", name: "", market: "KOSPI" });
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [refreshingCode, setRefreshingCode] = useState<string | null>(null);
  const [refreshResults, setRefreshResults] = useState<Record<string, string>>({});

  const handleAdd = useCallback(async () => {
    setFormError(null);
    if (!/^\d{6}$/.test(form.stock_code)) {
      setFormError("종목 코드는 6자리 숫자입니다.");
      return;
    }
    if (!form.name.trim()) {
      setFormError("종목명은 필수입니다.");
      return;
    }
    setSubmitting(true);
    try {
      await createStock(form);
      setForm({ stock_code: "", name: "", market: "KOSPI" });
      setAdding(false);
      onChanged();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "등록 실패");
    } finally {
      setSubmitting(false);
    }
  }, [form, onChanged]);

  const handleToggle = useCallback(async (code: string, current: boolean) => {
    try {
      await toggleStock(code, !current);
      onChanged();
    } catch (e) {
      alert(e instanceof Error ? e.message : "변경 실패");
    }
  }, [onChanged]);

  const handleDelete = useCallback(async (code: string, name: string) => {
    if (!confirm(`"${name}" (${code}) 을 삭제하시겠습니까?\n관련 데이터가 모두 삭제됩니다.`)) return;
    try {
      await deleteStock(code);
      onChanged();
    } catch (e) {
      alert(e instanceof Error ? e.message : "삭제 실패");
    }
  }, [onChanged]);

  const handleRefresh = useCallback(async (code: string) => {
    setRefreshingCode(code);
    try {
      const result = await refreshStock(code);
      const msg = result.ok
        ? "갱신 완료"
        : `오류: ${result.errors.join(", ")}`;
      setRefreshResults((prev) => ({ ...prev, [code]: msg }));
      setTimeout(() => setRefreshResults((prev) => { const next = { ...prev }; delete next[code]; return next; }), 5000);
    } catch (e) {
      setRefreshResults((prev) => ({ ...prev, [code]: e instanceof Error ? e.message : "실패" }));
    } finally {
      setRefreshingCode(null);
    }
  }, []);

  return (
    <div className="space-y-4">
      {/* 상단 툴바 */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-zinc-400">전체 {stocks.length}종목</p>
        <button
          onClick={() => { setAdding((v) => !v); setFormError(null); }}
          className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded transition"
        >
          + 종목 추가
        </button>
      </div>

      {/* 추가 폼 */}
      {adding && (
        <div className="p-4 bg-zinc-800/60 border border-zinc-700 rounded-lg space-y-3">
          <p className="text-xs font-medium text-zinc-300">신규 종목 등록</p>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[10px] text-zinc-500 mb-1">종목 코드 *</label>
              <input
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-xs focus:outline-none focus:border-zinc-500"
                placeholder="005930"
                maxLength={6}
                value={form.stock_code}
                onChange={(e) => setForm((f) => ({ ...f, stock_code: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-[10px] text-zinc-500 mb-1">종목명 *</label>
              <input
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-xs focus:outline-none focus:border-zinc-500"
                placeholder="삼성전자"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-[10px] text-zinc-500 mb-1">시장</label>
              <select
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-xs focus:outline-none"
                value={form.market}
                onChange={(e) => setForm((f) => ({ ...f, market: e.target.value }))}
              >
                <option value="KOSPI">KOSPI</option>
                <option value="KOSDAQ">KOSDAQ</option>
              </select>
            </div>
          </div>
          {formError && <p className="text-xs text-rose-400">{formError}</p>}
          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              disabled={submitting}
              className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded transition"
            >
              {submitting ? "등록 중…" : "등록"}
            </button>
            <button
              onClick={() => { setAdding(false); setFormError(null); }}
              className="text-xs px-3 py-1.5 border border-zinc-700 hover:border-zinc-500 rounded transition"
            >
              취소
            </button>
          </div>
        </div>
      )}

      {/* 종목 테이블 */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-500">
              <th className="text-left py-2 pr-4 font-medium">코드</th>
              <th className="text-left py-2 pr-4 font-medium">종목명</th>
              <th className="text-left py-2 pr-4 font-medium">시장</th>
              <th className="text-center py-2 pr-4 font-medium">활성</th>
              <th className="text-left py-2 pr-4 font-medium">등록일</th>
              <th className="text-right py-2 font-medium">액션</th>
            </tr>
          </thead>
          <tbody>
            {stocks.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-zinc-600">
                  종목 없음
                </td>
              </tr>
            )}
            {stocks.map((s) => (
              <tr key={s.stock_code} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition">
                <td className="py-2.5 pr-4 font-mono text-zinc-300">{s.stock_code}</td>
                <td className="py-2.5 pr-4 text-zinc-100">{s.name}</td>
                <td className="py-2.5 pr-4 text-zinc-400">{s.market}</td>
                <td className="py-2.5 pr-4 text-center">
                  <button
                    onClick={() => handleToggle(s.stock_code, Boolean(s.is_active))}
                    className={`w-8 h-4 rounded-full transition relative ${
                      s.is_active ? "bg-emerald-600" : "bg-zinc-700"
                    }`}
                    title={s.is_active ? "활성 (클릭 시 비활성)" : "비활성 (클릭 시 활성)"}
                  >
                    <span
                      className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all ${
                        s.is_active ? "left-4.5" : "left-0.5"
                      }`}
                      style={{ left: s.is_active ? "calc(100% - 14px)" : "2px" }}
                    />
                  </button>
                </td>
                <td className="py-2.5 pr-4 text-zinc-500 tabular-nums">
                  {s.created_at ? s.created_at.slice(0, 10) : "—"}
                </td>
                <td className="py-2.5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {refreshResults[s.stock_code] && (
                      <span className={`text-[10px] ${refreshResults[s.stock_code].startsWith("오류") ? "text-rose-400" : "text-emerald-400"}`}>
                        {refreshResults[s.stock_code]}
                      </span>
                    )}
                    <button
                      onClick={() => handleRefresh(s.stock_code)}
                      disabled={refreshingCode === s.stock_code}
                      className="px-2 py-1 text-[10px] border border-zinc-700 hover:border-zinc-500 rounded transition disabled:opacity-50"
                      title="수동 갱신"
                    >
                      {refreshingCode === s.stock_code ? "갱신 중…" : "갱신"}
                    </button>
                    <button
                      onClick={() => handleDelete(s.stock_code, s.name)}
                      className="px-2 py-1 text-[10px] border border-rose-800/60 hover:border-rose-600 text-rose-400 hover:text-rose-300 rounded transition"
                      title="삭제"
                    >
                      삭제
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
