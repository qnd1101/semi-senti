import type { Database, SqlValue } from "sql.js";

import { classifySentiment } from "@/lib/classify-sentiment";
import { sqlAll, sqlGet } from "@/lib/db";
import type {
  Band,
  Candle,
  CycleScore,
  DashboardSnapshot,
  DivergenceMarker,
  FinancialSummaryDTO,
  KeywordContribution,
  SentimentSnapshot,
  SignalKind,
  SignalMarker,
  StaleStatus,
  Stock,
} from "@/lib/types";

const SENTIMENT_KEYWORD_LIMIT = 15;
const DEFAULT_STALE_AFTER_HOURS = 24;

/** `cycle.py` `_PHASE_LABEL_KO` 와 동일. */
const PHASE_LABEL_KO: Record<string, string> = {
  TROUGH: "저점 (회복 임박)",
  EARLY_CYCLE: "회복 초입",
  MID_CYCLE: "확장 국면",
  LATE_CYCLE: "후기 호황",
  PEAK: "정점 (조정 임박)",
};

export interface SnapshotBuildOptions {
  candleLimit?: number;
  signalLimit?: number;
  staleAfterHours?: number;
}

export function listActiveStocks(db: Database): Stock[] {
  const rows = sqlAll<{
    stock_code: SqlValue;
    name: SqlValue;
    market: SqlValue;
    is_active: SqlValue;
  }>(
    db,
    `SELECT stock_code, name, market, is_active FROM stocks
     WHERE is_active = 1 ORDER BY name ASC`
  );
  return rows.map((r) => ({
    stock_code: String(r.stock_code ?? ""),
    name: String(r.name ?? ""),
    market: r.market == null ? null : String(r.market),
    is_active: Number(r.is_active) === 1,
  }));
}

function safeFloat(v: SqlValue): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function extractDate(v: SqlValue): string | null {
  if (v == null) return null;
  const t = String(v);
  return t.length >= 10 ? t.slice(0, 10) : null;
}

function parseIsoToUtcMs(raw: SqlValue): number | null {
  if (raw == null) return null;
  const s = String(raw).replace(" ", "T");
  const ms = Date.parse(s.length === 10 ? `${s}T00:00:00Z` : `${s}Z`);
  return Number.isFinite(ms) ? ms : null;
}

function buildSignalReason(rationale: string, tooltip: string): string {
  const a = (rationale ?? "").trim();
  const b = (tooltip ?? "").trim();
  if (a && b && a !== b) return `${a}\n${b}`;
  return a || b || "";
}

function mapSignalKind(t: string): SignalKind | null {
  const u = t.toUpperCase();
  if (u === "BUY" || u === "SELL" || u === "HOLD") return u;
  return null;
}

function parseTopKeywordsJson(raw: SqlValue): KeywordContribution[] {
  if (raw == null || raw === "") return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(String(raw));
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  const out: KeywordContribution[] = [];
  for (const item of parsed) {
    if (!item || typeof item !== "object") continue;
    const o = item as Record<string, unknown>;
    const word = o.word ?? o.keyword;
    if (typeof word !== "string") continue;
    const weight = safeFloat(o.weight as SqlValue) ?? 0;
    const count = Math.trunc(Number(o.count) || 0);
    out.push({ keyword: word, weight, count });
  }
  return out;
}

function fetchCandles(
  db: Database,
  stockCode: string,
  limit: number
): Candle[] {
  const rows = sqlAll<{
    record_date: SqlValue;
    open_price: SqlValue;
    high_price: SqlValue;
    low_price: SqlValue;
    close_price: SqlValue;
    volume: SqlValue;
  }>(
    db,
    `SELECT record_date, open_price, high_price, low_price, close_price, volume
     FROM financials WHERE stock_code = ? AND close_price IS NOT NULL
     ORDER BY record_date DESC LIMIT ?`,
    [stockCode, limit]
  ).reverse();

  const candles: Candle[] = [];
  for (const r of rows) {
    const timeStr = extractDate(r.record_date);
    const close = safeFloat(r.close_price);
    if (!timeStr || close == null) continue;
    candles.push({
      time: timeStr,
      open: safeFloat(r.open_price) ?? close,
      high: safeFloat(r.high_price) ?? close,
      low: safeFloat(r.low_price) ?? close,
      close,
      volume: Math.trunc(Number(r.volume) || 0),
    });
  }
  return candles;
}

