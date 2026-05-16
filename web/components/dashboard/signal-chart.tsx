"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { Candle, SignalMarker, DivergenceMarker, Band } from "@/lib/types";

interface SignalChartProps {
  candles: Candle[];
  signals: SignalMarker[];
  divergences: DivergenceMarker[];
  band: Band;
  className?: string;
  onMarkerClick?: (marker: SignalMarker) => void;
}

/**
 * SignalChart — TradingView Lightweight Charts 기반 캔들 + 밴드 + 마커 차트 (T-056).
 *
 * PRD §F-4.1:
 * - 캔들스틱 차트
 * - 펀더멘털 밴드 (Area Series)
 * - BUY(▲ emerald) / SELL(▼ rose) 마커
 * - Divergence(◆ amber/violet) 마커
 */
export function SignalChart({
  candles,
  signals,
  divergences,
  band,
  className,
  onMarkerClick,
}: SignalChartProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const chartRef = React.useRef<import("lightweight-charts").IChartApi | null>(null);

  React.useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    let chart: import("lightweight-charts").IChartApi | null = null;

    const init = async () => {
      const { createChart, CrosshairMode, LineStyle } = await import(
        "lightweight-charts"
      );

      if (!containerRef.current) return;

      chart = createChart(containerRef.current, {
        layout: {
          background: { color: "transparent" },
          textColor: "hsl(0 0% 65%)",
          fontFamily: "inherit",
        },
        grid: {
          vertLines: { color: "hsl(240 4% 16% / 0.5)" },
          horzLines: { color: "hsl(240 4% 16% / 0.5)" },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
        },
        rightPriceScale: {
          borderColor: "hsl(240 4% 16%)",
        },
        timeScale: {
          borderColor: "hsl(240 4% 16%)",
          timeVisible: false,
        },
        handleScroll: true,
        handleScale: true,
      });

      chartRef.current = chart;

      // Candlestick series
      const candleSeries = chart.addCandlestickSeries({
        upColor: "hsl(158 70% 48%)",
        downColor: "hsl(350 89% 65%)",
        borderUpColor: "hsl(158 70% 48%)",
        borderDownColor: "hsl(350 89% 65%)",
        wickUpColor: "hsl(158 70% 48%)",
        wickDownColor: "hsl(350 89% 65%)",
      });
      candleSeries.setData(
        candles.map((c) => ({
          time: c.time as unknown as import("lightweight-charts").UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }))
      );

      // Band lines
      if (band.band_low != null && band.band_high != null) {
        const bandHighSeries = chart.addLineSeries({
          color: "hsl(240 5% 60% / 0.4)",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          crosshairMarkerVisible: false,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        bandHighSeries.setData(
          candles.map((c) => ({
            time: c.time as unknown as import("lightweight-charts").UTCTimestamp,
            value: band.band_high!,
          }))
        );

        const bandLowSeries = chart.addLineSeries({
          color: "hsl(240 5% 60% / 0.4)",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          crosshairMarkerVisible: false,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        bandLowSeries.setData(
          candles.map((c) => ({
            time: c.time as unknown as import("lightweight-charts").UTCTimestamp,
            value: band.band_low!,
          }))
        );
      }

      // Signal markers
      type TWCMarker = import("lightweight-charts").SeriesMarker<import("lightweight-charts").Time>;
      const markers: TWCMarker[] = signals
        .filter((s) => s.kind === "BUY" || s.kind === "SELL")
        .map((s) => ({
          time: s.time.slice(0, 10) as unknown as import("lightweight-charts").Time,
          position: s.kind === "BUY" ? ("belowBar" as const) : ("aboveBar" as const),
          color: s.kind === "BUY" ? "hsl(158 70% 48%)" : "hsl(350 89% 65%)",
          shape: s.kind === "BUY" ? ("arrowUp" as const) : ("arrowDown" as const),
          text: s.kind,
          size: 1.5,
        }));

      // Divergence markers
      const divMarkers: TWCMarker[] = divergences.map((d) => ({
        time: d.time.slice(0, 10) as unknown as import("lightweight-charts").Time,
        position: "inBar" as const,
        color:
          d.kind === "BULLISH"
            ? "hsl(38 95% 56%)"
            : "hsl(262 85% 66%)",
        shape: "circle" as const,
        text: d.kind === "BULLISH" ? "◆" : "◆",
        size: 1,
      }));

      candleSeries.setMarkers(
        [...markers, ...divMarkers].sort((a, b) =>
          String(a.time).localeCompare(String(b.time))
        )
      );

      // Fit content
      chart.timeScale().fitContent();

      // Marker click handler
      if (onMarkerClick) {
        chart.subscribeClick((param) => {
          if (!param.time) return;
          const timeStr = String(param.time);
          const matched = signals.find(
            (s) => s.time.startsWith(timeStr) && (s.kind === "BUY" || s.kind === "SELL")
          );
          if (matched) onMarkerClick(matched);
        });
      }
    };

    init();

    const handleResize = () => {
      if (chartRef.current && containerRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };

    const observer = new ResizeObserver(handleResize);
    if (containerRef.current) observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      if (chart) {
        chart.remove();
        chartRef.current = null;
      }
    };
  }, [candles, signals, divergences, band, onMarkerClick]);

  if (candles.length === 0) {
    return (
      <div
        className={cn(
          "flex h-full items-center justify-center text-sm text-muted-foreground",
          className
        )}
      >
        캔들 데이터가 없습니다
      </div>
    );
  }

  return <div ref={containerRef} className={cn("h-full w-full", className)} />;
}
