import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Shadcn UI 표준 `cn()` 헬퍼.
 *
 * 사용:
 *   <div className={cn("base", isActive && "bg-signal-buy")} />
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
