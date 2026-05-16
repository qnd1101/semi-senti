import { NextResponse } from "next/server";

import { getDb, sqlAll, sqlGet } from "@/lib/db";
import type { SqlValue } from "sql.js";

export const dynamic = "force-dynamic";

/** GET /api/admin/system — 시스템 상태 요약 (T-047) */
export async function GET() {
  try {
    const db = await getDb();

    const tables = [
      "stocks",
      "financials",
      "news",
      "signals",
      "sentiment_scores",
      "notifications",
      "cycle_scores",
    ];
    const tableCounts: Record<string, number> = {};
    for (const t of tables) {
      const row = sqlGet<{ cnt: SqlValue }>(
        db,
        `SELECT COUNT(*) AS cnt FROM ${t}`
      );
      tableCounts[t] = Number(row?.cnt ?? 0);
    }

    const failedNotifs = sqlGet<{ cnt: SqlValue }>(
      db,
      "SELECT COUNT(*) AS cnt FROM notifications WHERE status = 'FAILED'"
    );

    const stocks = sqlAll<{
      stock_code: SqlValue;
      name: SqlValue;
      market: SqlValue;
      is_active: SqlValue;
    }>(db, "SELECT stock_code, name, market, is_active FROM stocks ORDER BY name");

    const stockStatuses = [];
    for (const s of stocks) {
      const code = String(s.stock_code);
      const lastPrice = sqlGet<{ d: SqlValue }>(
        db,
        "SELECT MAX(record_date) AS d FROM financials WHERE stock_code = ?",
        [code]
      );
      const lastSignal = sqlGet<{ d: SqlValue }>(
        db,
        "SELECT MAX(signaled_at) AS d FROM signals WHERE stock_code = ?",
        [code]
      );
      const newsCount = sqlGet<{ cnt: SqlValue }>(
        db,
        "SELECT COUNT(*) AS cnt FROM news WHERE stock_code = ?",
        [code]
      );
      stockStatuses.push({
        stock_code: code,
        name: String(s.name),
        market: s.market != null ? String(s.market) : null,
        is_active: Number(s.is_active) === 1,
        last_price_at: lastPrice?.d != null ? String(lastPrice.d) : null,
        last_signal_at: lastSignal?.d != null ? String(lastSignal.d) : null,
        news_count: Number(newsCount?.cnt ?? 0),
      });
    }

    return NextResponse.json({
      generated_at: new Date().toISOString(),
      table_counts: tableCounts,
      failed_notifications: Number(failedNotifs?.cnt ?? 0),
      stocks: stockStatuses,
    });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
