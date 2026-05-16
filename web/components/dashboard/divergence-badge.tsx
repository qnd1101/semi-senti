"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { DivergenceMarker } from "@/lib/types";

interface DivergenceBadgeProps {
  divergences: DivergenceMarker[];
  className?: string;
}

const MESSAGES = {
  bullish: "강세 다이버전스",
  bearish: "약세 다이버전스",
} as const;

export function DivergenceBadge({ divergences, className }: DivergenceBadgeProps) {
  if (divergences.length === 0) return null;

  const latest = divergences[divergences.length - 1]!;

  return (
    <Badge
      variant={latest.kind === "BULLISH" ? "bullish" : "bearish"}
      className={cn("gap-1", className)}
    >
      <span className="text-lg leading-none">◆</span>
      <span>
        {latest.kind === "BULLISH" ? MESSAGES.bullish : MESSAGES.bearish}
      </span>
    </Badge>
  );
}
