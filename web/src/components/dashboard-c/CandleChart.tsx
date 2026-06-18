"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { IChartApi, ISeriesApi, SeriesType, Time } from "lightweight-charts";
import { useCandles } from "@/lib/dashboard-c/hooks";
import { C } from "@/lib/dashboard-c/tokens";

type Interval = "1d" | "1wk" | "1mo";

interface TooltipData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

const INTERVAL_BUTTONS: { key: Interval; label: string }[] = [
  { key: "1d", label: "일봉" },
  { key: "1wk", label: "주봉" },
  { key: "1mo", label: "월봉" },
];

/** 한국 주식 색: 상승 빨강 / 하락 파랑 */
const UP_COLOR = "#ef4444";
const DOWN_COLOR = "#3b82f6";

function fmtPrice(v: number) {
  return v.toLocaleString("ko-KR");
}

export function CandleChart({ code }: { code: string }) {
  const [interval, setInterval] = useState<Interval>("1d");
  const { data, isLoading, error } = useCandles(code || null, interval);

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<SeriesType, Time> | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || !data?.candles?.length) return;

    const cleanupFns: (() => void)[] = [];

    (async () => {
      const { createChart, CrosshairMode, CandlestickSeries } = await import("lightweight-charts");
      if (!containerRef.current) return;

      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
      }

      const chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: 360,
        layout: {
          background: { color: "transparent" },
          textColor: C.muted,
          fontFamily: "Pretendard, system-ui, sans-serif",
        },
        grid: {
          vertLines: { color: C.line },
          horzLines: { color: C.line },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: {
          borderColor: C.line,
          scaleMargins: { top: 0.1, bottom: 0.1 },
        },
        timeScale: {
          borderColor: C.line,
          timeVisible: true,
          secondsVisible: false,
        },
        handleScroll: true,
        handleScale: true,
      });
      chartRef.current = chart;

      const series = chart.addSeries(CandlestickSeries, {
        upColor: UP_COLOR,
        downColor: DOWN_COLOR,
        borderUpColor: UP_COLOR,
        borderDownColor: DOWN_COLOR,
        wickUpColor: UP_COLOR,
        wickDownColor: DOWN_COLOR,
      });
      seriesRef.current = series;

      const chartData = data.candles.map((c) => ({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));

      series.setData(chartData);

      const INIT_BARS: Record<Interval, number> = { "1d": 30, "1wk": 26, "1mo": 24 };
      const bars = INIT_BARS[interval];
      if (chartData.length > bars) {
        chart.timeScale().setVisibleRange({
          from: chartData[chartData.length - bars].time,
          to: chartData[chartData.length - 1].time,
        });
      } else {
        chart.timeScale().fitContent();
      }

      const handleCrosshair = (param: unknown) => {
        const p = param as {
          time?: unknown;
          point?: { x: number; y: number };
          seriesData?: Map<unknown, { open: number; high: number; low: number; close: number }>;
        };
        if (!p.time || !p.point) {
          setTooltip(null);
          return;
        }
        const bar = p.seriesData?.get(seriesRef.current);
        if (!bar) {
          setTooltip(null);
          return;
        }
        setTooltip({
          time: String(p.time),
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        });
      };

      chart.subscribeCrosshairMove(handleCrosshair);
      cleanupFns.push(() => {
        chart.unsubscribeCrosshairMove(handleCrosshair);
      });

      const ro = new ResizeObserver(() => {
        if (containerRef.current && chartRef.current) {
          chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
      if (containerRef.current) ro.observe(containerRef.current);
      cleanupFns.push(() => ro.disconnect());

      setReady(true);
    })();

    return () => {
      cleanupFns.forEach((fn) => fn());
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
      }
      setReady(false);
      setTooltip(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.candles, interval]);

  const handleInterval = useCallback((iv: Interval) => {
    setInterval(iv);
    setTooltip(null);
  }, []);

  const isUp = tooltip ? tooltip.close >= tooltip.open : false;

  return (
    <section className="rise d2 card px-6 sm:px-8 py-7 mb-5">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <span className="text-xl">📊</span> 캔들 차트
        </h2>
        <div className="flex items-center gap-1.5" role="group" aria-label="봉주기 선택">
          {INTERVAL_BUTTONS.map((btn) => (
            <button
              key={btn.key}
              type="button"
              aria-pressed={interval === btn.key}
              onClick={() => handleInterval(btn.key)}
              className="news-filter px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-300"
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      <div
        className="mb-3 h-8 flex items-center gap-4 text-xs font-mono tabular-nums"
        style={{ color: C.muted }}
      >
        {tooltip ? (
          <>
            <span style={{ color: C.ink, fontWeight: 600 }}>{tooltip.time}</span>
            <span>시 <b style={{ color: isUp ? UP_COLOR : DOWN_COLOR }}>{fmtPrice(tooltip.open)}</b></span>
            <span>고 <b style={{ color: isUp ? UP_COLOR : DOWN_COLOR }}>{fmtPrice(tooltip.high)}</b></span>
            <span>저 <b style={{ color: isUp ? UP_COLOR : DOWN_COLOR }}>{fmtPrice(tooltip.low)}</b></span>
            <span>종 <b style={{ color: isUp ? UP_COLOR : DOWN_COLOR }}>{fmtPrice(tooltip.close)}</b></span>
          </>
        ) : (
          <span style={{ color: C.faint }}>차트에 마우스를 올려 가격을 확인하세요</span>
        )}
      </div>

      <div className="relative" style={{ height: 360 }}>
        {(isLoading || !ready) && !error && (
          <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ color: C.faint, fontSize: 14 }}
          >
            차트를 불러오는 중…
          </div>
        )}
        {error && (
          <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ color: C.rose, fontSize: 14 }}
          >
            차트 데이터를 불러오지 못했어요.
          </div>
        )}
        {!isLoading && !error && data && data.candles.length === 0 && (
          <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ color: C.faint, fontSize: 14 }}
          >
            해당 기간의 캔들 데이터가 없어요.
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />
      </div>

      <div className="flex items-center gap-4 mt-3 text-xs" style={{ color: C.muted }}>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: UP_COLOR }} />
          상승
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: DOWN_COLOR }} />
          하락
        </span>
        <span style={{ color: C.faint }}>· 스크롤/핀치로 줌</span>
      </div>
    </section>
  );
}