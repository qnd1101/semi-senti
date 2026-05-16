"use client";

import * as React from "react";
import { BarChart3, Settings, TrendingUp, RefreshCw } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface SidebarProps {
  className?: string;
  children?: React.ReactNode;
}

const MESSAGES = {
  dashboard: "대시보드",
  admin: "관리자",
  autoRefresh: "자동 갱신",
  refreshInterval: "갱신 주기",
  minutes: "분",
} as const;

export function Sidebar({ className, children }: SidebarProps) {
  const [autoRefresh, setAutoRefresh] = React.useState(true);
  const [refreshInterval, setRefreshInterval] = React.useState([5]);

  return (
    <TooltipProvider delayDuration={300}>
      <aside
        className={cn(
          "flex h-full w-64 flex-col border-r border-border bg-card/50",
          className
        )}
      >
        {/* Logo / Brand */}
        <div className="flex h-14 items-center gap-2 border-b border-border px-4">
          <TrendingUp className="h-6 w-6 text-signal-buy" />
          <span className="text-lg font-semibold tracking-tight">
            Semi Senti
          </span>
        </div>

        {/* Stock Selector Area */}
        <div className="flex-1 overflow-y-auto p-4">
          {children}
        </div>

        {/* Refresh Settings */}
        <div className="border-t border-border p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
              <span>{MESSAGES.autoRefresh}</span>
            </div>
            <Switch
              checked={autoRefresh}
              onCheckedChange={setAutoRefresh}
              aria-label={MESSAGES.autoRefresh}
            />
          </div>

          {autoRefresh && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{MESSAGES.refreshInterval}</span>
                <span>
                  {refreshInterval[0]} {MESSAGES.minutes}
                </span>
              </div>
              <Slider
                value={refreshInterval}
                onValueChange={setRefreshInterval}
                min={1}
                max={30}
                step={1}
                className="w-full"
                aria-label={MESSAGES.refreshInterval}
              />
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="border-t border-border p-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                className="w-full justify-start gap-2"
                aria-current="page"
              >
                <BarChart3 className="h-4 w-4" />
                <span>{MESSAGES.dashboard}</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {MESSAGES.dashboard}
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                className="w-full justify-start gap-2 text-muted-foreground"
              >
                <Settings className="h-4 w-4" />
                <span>{MESSAGES.admin}</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {MESSAGES.admin}
            </TooltipContent>
          </Tooltip>
        </nav>
      </aside>
    </TooltipProvider>
  );
}
