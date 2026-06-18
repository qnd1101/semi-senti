"use client";

import type { CandleData, SignalInfo } from "@/lib/types";
import { useEffect, useRef, useState } from "react";

interface Props {
  candles: CandleData[];
  signals?: {
    short: SignalInfo | null;
    mid: SignalInfo | null;
    long: SignalInfo | null;
  };
  bandLow?: number | null;
  bandHigh?: number | null;
}

const INTERVAL_OPTIONS = [
  { id: "1d", label: "일봉" },
  { id: "1wk", label: "주봉" },
  { id: "1mo", label: "월봉" },
  { id: "1y", label: "연봉" },
];

export function SignalChart({ candles, signals, bandLow, bandHigh }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<unknown>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || !candles.length) return;

    let chart: unknown;
    let candleSeries: unknown;

    (async () => {
      const { createChart, CrosshairMode, CandlestickSeries, LineSeries } = await import("lightweight-charts");
      if (!containerRef.current) return;

      chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight || 320,
        layout: {
          background: { color: "transparent" },
          textColor: "#a1a1aa",
        },
        grid: {
          vertLines: { color: "rgba(63,63,70,0.4)" },
          horzLines: { color: "rgba(63,63,70,0.4)" },
        },
        crosshair: { mode: CrosshairMode?.Normal },
        rightPriceScale: { borderColor: "#3f3f46" },
        timeScale: { borderColor: "#3f3f46", timeVisible: true },
      });
      chartRef.current = chart;

      // @ts-expect-error lightweight-charts API
      candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#34d399",
        downColor: "#fb7185",
        borderUpColor: "#34d399",
        borderDownColor: "#fb7185",
        wickUpColor: "#34d399",
        wickDownColor: "#fb7185",
      });

      // @ts-expect-error lightweight-charts API
      candleSeries.setData(
        candles.map((c) => ({
          time: c.time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }))
      );

      // 펀더멘털 밴드 라인
      if (bandLow) {
        // @ts-expect-error lightweight-charts API
        const lowLine = chart.addSeries(LineSeries, { color: "#22c55e55", lineWidth: 1, lineStyle: 2, priceLineVisible: false });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (lowLine as any).setData(candles.map((c) => ({ time: c.time, value: bandLow })));
      }
      if (bandHigh) {
        // @ts-expect-error lightweight-charts API
        const highLine = chart.addSeries(LineSeries, { color: "#fb718555", lineWidth: 1, lineStyle: 2, priceLineVisible: false });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (highLine as any).setData(candles.map((c) => ({ time: c.time, value: bandHigh })));
      }

      // 시그널 마커
      if (signals) {
        const markers: unknown[] = [];
        for (const [persp, sig] of Object.entries(signals)) {
          if (!sig) continue;
          const dateStr = sig.signaled_at?.substring(0, 10);
          if (!dateStr) continue;
          const color = sig.signal_type === "BUY" ? "#34d399" : sig.signal_type === "SELL" ? "#fb7185" : "#71717a";
          const prefix = { short: "단", mid: "중", long: "장" }[persp] || persp;
          markers.push({
            time: dateStr,
            position: sig.signal_type === "SELL" ? "aboveBar" : "belowBar",
            color,
            shape: sig.signal_type === "BUY" ? "arrowUp" : sig.signal_type === "SELL" ? "arrowDown" : "circle",
            text: `${prefix}/${sig.signal_type}`,
          });
        }
        if (markers.length) {
          // @ts-expect-error lightweight-charts API
          candleSeries.setMarkers(markers.sort((a, b) => (a.time > b.time ? 1 : -1)));
        }
      }

      // @ts-expect-error lightweight-charts API
      chart.timeScale().fitContent();
      setReady(true);

      const ro = new ResizeObserver(() => {
        if (containerRef.current) {
          // @ts-expect-error lightweight-charts API
          chart.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
      if (containerRef.current) ro.observe(containerRef.current);

      return () => {
        ro.disconnect();
        // @ts-expect-error lightweight-charts API
        chart.remove();
      };
    })();

    return () => {
      if (chartRef.current) {
        // @ts-expect-error lightweight-charts API
        chartRef.current.remove?.();
        chartRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candles]);

  return (
    <div className="w-full h-full relative">
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center text-zinc-500 text-sm">
          차트 로딩 중…
        </div>
      )}
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
}

export { INTERVAL_OPTIONS };
