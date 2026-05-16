"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import type { SignalMarker } from "@/lib/types";

interface SignalMarkerPopoverProps {
  marker: SignalMarker;
  children: React.ReactNode;
  className?: string;
}

const MESSAGES = {
  buy: "매수 시그널",
  sell: "매도 시그널",
  price: "가격",
  sentiment: "감성 점수",
  reason: "근거",
} as const;

function formatPrice(value: number | null): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("ko-KR").format(value);
}

export function SignalMarkerPopover({
  marker,
  children,
  className,
}: SignalMarkerPopoverProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent
        className={cn("w-64 space-y-3 text-sm", className)}
        side="top"
        sideOffset={8}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <Badge variant={marker.kind === "BUY" ? "buy" : "sell"}>
            {marker.kind === "BUY" ? MESSAGES.buy : MESSAGES.sell}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {marker.time.slice(0, 10)}
          </span>
        </div>

        {/* Details */}
        <div className="space-y-1.5 text-xs">
          <div className="flex justify-between">
            <span className="text-muted-foreground">{MESSAGES.price}</span>
            <span className="font-medium tabular-nums">
              {formatPrice(marker.price)}
            </span>
          </div>
          {marker.sentiment_score != null && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">{MESSAGES.sentiment}</span>
              <span
                className={cn(
                  "font-medium tabular-nums",
                  marker.sentiment_score >= 34 && "text-signal-buy",
                  marker.sentiment_score <= -34 && "text-signal-sell"
                )}
              >
                {marker.sentiment_score >= 0 ? "+" : ""}
                {marker.sentiment_score.toFixed(1)}
              </span>
            </div>
          )}
        </div>

        {/* Reason */}
        {marker.reason && (
          <div className="border-t border-border pt-2">
            <p className="text-xs leading-relaxed text-muted-foreground">
              {marker.reason}
            </p>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
