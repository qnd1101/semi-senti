import { C, TONE } from "@/lib/dashboard-c/tokens";
import type { HeaderView } from "@/lib/dashboard-c/types";

export function StockHeader({ header }: { header: HeaderView }) {
  const change = header.change;
  const color = change ? TONE[change.tone] : C.muted;
  return (
    <div className="text-right">
      <div className="text-[19px] font-bold tnum leading-none">
        {header.price}
        {header.price !== "—" && <span className="text-sm text-inkMuted font-medium ml-0.5">원</span>}
      </div>
      {change ? (
        <div className="text-[12px] font-semibold tnum mt-1" style={{ color }}>
          {change.dir} {change.amount} · {change.pct}
        </div>
      ) : (
        <div className="text-faint text-[12px] font-medium mt-1">등락 정보 준비 중</div>
      )}
    </div>
  );
}