function buildSignalTooltipRow(row: {
  sentiment_score: SqlValue;
  price: SqlValue;
  band_low: SqlValue;
  band_high: SqlValue;
  signal_type: SqlValue;
}): string {
  const parts: string[] = [];
  const sent = safeFloat(row.sentiment_score);
  if (sent != null) parts.push(`감성 ${sent >= 0 ? "+" : ""}${sent.toFixed(1)}`);
  const price = safeFloat(row.price);
  if (price != null) parts.push(`현재가 ${price.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}`);
  const bandLow = safeFloat(row.band_low);
  const bandHigh = safeFloat(row.band_high);
  const sig = String(row.signal_type ?? "").toUpperCase();
  if (sig === "BUY" && bandLow != null && price != null && bandLow !== 0) {
    const diffPct = ((price - bandLow) / bandLow) * 100;
    parts.push(
      `밴드 하단 ${bandLow.toLocaleString("ko-KR", { maximumFractionDigits: 0 })} 대비 ${diffPct >= 0 ? "+" : ""}${diffPct.toFixed(2)}%`
    );
  } else if (sig === "SELL" && bandHigh != null && price != null && bandHigh !== 0) {
    const diffPct = ((price - bandHigh) / bandHigh) * 100;
    parts.push(
      `밴드 상단 ${bandHigh.toLocaleString("ko-KR", { maximumFractionDigits: 0 })} 대비 ${diffPct >= 0 ? "+" : ""}${diffPct.toFixed(2)}%`
    );
  }
  return parts.length > 0 ? parts.join(" / ") : "근거 정보 없음";
}

function fetchSignals(
  db: Database,
  stockCode: string,
  limit: number
): SignalMarker[] {
  const rows = sqlAll<{
    signal_type: SqlValue;
    price: SqlValue;
    band_low: SqlValue;
    band_high: SqlValue;
    sentiment_score: SqlValue;
    rationale: SqlValue;
    signaled_at: SqlValue;
  }>(
    db,
    `SELECT signal_type, price, band_low, band_high, sentiment_score, rationale, signaled_at
     FROM signals WHERE stock_code = ?
     ORDER BY signaled_at DESC LIMIT ?`,
    [stockCode, limit]
  ).reverse();

  const markers: SignalMarker[] = [];
  for (const r of rows) {
    const kind = mapSignalKind(String(r.signal_type ?? ""));
    if (kind !== "BUY" && kind !== "SELL") continue;
    const timeStr = extractDate(r.signaled_at);
    if (!timeStr) continue;
    const tooltip = buildSignalTooltipRow(r);
    const rationale = String(r.rationale ?? "");
    markers.push({
      time: timeStr,
      kind,
      price: safeFloat(r.price),
      reason: buildSignalReason(rationale, tooltip),
      color_token: kind === "BUY" ? "signal.buy" : "signal.sell",
      sentiment_score: safeFloat(r.sentiment_score),
    });
  }
  return markers;
}

/**
 * 다이버전스는 Python `DivergenceDetector` 런타임 산출 — SQL만으로는 동일 결과를 내지 않음.
 * FastAPI/분석 트리거(T-058) 연계 전까지 빈 배열.
 */
function fetchDivergences(): DivergenceMarker[] {
  return [];
}

