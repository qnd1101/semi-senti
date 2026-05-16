"use client";

import * as React from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StaleStatus } from "@/lib/types";

interface StaleBannerProps {
  stale: StaleStatus;
  className?: string;
}

export function StaleBanner({ stale, className }: StaleBannerProps) {
  if (!stale.is_stale) return null;

  return (
    <div
      role="alert"
      className={cn(
        "flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive",
        className
      )}
    >
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>{stale.message || "데이터 갱신이 지연되고 있습니다."}</span>
    </div>
  );
}
