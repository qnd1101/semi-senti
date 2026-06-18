"use client";

import { useState, useCallback, useMemo } from 'react';
import Link from 'next/link';
import { useScreener } from '@/lib/dashboard-c/hooks';
import type { ViewKey } from '@/app/page';
import { C } from '@/lib/dashboard-c/tokens';

// ── 등락 색 (한국식) ──────────────────────────────────────────
function pctColor(v: number | null): string {
  if (v == null) return C.muted;
  if (v > 0) return C.rose;
  if (v < 0) return '#2563EB';
  return C.muted;
}
function pctSign(v: number | null): string {
  if (v == null) return '—';
  return v > 0 ? `+${v.toFixed(2)}%` : `${v.toFixed(2)}%`;
}
function fmtPrice(v: number | null): string {
  if (v == null) return '—';
  return v.toLocaleString('ko-KR');
}

// ── 네비 항목 타입 ────────────────────────────────────────────
interface NavItem {
  key: ViewKey;
  label: string;
  icon: string;
}

const TOP_NAV: NavItem[] = [
  { key: 'screener', label: '시세', icon: '📊' },
];

const DETAIL_NAV: NavItem[] = [
  { key: 'home', label: '홈', icon: '🏠' },
  { key: 'chart', label: '차트', icon: '📈' },
  { key: 'news', label: '뉴스', icon: '📰' },
  { key: 'finance', label: '재무·공시', icon: '🧾' },
];

// ── Props ─────────────────────────────────────────────────────
interface SidebarProps {
  view: ViewKey;
  activeTicker: string;
  onViewChange: (v: ViewKey) => void;
  onSelectTicker: (code: string) => void;
}

