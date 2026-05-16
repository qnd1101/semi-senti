import { NextResponse } from "next/server";

import { getDb } from "@/lib/db";
import { listActiveStocks } from "@/lib/snapshot";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const db = await getDb();
    const stocks = listActiveStocks(db);
    return NextResponse.json(stocks, {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "unknown_error";
    return NextResponse.json(
      { error: message, stocks: [] },
      { status: 500 }
    );
  }
}
