"use client";

import { useEffect, useMemo, useRef } from "react";
import { C, MARKER_STYLE } from "@/lib/dashboard-c/tokens";
import { smoothPath } from "@/lib/dashboard-c/smoothPath";
import type { ChartView } from "@/lib/dashboard-c/types";

const W = 720;
const H = 200;
const PAD_X = 10;
const PAD_TOP = 20;
const PAD_BOT = 18;

export function LineChartWithMarkers({ chart }: { chart: ChartView | null }) {
  return (
    <section className="rise d5 card px-6 sm:px-8 py-7 mb-5">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <span className="text-xl">📈</span> 최근 주가 흐름
        </h2>
        <span className="text-faint text-xs">
          최근 {chart?.barCount ?? 0}거래일
        </span>
      </div>
      <p className="text-inkMuted text-sm mb-4">
        최근 주가가 어떻게 움직였는지, 신호가 켜진 지점과 함께 살펴보세요.
      </p>
      {chart && chart.priceTrend.length >= 2 ? (
        <>
          <ChartSvg chart={chart} />
          <div className="flex items-center justify-center gap-5 text-xs mt-2">
            <span className="flex items-center gap-1.5 text-ink font-medium">
              <span className="w-3.5 h-[3px] rounded-full bg-ink" />
              주가
            </span>
            <span className="flex items-center gap-1.5 font-medium" style={{ color: C.emerald }}>
              <span className="w-3.5 h-[3px] rounded-full" style={{ background: C.emerald }} />
              신호 지점
            </span>
          </div>
        </>
      ) : (
        <div className="h-[200px] grid place-items-center text-faint text-sm">
          주가 흐름을 불러오고 있어요.
        </div>
      )}
    </section>
  );
}

function ChartSvg({ chart }: { chart: ChartView }) {
  const svgRef = useRef<SVGSVGElement>(null);

  const { price, lastP, markers } = useMemo(() => {
    const price = smoothPath(chart.priceTrend, W, H, PAD_X, PAD_TOP, PAD_BOT);
    const lastP = price.pts[price.pts.length - 1];
    const markers = chart.markers
      .map((mk) => {
        const pt = price.pts[mk.idx];
        if (!pt) return null;
        const ms = MARKER_STYLE[mk.signal];
        const up = pt[1] < 70;
        const labelY = up ? pt[1] + 26 : pt[1] - 16;
        const anchor: "start" | "middle" | "end" = pt[0] > W - 120 ? "end" : pt[0] < 120 ? "start" : "middle";
        const dx = anchor === "end" ? -8 : anchor === "start" ? 8 : 0;
        return { mk, pt, ms, labelY, anchor, dx };
      })
      .filter((m): m is NonNullable<typeof m> => m !== null);
    return { price, lastP, markers };
  }, [chart]);

  // 라인 드로잉 애니메이션 (prefers-reduced-motion 존중)
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const path = svg.querySelector<SVGPathElement>(".line-anim");
    if (!path) return;
    const len = path.getTotalLength();

    // 모션 최소화 설정이면 드로잉을 생략하고 즉시 최종 상태로 렌더한다.
    const reduceMotion =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      path.style.strokeDasharray = "none";
      path.style.strokeDashoffset = "0";
      return;
    }

    path.style.strokeDasharray = String(len);
    path.style.strokeDashoffset = String(len);
    const anim = path.animate(
      [{ strokeDashoffset: len }, { strokeDashoffset: 0 }],
      { duration: 1500, delay: 550, easing: "cubic-bezier(0.16,1,0.3,1)", fill: "forwards" }
    );
    return () => anim.cancel();
  }, [price.d]);

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      className="w-full h-[200px]"
      role="img"
      aria-label="최근 주가 흐름 그래프. 신호가 켜진 지점이 마커로 표시돼요."
    >
      <defs>
        <linearGradient id="cArea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={C.ink} stopOpacity="0.09" />
          <stop offset="100%" stopColor={C.ink} stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* 주가 영역 + 선 */}
      <path d={`${price.d} L ${lastP[0].toFixed(1)} ${H} L ${PAD_X} ${H} Z`} fill="url(#cArea)" />
      <path
        d={price.d}
        fill="none"
        stroke={C.ink}
        strokeWidth="2.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="line-anim"
      />
      {/* 시그널 마커 */}
      {markers.map((m, i) => (
        <g
          key={i}
          className="chart-marker"
          tabIndex={0}
          role="button"
          aria-label={`${m.mk.short} 지점: ${m.mk.tip}`}
        >
          <circle cx={m.pt[0].toFixed(1)} cy={m.pt[1].toFixed(1)} r="11" fill={m.ms.glow} className="mk-halo" />
          <circle cx={m.pt[0].toFixed(1)} cy={m.pt[1].toFixed(1)} r="5.5" fill={C.white} stroke={m.ms.color} strokeWidth="3" />
          <text
            x={(m.pt[0] + m.dx).toFixed(1)}
            y={m.labelY.toFixed(1)}
            textAnchor={m.anchor}
            fontSize="11.5"
            fontWeight="700"
            fill={m.ms.color}
          >
            {m.ms.arrow} {m.mk.short}
          </text>
          <title>{m.mk.tip}</title>
        </g>
      ))}
      {/* 끝점 */}
      <circle cx={lastP[0].toFixed(1)} cy={lastP[1].toFixed(1)} r="5" fill={C.white} stroke={C.ink} strokeWidth="2.6" />
    </svg>
  );
}
