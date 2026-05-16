import { NextResponse } from "next/server";

import { dbFileExists, getDb } from "@/lib/db";

/**
 * SQLite 연결 가능 여부 (T-053).
 */
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    if (!dbFileExists()) {
      return NextResponse.json(
        { ok: false, db: false, error: "db_file_missing" },
        { status: 503 }
      );
    }
    const db = await getDb();
    db.run("SELECT 1");
    return NextResponse.json({ ok: true, db: true }, { status: 200 });
  } catch (e) {
    const message = e instanceof Error ? e.message : "unknown_error";
    return NextResponse.json(
      { ok: false, db: false, error: message },
      { status: 503 }
    );
  }
}
