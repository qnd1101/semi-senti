"use client";

import { useEffect, useRef, useState } from "react";
import { C } from "@/lib/dashboard-c/tokens";
import type { TickerOption, HeaderView } from "@/lib/dashboard-c/types";
import { Chevron } from "./Chevron";

export function TickerSelector({
  tickers,
  active,
  header,
  onSelect,
  onSoon,
}: {
  tickers: TickerOption[];
  active: string;
  header: HeaderView;
  onSelect: (ticker: string) => void;
  onSoon: (name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("click", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("click", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const handlePick = (t: TickerOption) => {
    setOpen(false);
    if (!t.ready) {
      onSoon(t.name);
      return;
    }
    if (t.ticker !== active) onSelect(t.ticker);
  };

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="flex items-center gap-2.5 rounded-2xl pl-2 pr-3 py-1.5 transition-all duration-300 hover:bg-surface"
        style={{ border: `1px solid ${C.line}`, background: "#FFFFFF", boxShadow: "var(--shadow-soft)" }}
      >
        <div
          className="w-9 h-9 rounded-xl grid place-items-center text-white text-[13px] font-bold shadow-sm shrink-0"
          style={{ background: `linear-gradient(135deg, ${C.emeraldSoft}, ${C.emerald})` }}
        >
          {header.logo}
        </div>
        <div className="text-left">
          <div className="font-bold text-[15px] leading-tight flex items-center gap-1.5">
            <span>{header.name}</span>
            <span className="text-faint text-xs font-medium tnum">{header.ticker}</span>
          </div>
          <div className="text-faint text-[11px] leading-tight">눌러서 종목 바꾸기</div>
        </div>
        <Chevron
          className="acc-chevron w-4 h-4 text-faint shrink-0 ml-0.5"
          style={{ transform: open ? "rotate(180deg)" : undefined }}
        />
      </button>

      {open && (
        <div
          role="listbox"
          aria-label="종목 선택"
          className="absolute left-0 top-[calc(100%+8px)] z-50 w-[248px] p-1.5 rounded-2xl card"
          style={{ boxShadow: "var(--shadow-card)" }}
        >
          {tickers.map((t) => {
            const selected = t.ticker === active;
            return (
              <button
                key={t.ticker}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => handlePick(t)}
                className={`stock-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left ${t.ready ? "" : "opacity-70"}`}
              >
                <span
                  className="w-8 h-8 rounded-lg grid place-items-center text-white text-[12px] font-bold shrink-0"
                  style={{ background: `linear-gradient(135deg, ${C.emeraldSoft}, ${C.emerald})` }}
                >
                  {t.logo}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-bold text-[14px] leading-tight">{t.name}</span>
                  <span className="block text-faint text-[11px] tnum leading-tight">{t.ticker}</span>
                </span>
                {selected ? (
                  <span className="text-[13px]" style={{ color: C.emerald }}>
                    ✓
                  </span>
                ) : !t.ready ? (
                  <span
                    className="text-[10px] font-semibold px-1.5 py-0.5 rounded-md"
                    style={{ color: C.amber, background: C.amberTint }}
                  >
                    준비중
                  </span>
                ) : null}
              </button>
            );
          })}
          {tickers.length === 0 && (
            <p className="px-3 py-3 text-faint text-[13px]">종목 목록을 불러오는 중이에요.</p>
          )}
        </div>
      )}
    </div>
  );
}
