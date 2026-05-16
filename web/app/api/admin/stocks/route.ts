import { NextResponse } from "next/server";

import { getDb, sqlAll, sqlGet } from "@/lib/db";
import type { SqlValue } from "sql.js";

export const dynamic = "force-dynamic";

/** GET /api/admin/stocks — 전체 종목 목록 (활성/비활성 포함) */
export async function GET() {
  try {
    const db = await getDb();
    const rows = sqlAll<{
      stock_code: SqlValue;
      name: SqlValue;
      market: SqlValue;
      is_active: SqlValue;
      created_at: SqlValue;
    }>(db, "SELECT stock_code, name, market, is_active, created_at FROM stocks ORDER BY name ASC");
    return NextResponse.json(rows, { status: 200 });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

/** POST /api/admin/stocks — 종목 추가 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { stock_code, name, market } = body as {
      stock_code?: string;
      name?: string;
      market?: string;
    };
    if (!stock_code || !name) {
      return NextResponse.json(
        { error: "stock_code and name are required" },
        { status: 400 }
      );
    }
    if (!/^\d{6}$/.test(stock_code)) {
      return NextResponse.json(
        { error: "stock_code must be 6 digits" },
        { status: 400 }
      );
    }

    const db = await getDb();
    const existing = sqlGet<{ stock_code: SqlValue }>(
      db,
      "SELECT stock_code FROM stocks WHERE stock_code = ?",
      [stock_code]
    );
    if (existing) {
      return NextResponse.json(
        { error: "stock_code already exists" },
        { status: 409 }
      );
    }

    db.run(
      "INSERT INTO stocks (stock_code, name, market, is_active) VALUES (?, ?, ?, 1)",
      [stock_code, name, market ?? "KOSPI"]
    );
    return NextResponse.json(
      { stock_code, name, market: market ?? "KOSPI", is_active: 1 },
      { status: 201 }
    );
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

/** DELETE /api/admin/stocks — 종목 삭제 (body: { stock_code }) */
export async function DELETE(request: Request) {
  try {
    const body = await request.json();
    const { stock_code } = body as { stock_code?: string };
    if (!stock_code) {
      return NextResponse.json({ error: "stock_code required" }, { status: 400 });
    }
    const db = await getDb();
    db.run("DELETE FROM stocks WHERE stock_code = ?", [stock_code]);
    return NextResponse.json({ deleted: stock_code }, { status: 200 });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

/** PATCH /api/admin/stocks — 종목 활성/비활성 토글 (body: { stock_code, is_active }) */
export async function PATCH(request: Request) {
  try {
    const body = await request.json();
    const { stock_code, is_active } = body as {
      stock_code?: string;
      is_active?: number;
    };
    if (!stock_code || is_active == null) {
      return NextResponse.json(
        { error: "stock_code and is_active required" },
        { status: 400 }
      );
    }
    const db = await getDb();
    db.run("UPDATE stocks SET is_active = ? WHERE stock_code = ?", [
      is_active ? 1 : 0,
      stock_code,
    ]);
    return NextResponse.json({ stock_code, is_active }, { status: 200 });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
