import { NextResponse } from "next/server";

import { getDb } from "@/lib/db";
import { buildDashboardSnapshot } from "@/lib/snapshot";

export const dynamic = "force-dynamic";

type RouteCtx = { params: { code: string } };

export async function GET(_request: Request, context: RouteCtx) {
  const raw = context.params.code ?? "";
  const stockCode = decodeURIComponent(raw).trim();
  if (!stockCode) {
    return NextResponse.json(
      { error: "stock_code_required" },
      { status: 400 }
    );
  }

  try {
    const db = await getDb();
    const snapshot = buildDashboardSnapshot(db, stockCode);
    return NextResponse.json(snapshot, {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "unknown_error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
