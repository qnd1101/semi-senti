"use client";

import { useState, useCallback } from 'react';
import { useScreener } from '@/lib/dashboard-c/hooks';
import type { ScreenerRow, ScreenerSortKey, SortOrder } from '@/lib/dashboard-c/screener-types';
import { C } from '@/lib/dashboard-c/tokens';

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
  return v.toLocaleString('ko-KR') + '원';
}

function fmtVol(v: number | null): string {
  if (v == null) return '—';
  if (v >= 100_000_000) return (v / 100_000_000).toFixed(1) + '억';
  if (v >= 10_000) return (v / 10_000).toFixed(1) + '만';
  return v.toLocaleString('ko-KR');
}

function SortArrow({ col, active, order }: { col: string; active: string; order: SortOrder }) {
  if (col !== active) return <span className="text-[10px] opacity-25 ml-0.5">↕</span>;
  return <span className="text-[10px] ml-0.5">{order === 'asc' ? '↑' : '↓'}</span>;
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: 7 }).map((__, j) => (
            <td key={j} className="px-3 py-3">
              <div className="skel h-4 rounded" style={{ width: j === 0 ? '80px' : '60px' }} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

interface ColDef {
  key: ScreenerSortKey;
  label: string;
  align: 'left' | 'right';
  render: (row: ScreenerRow) => React.ReactNode;
}

const COLS: ColDef[] = [
  {
    key: 'name',
    label: '종목명',
    align: 'left',
    render: (r) => (
      <span className="font-semibold text-[13px]" style={{ color: C.ink }}>
        {r.name}
        <span className="block text-[11px] font-normal" style={{ color: C.faint }}>
          {r.stock_code}
        </span>
      </span>
    ),
  },
  {
    key: 'price',
    label: '현재가',
    align: 'right',
    render: (r) => (
      <span className="tnum text-[13px] font-semibold" style={{ color: C.ink }}>
        {fmtPrice(r.price)}
      </span>
    ),
  },
  {
    key: 'change',
    label: '등락률',
    align: 'right',
    render: (r) => (
      <span className="tnum text-[13px] font-bold" style={{ color: pctColor(r.change_pct) }}>
        {pctSign(r.change_pct)}
      </span>
    ),
  },
  {
    key: 'volume',
    label: '거래량',
    align: 'right',
    render: (r) => (
      <span className="tnum text-[13px]" style={{ color: C.muted }}>
        {fmtVol(r.volume)}
      </span>
    ),
  },
  {
    key: 'w1',
    label: '1주',
    align: 'right',
    render: (r) => (
      <span className="tnum text-[13px] font-medium" style={{ color: pctColor(r.return_1w) }}>
        {pctSign(r.return_1w)}
      </span>
    ),
  },
  {
    key: 'm1',
    label: '1개월',
    align: 'right',
    render: (r) => (
      <span className="tnum text-[13px] font-medium" style={{ color: pctColor(r.return_1m) }}>
        {pctSign(r.return_1m)}
      </span>
    ),
  },
  {
    key: 'y1',
    label: '1년',
    align: 'right',
    render: (r) => (
      <span className="tnum text-[13px] font-medium" style={{ color: pctColor(r.return_1y) }}>
        {pctSign(r.return_1y)}
      </span>
    ),
  },
];

interface ScreenerProps {
  onSelectTicker: (code: string, name: string, isTracked: boolean) => void;
}

export function Screener({ onSelectTicker }: ScreenerProps) {
  const [sort, setSort] = useState<ScreenerSortKey>('change');
  const [order, setOrder] = useState<SortOrder>('desc');

  const { data: rows, isLoading, error } = useScreener(sort, order);

  const handleHeaderClick = useCallback(
    (col: ScreenerSortKey) => {
      if (sort === col) {
        setOrder((o) => (o === 'desc' ? 'asc' : 'desc'));
      } else {
        setSort(col);
        setOrder('desc');
      }
    },
    [sort]
  );

  const handleRowClick = useCallback(
    (row: ScreenerRow) => {
      onSelectTicker(row.stock_code, row.name, row.is_tracked);
    },
    [onSelectTicker]
  );

  return (
    <section className="rise d2">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold" style={{ color: C.ink }}>
            반도체 시세
          </h1>
          <p className="text-xs mt-0.5" style={{ color: C.faint }}>
            주요 반도체 종목 {rows ? rows.length : '—'}개 · 헤더 클릭으로 정렬
          </p>
        </div>
        {error && (
          <span
            className="text-xs px-3 py-1 rounded-full"
            style={{ background: C.amberTint, color: C.amber }}
          >
            서버 준비중
          </span>
        )}
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse">
          <thead>
            <tr style={{ borderBottom: `1px solid ${C.line}` }}>
              {COLS.map((col) => (
                <th
                  key={col.key}
                  className={`px-3 py-3 text-xs font-semibold cursor-pointer select-none transition-colors hover:opacity-70 ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                  style={{ color: sort === col.key ? C.ink : C.muted }}
                  onClick={() => handleHeaderClick(col.key)}
                  aria-sort={
                    sort === col.key
                      ? order === 'asc'
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                  }
                >
                  {col.label}
                  <SortArrow col={col.key} active={sort} order={order} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && !rows ? (
              <SkeletonRows />
            ) : !rows || rows.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  className="px-3 py-12 text-center text-sm"
                  style={{ color: C.faint }}
                >
                  데이터를 불러오는 중이에요
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.stock_code}
                  className="stock-item cursor-pointer transition-colors"
                  style={{ borderBottom: `1px solid ${C.line}` }}
                  onClick={() => handleRowClick(row)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleRowClick(row);
                    }
                  }}
                  aria-label={`${row.name} 상세 보기`}
                >
                  {COLS.map((col) => (
                    <td
                      key={col.key}
                      className={`px-3 py-3 ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                    >
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="text-center text-xs mt-4" style={{ color: C.faint }}>
        종목 클릭 시 상세 분석 페이지로 이동합니다
      </p>
    </section>
  );
}
