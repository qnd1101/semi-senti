"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import type { StaleStatus } from "@/lib/types";

interface AppShellProps {
  children: React.ReactNode;
  stockName?: string;
  stockCode?: string;
  currentPrice?: number | null;
  currency?: string;
  baseDate?: string | null;
  stale?: StaleStatus;
  sidebarContent?: React.ReactNode;
  sidebarAutoRefreshEnabled?: boolean;
  onSidebarAutoRefreshChange?: (enabled: boolean) => void;
  sidebarPollMinutes?: number;
  onSidebarPollMinutesChange?: (minutes: number) => void;
  className?: string;
}

/**
 * AppShell — Semi Senti 메인 레이아웃 셸.
 *
 * 구조:
 * ┌──────────────────────────────────────────┐
 * │ Sidebar │ Topbar                         │
 * │         ├────────────────────────────────│
 * │         │ Main (viewport-lock)           │
 * │         │                                │
 * └─────────┴────────────────────────────────┘
 *
 * PRD §4.3 1화면 집중 원칙: Main 영역은 스크롤 없이 100vh - topbar 높이에 맞춤.
 */
export function AppShell({
  children,
  stockName,
  stockCode,
  currentPrice,
  currency,
  baseDate,
  stale,
  sidebarContent,
  sidebarAutoRefreshEnabled,
  onSidebarAutoRefreshChange,
  sidebarPollMinutes,
  onSidebarPollMinutesChange,
  className,
}: AppShellProps) {
  return (
    <div className={cn("flex h-screen overflow-hidden bg-background", className)}>
      {/* Sidebar */}
      <Sidebar
        autoRefreshEnabled={sidebarAutoRefreshEnabled}
        onAutoRefreshChange={onSidebarAutoRefreshChange}
        pollMinutes={sidebarPollMinutes}
        onPollMinutesChange={onSidebarPollMinutesChange}
      >
        {sidebarContent}
      </Sidebar>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <Topbar
          stockName={stockName}
          stockCode={stockCode}
          currentPrice={currentPrice}
          currency={currency}
          baseDate={baseDate}
          stale={stale}
        />

        {/* Main — viewport-lock */}
        <main className="viewport-lock flex-1 overflow-auto p-4">
          {children}
        </main>
      </div>
    </div>
  );
}
