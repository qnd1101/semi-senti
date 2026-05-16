"use client";

import * as React from "react";

const DEFAULT_SECONDS = 300;

function defaultMinutesFromEnv(): number {
  if (typeof window === "undefined") return 5;
  const n = Number(process.env.NEXT_PUBLIC_AUTO_REFRESH_SECONDS);
  const sec = Number.isFinite(n) && n > 0 ? n : DEFAULT_SECONDS;
  return Math.max(1, Math.round(sec / 60));
}

export interface UseAutoRefreshResult {
  /** SWR에 넘길 `refreshInterval` (ms). 0이면 폴링 끔. */
  refreshIntervalMs: number;
  enabled: boolean;
  setEnabled: React.Dispatch<React.SetStateAction<boolean>>;
  pollMinutes: number;
  setPollMinutes: React.Dispatch<React.SetStateAction<number>>;
}

/**
 * 자동 갱신 on/off + 폴링 주기(분). 기본값은 `NEXT_PUBLIC_AUTO_REFRESH_SECONDS`에서 유도 (T-054).
 */
export function useAutoRefresh(): UseAutoRefreshResult {
  const [enabled, setEnabled] = React.useState(true);
  const [pollMinutes, setPollMinutes] = React.useState(defaultMinutesFromEnv);

  const refreshIntervalMs = enabled ? pollMinutes * 60_000 : 0;

  return {
    refreshIntervalMs,
    enabled,
    setEnabled,
    pollMinutes,
    setPollMinutes,
  };
}