// ── 데스크톱 사이드바 ─────────────────────────────────────────
export function Sidebar({ view, activeTicker, onViewChange, onSelectTicker }: SidebarProps) {
  const [search, setSearch] = useState('');
  const { data: rows } = useScreener('change', 'desc');

  const filtered = useMemo(() => {
    if (!rows) return [];
    if (!search.trim()) return rows;
    const q = search.trim().toLowerCase();
    return rows.filter(
      (r) => r.name.toLowerCase().includes(q) || r.stock_code.includes(q)
    );
  }, [rows, search]);

  const handleTickerClick = useCallback(
    (code: string) => {
      onSelectTicker(code);
      onViewChange('home');
    },
    [onSelectTicker, onViewChange]
  );

  return (
    <aside
      className="hidden md:flex flex-col shrink-0"
      style={{
        width: '200px',
        height: '100vh',
        position: 'sticky',
        top: 0,
        background: C.white,
        borderRight: `1px solid ${C.line}`,
        boxShadow: '1px 0 0 0 #ebf0f7',
      }}
    >
      {/* 로고 */}
      <div
        className="px-4 pt-5 pb-3 flex items-center gap-2"
        style={{ borderBottom: `1px solid ${C.line}` }}
      >
        <span className="text-base font-black tracking-tight" style={{ color: C.ink }}>
          Semi<span style={{ color: C.amber }}>Senti</span>
        </span>
      </div>

      {/* 시세 버튼 */}
      <div className="px-3 pt-3 pb-2">
        {TOP_NAV.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => onViewChange(item.key)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold transition-colors text-left"
            style={{
              background: view === item.key ? '#EEF6F2' : 'transparent',
              color: view === item.key ? C.emerald : C.muted,
            }}
            aria-current={view === item.key ? 'page' : undefined}
          >
            <span>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </div>

      {/* 종목 분석 섹션 */}
      <div className="px-3 pb-1">
        <p
          className="text-[10px] font-semibold uppercase tracking-widest px-1 pb-1"
          style={{ color: C.faint }}
        >
          종목 분석
        </p>
        {DETAIL_NAV.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => onViewChange(item.key)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold transition-colors text-left"
            style={{
              background: view === item.key ? C.track : 'transparent',
              color: view === item.key ? C.ink : C.muted,
            }}
            aria-current={view === item.key ? 'page' : undefined}
          >
            <span>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </div>

      {/* 구분선 */}
      <div style={{ borderTop: `1px solid ${C.line}`, margin: '8px 12px' }} />

      {/* 종목 검색 */}
      <div className="px-3 pb-1">
        <div
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
          style={{ background: C.track, border: `1px solid ${C.line}` }}
        >
          <span className="text-xs" style={{ color: C.faint }}>🔍</span>
          <input
            type="text"
            placeholder="종목 검색"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent text-xs outline-none"
            style={{ color: C.ink }}
            aria-label="종목 검색"
          />
        </div>
      </div>

      {/* 종목 리스트 — 독립 스크롤 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2 min-h-0">
        {!rows ? (
          <div className="px-2 py-3 space-y-1">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="skel h-8 rounded-lg" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-xs text-center py-4" style={{ color: C.faint }}>
            결과 없음
          </p>
        ) : (
          filtered.map((row) => {
            const isActive = row.stock_code === activeTicker;
            return (
              <button
                key={row.stock_code}
                type="button"
                onClick={() => handleTickerClick(row.stock_code)}
                className="w-full flex items-center justify-between px-2 py-2 rounded-lg transition-colors text-left stock-item"
                style={{
                  background: isActive ? '#EEF6F2' : 'transparent',
                  border: isActive ? `1px solid ${C.emeraldSoft}55` : '1px solid transparent',
                }}
                aria-selected={isActive}
              >
                <span
                  className="text-[12px] font-semibold truncate max-w-[90px]"
                  style={{ color: isActive ? C.emerald : C.ink }}
                >
                  {row.name}
                </span>
                <div className="text-right shrink-0">
                  <span className="block text-[11px] tnum font-medium" style={{ color: C.ink }}>
                    {fmtPrice(row.price)}
                  </span>
                  <span
                    className="block text-[10px] tnum font-bold"
                    style={{ color: pctColor(row.change_pct) }}
                  >
                    {pctSign(row.change_pct)}
                  </span>
                </div>
              </button>
            );
          })
        )}
      </div>

      {/* 관리자 링크 — 하단 고정 */}
      <div
        className="px-4 py-3 shrink-0"
        style={{ borderTop: `1px solid ${C.line}` }}
      >
        <Link
          href="/admin"
          className="text-xs font-medium transition-colors"
          style={{ color: C.faint }}
        >
          ⚙️ 관리자
        </Link>
      </div>
    </aside>
  );
}

// ── 모바일 하단 탭바 ─────────────────────────────────────────
const MOBILE_TABS: NavItem[] = [
  { key: 'screener', label: '시세', icon: '📊' },
  { key: 'home', label: '홈', icon: '🏠' },
  { key: 'chart', label: '차트', icon: '📈' },
  { key: 'news', label: '뉴스', icon: '📰' },
  { key: 'finance', label: '재무', icon: '🧾' },
];

interface MobileTabBarProps {
  view: ViewKey;
  onViewChange: (v: ViewKey) => void;
}

export function MobileTabBar({ view, onViewChange }: MobileTabBarProps) {
  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around px-1 pb-safe"
      style={{
        background: C.white,
        borderTop: `1px solid ${C.line}`,
        boxShadow: '0 -1px 0 0 #ebf0f7, 0 -8px 24px -8px rgba(26,43,69,0.08)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      }}
      role="tablist"
      aria-label="화면 전환"
    >
      {MOBILE_TABS.map((item) => {
        const isActive = view === item.key;
        return (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onViewChange(item.key)}
            className="flex flex-col items-center gap-0.5 px-2 py-2 min-w-[52px] transition-all"
            style={{ color: isActive ? C.emerald : C.faint }}
          >
            <span className="text-base leading-none">{item.icon}</span>
            <span className="text-[10px] font-semibold leading-tight">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