function fetchBand(db: Database, stockCode: string): Band {
  const row = sqlGet<{ band_low: SqlValue; band_high: SqlValue }>(
    db,
    `SELECT band_low, band_high FROM signals
     WHERE stock_code = ? AND band_low IS NOT NULL AND band_high IS NOT NULL
     ORDER BY signaled_at DESC LIMIT 1`,
    [stockCode]
  );
  if (!row) {
    return { band_low: null, band_high: null, method: "unavailable" };
  }
  return {
    band_low: safeFloat(row.band_low),
    band_high: safeFloat(row.band_high),
    method: "from_latest_signal",
  };
}

function fetchSentimentHistory(
  db: Database,
  stockCode: string,
  maxPoints: number
): Array<{ date: string; score: number }> {
  const rows = sqlAll<{ score_date: SqlValue; score: SqlValue }>(
    db,
    `SELECT score_date, score FROM sentiment_scores
     WHERE stock_code = ? ORDER BY score_date DESC LIMIT ?`,
    [stockCode, maxPoints]
  );
  return rows
    .reverse()
    .map((r) => {
      const d = extractDate(r.score_date);
      const s = safeFloat(r.score);
      if (!d || s == null) return null;
      return { date: d, score: s };
    })
    .filter((x): x is { date: string; score: number } => x != null);
}

function fetchSentiment(db: Database, stockCode: string): SentimentSnapshot {
  const empty: SentimentSnapshot = {
    score: null,
    bucket: "UNKNOWN",
    bucket_label_ko: "데이터 없음",
    history: [],
    top_keywords: [],
    updated_at: null,
  };
  const row = sqlGet<{
    score_date: SqlValue;
    score: SqlValue;
    raw_score: SqlValue;
    news_count: SqlValue;
    top_keywords: SqlValue;
  }>(
    db,
    `SELECT score_date, score, raw_score, news_count, top_keywords
     FROM sentiment_scores WHERE stock_code = ?
     ORDER BY score_date DESC LIMIT 1`,
    [stockCode]
  );
  if (!row) return empty;

  const score = safeFloat(row.score);
  const classification = classifySentiment(score);
  const kws = parseTopKeywordsJson(row.top_keywords).slice(
    0,
    SENTIMENT_KEYWORD_LIMIT
  );
  const history = fetchSentimentHistory(db, stockCode, 30);
  const dateStr = extractDate(row.score_date);
  return {
    score,
    bucket: classification.key,
    bucket_label_ko: classification.label_ko,
    history,
    top_keywords: kws,
    updated_at: dateStr ? `${dateStr}T00:00:00.000Z` : null,
  };
}

function fetchFinancialSummary(
  db: Database,
  stockCode: string
): FinancialSummaryDTO {
  const empty: FinancialSummaryDTO = {
    current_price: null,
    currency: "KRW",
    record_date: null,
    revenue: null,
    operating_income: null,
    per: null,
    pbr: null,
    eps: null,
  };
  const latest = sqlGet<{
    record_date: SqlValue;
    close_price: SqlValue;
    currency: SqlValue;
  }>(
    db,
    `SELECT record_date, close_price, currency FROM financials
     WHERE stock_code = ? AND close_price IS NOT NULL
     ORDER BY record_date DESC LIMIT 1`,
    [stockCode]
  );
  if (!latest) return empty;

  const result: FinancialSummaryDTO = {
    ...empty,
    current_price: safeFloat(latest.close_price),
    record_date: extractDate(latest.record_date),
    currency: String(latest.currency ?? "KRW"),
  };

  for (const col of ["revenue", "operating_profit", "per", "pbr", "eps"] as const) {
    const row = sqlGet<{ v: SqlValue }>(
      db,
      `SELECT ${col} AS v FROM financials WHERE stock_code = ?
       AND ${col} IS NOT NULL ORDER BY record_date DESC LIMIT 1`,
      [stockCode]
    );
    const v = row ? safeFloat(row.v) : null;
    switch (col) {
      case "revenue":
        result.revenue = v;
        break;
      case "operating_profit":
        result.operating_income = v;
        break;
      case "per":
        result.per = v;
        break;
      case "pbr":
        result.pbr = v;
        break;
      case "eps":
        result.eps = v;
        break;
      default:
        break;
    }
  }
  return result;
}

