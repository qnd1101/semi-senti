"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { KeywordContribution } from "@/lib/types";

interface KeywordTrendProps {
  keywords: KeywordContribution[];
  maxDisplay?: number;
  className?: string;
}

const MESSAGES = {
  noKeywords: "키워드 데이터 없음",
} as const;

export function KeywordTrend({
  keywords,
  maxDisplay = 8,
  className,
}: KeywordTrendProps) {
  const displayed = keywords.slice(0, maxDisplay);

  if (displayed.length === 0) {
    return (
      <p className={cn("text-xs text-muted-foreground", className)}>
        {MESSAGES.noKeywords}
      </p>
    );
  }

  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {displayed.map((kw) => (
        <Badge
          key={kw.keyword}
          variant="secondary"
          className={cn(
            "gap-1 text-xs",
            kw.weight > 0 && "border-signal-buy/30",
            kw.weight < 0 && "border-signal-sell/30"
          )}
        >
          <span>{kw.keyword}</span>
          <span
            className={cn(
              "text-[10px] tabular-nums",
              kw.weight > 0 && "text-signal-buy",
              kw.weight < 0 && "text-signal-sell"
            )}
          >
            {kw.weight > 0 ? "+" : ""}
            {kw.weight.toFixed(1)}
          </span>
        </Badge>
      ))}
    </div>
  );
}
