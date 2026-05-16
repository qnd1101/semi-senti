"use client";

import * as React from "react";
import { Search } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Stock } from "@/lib/types";

interface StockSelectorProps {
  stocks: Stock[];
  value?: string;
  onValueChange?: (code: string) => void;
  placeholder?: string;
  className?: string;
  isLoading?: boolean;
}

const MESSAGES = {
  placeholder: "종목 선택",
  noStocks: "등록된 종목이 없습니다",
  loading: "로딩 중...",
} as const;

export function StockSelector({
  stocks,
  value,
  onValueChange,
  placeholder = MESSAGES.placeholder,
  className,
  isLoading = false,
}: StockSelectorProps) {
  const activeStocks = React.useMemo(
    () => stocks.filter((s) => s.is_active),
    [stocks]
  );

  if (isLoading) {
    return (
      <div
        className={cn(
          "flex h-10 w-full items-center justify-center rounded-md border border-input bg-background text-sm text-muted-foreground",
          className
        )}
      >
        {MESSAGES.loading}
      </div>
    );
  }

  if (activeStocks.length === 0) {
    return (
      <div
        className={cn(
          "flex h-10 w-full items-center justify-center rounded-md border border-input bg-background text-sm text-muted-foreground",
          className
        )}
      >
        {MESSAGES.noStocks}
      </div>
    );
  }

  return (
    <Select value={value} onValueChange={onValueChange}>
      <SelectTrigger className={cn("w-full", className)}>
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <SelectValue placeholder={placeholder} />
        </div>
      </SelectTrigger>
      <SelectContent>
        {activeStocks.map((stock) => (
          <SelectItem key={stock.stock_code} value={stock.stock_code}>
            <div className="flex items-center gap-2">
              <span className="font-medium">{stock.name}</span>
              <span className="text-xs text-muted-foreground">
                ({stock.stock_code})
              </span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
