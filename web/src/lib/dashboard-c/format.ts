/** 표시용 포맷 유틸 (값만 — 산출 로직과 무관). */

/** 억원 단위를 입문자용 "약 N조원" 문자열로. */
export function eokToJo(eok: number): string {
  const jo = eok / 10000;
  const num = jo >= 100 ? String(Math.round(jo)) : jo.toFixed(1).replace(/\.0$/, "");
  return "약 " + num + "조원";
}

/** 원 단위 금액을 입문자용 "약 N조원 / N억원" 으로 (적응형). */
export function wonToKoreanAmount(won: number): string {
  const jo = won / 1e12;
  if (jo >= 1) {
    const num = jo >= 100 ? String(Math.round(jo)) : jo.toFixed(1).replace(/\.0$/, "");
    return "약 " + num + "조원";
  }
  const eok = won / 1e8;
  const num = eok >= 100 ? String(Math.round(eok)) : eok.toFixed(1).replace(/\.0$/, "");
  return "약 " + num + "억원";
}

/** 천단위 콤마 (ko-KR). */
export function won(n: number): string {
  return Math.round(n).toLocaleString("ko-KR");
}

/** 소수 1자리 고정. */
export function dec1(n: number): string {
  return n.toFixed(1);
}

/**
 * 감성 점수 표시용: 정수 반올림 + 부호 prefix.
 * 예) 87.4053 → "+87", -12.7 → "-13"
 */
export function sentiFmt(score: number): string {
  const rounded = Math.round(score);
  return `${rounded >= 0 ? "+" : ""}${rounded}`;
}

/**
 * 밴드 위치 % 표시용: 정수 반올림.
 * 예) 124.0 → "124", 68.7 → "69"
 */
export function bandPosFmt(pct: number): string {
  return String(Math.round(pct));
}

/** ISO 날짜/시각을 "N시간 전 / 어제 / N일 전 / yyyy.mm.dd" 상대 표기로. */
export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const diffMs = Date.now() - t;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "방금 전";
  if (diffMin < 60) return `${diffMin}분 전`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}시간 전`;
  const diffD = Math.floor(diffH / 24);
  if (diffD === 1) return "어제";
  if (diffD < 7) return `${diffD}일 전`;
  const d = new Date(t);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

/** 등락 표시: 부호/금액/퍼센트 (close 대비 전일). 전일가 미상이면 null. */
export interface ChangeView {
  dir: "▲" | "▼" | "—";
  amount: string;
  pct: string;
  tone: "up" | "down" | "flat";
}
export function buildChange(close: number | null, prevClose: number | null): ChangeView | null {
  if (close == null) return null;
  if (prevClose == null || prevClose === 0) return null;
  const diff = close - prevClose;
  const pct = (diff / prevClose) * 100;
  const tone = diff > 0 ? "up" : diff < 0 ? "down" : "flat";
  const dir = diff > 0 ? "▲" : diff < 0 ? "▼" : "—";
  return {
    dir,
    amount: won(Math.abs(diff)),
    pct: `${diff >= 0 ? "+" : "-"}${Math.abs(pct).toFixed(2)}%`,
    tone,
  };
}