function fetchCycle(db: Database, stockCode: string): CycleScore | null {
  const row = sqlGet<{
    score_date: SqlValue;
    cycle_score: SqlValue;
    phase: SqlValue;
    inventory_turnover: SqlValue;
    revenue_growth_pct: SqlValue;
    op_margin_pct: SqlValue;
    created_at: SqlValue;
  }>(
    db,
    `SELECT score_date, cycle_score, phase, inventory_turnover,
            revenue_growth_pct, op_margin_pct, created_at
     FROM cycle_scores WHERE stock_code = ?
     ORDER BY score_date DESC LIMIT 1`,
    [stockCode]
  );
  if (!row) return null;
  const raw = safeFloat(row.cycle_score);
  const s =
    raw == null
      ? null
      : Math.round(((Math.max(-100, Math.min(100, raw)) + 100) / 2) * 100) / 100;
  const phase = String(row.phase ?? "MID_CYCLE");
  return {
    score: s,
    label: PHASE_LABEL_KO[phase] ?? phase,
    inventory_turnover: safeFloat(row.inventory_turnover),
    yoy_revenue: safeFloat(row.revenue_growth_pct),
    updated_at: row.created_at != null ? String(row.created_at) : null,
  };
}

function computeStaleStatus(
  db: Database,
  stockCode: string,
  staleAfterHours: number
): StaleStatus {
  const empty: StaleStatus = {
    is_stale: false,
    last_updated: null,
    hours_old: null,
    message: "",
  };
  const row = sqlGet<{ last_at: SqlValue }>(
    db,
    `SELECT MAX(updated_at) AS last_at FROM financials WHERE stock_code = ?`,
    [stockCode]
  );
  const lastRaw = row?.last_at;
  if (lastRaw == null || lastRaw === "") {
    return {
      is_stale: true,
      last_updated: null,
      hours_old: null,
      message: "아직 수집된 데이터가 없습니다.",
    };
  }
  const lastMs = parseIsoToUtcMs(lastRaw);
  if (lastMs == null) {
    return {
      is_stale: true,
      last_updated: String(lastRaw),
      hours_old: null,
      message: "",
    };
  }
  const now = Date.now();
  const hoursOld = Math.max(0, (now - lastMs) / 3600_000);
  const isStale = hoursOld > staleAfterHours;
  const lastUpdated = new Date(lastMs)
    .toISOString()
    .replace("T", " ")
    .slice(0, 19);
  return {
    is_stale: isStale,
    last_updated: lastUpdated,
    hours_old: Math.round(hoursOld * 100) / 100,
    message: isStale
      ? `외부 API 갱신이 지연되었습니다. 약 ${hoursOld.toFixed(
          1
        )}시간 전 데이터 기준으로 표시됩니다.`
      : "",
  };
}

export function buildDashboardSnapshot(
  db: Database,
  stockCode: string,
  options: SnapshotBuildOptions = {}
): DashboardSnapshot {
  const candleLimit = options.candleLimit ?? 180;
  const signalLimit = options.signalLimit ?? 60;
  const staleAfterHours =
    options.staleAfterHours ?? DEFAULT_STALE_AFTER_HOURS;

  const stockRow = sqlGet<{ name: SqlValue }>(
    db,
    `SELECT name FROM stocks WHERE stock_code = ?`,
    [stockCode]
  );
  const stockName = stockRow?.name != null ? String(stockRow.name) : stockCode;

  return {
    stock_code: stockCode,
    stock_name: stockName,
    candles: fetchCandles(db, stockCode, candleLimit),
    signals: fetchSignals(db, stockCode, signalLimit),
    divergences: fetchDivergences(),
    sentiment: fetchSentiment(db, stockCode),
    financial: fetchFinancialSummary(db, stockCode),
    band: fetchBand(db, stockCode),
    cycle: fetchCycle(db, stockCode),
    stale: computeStaleStatus(db, stockCode, staleAfterHours),
    generated_at: new Date().toISOString(),
  };
}
