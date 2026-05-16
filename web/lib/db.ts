import fs from "fs";
import path from "path";

import initSqlJs, { type Database, type SqlValue } from "sql.js";

/**
 * SQLite read-only 인메모리 뷰 (sql.js WASM).
 * OS 네이티브 모듈 없이 Windows/Node 24 환경에서 동작 (T-051).
 *
 * 환경 변수 `SEMI_SENTI_DB_PATH` — `.env.local` 기준, 보통 레포의 `db/semi_senti.sqlite`.
 */

const WASM_SUBDIR = ["node_modules", "sql.js", "dist"] as const;

let dbSingleton: Database | null = null;
let initTask: Promise<Database> | null = null;

export function resolveDbPath(): string {
  const raw = process.env.SEMI_SENTI_DB_PATH?.trim();
  const rel = raw && raw.length > 0 ? raw : "../db/semi_senti.sqlite";
  return path.isAbsolute(rel) ? rel : path.resolve(process.cwd(), rel);
}

export function dbFileExists(): boolean {
  try {
    fs.accessSync(resolveDbPath(), fs.constants.R_OK);
    return true;
  } catch {
    return false;
  }
}

/** wasm 바이너리 경로 (next dev / next start 모두 `web/` cwd 가정). */
function wasmLocate(file: string): string {
  return path.join(process.cwd(), ...WASM_SUBDIR, file);
}

/**
 * 공유 DB 인스턴스. Route Handler에서만 사용 (Node 런타임).
 */
export async function getDb(): Promise<Database> {
  if (dbSingleton) return dbSingleton;
  if (!initTask) {
    initTask = (async () => {
      const SQL = await initSqlJs({
        locateFile: (f) => wasmLocate(f),
      });
      const filePath = resolveDbPath();
      const buf = fs.readFileSync(filePath);
      dbSingleton = new SQL.Database(buf);
      return dbSingleton;
    })();
  }
  return initTask;
}

/** Prepared statement 패턴 — `sql.js` 바인딩은 값 배열(`?` 순서). */
export function sqlAll<T extends Record<string, SqlValue>>(
  db: Database,
  sql: string,
  params: SqlValue[] = []
): T[] {
  const stmt = db.prepare(sql);
  stmt.bind(params);
  const out: T[] = [];
  while (stmt.step()) {
    out.push(stmt.getAsObject() as T);
  }
  stmt.free();
  return out;
}

export function sqlGet<T extends Record<string, SqlValue>>(
  db: Database,
  sql: string,
  params: SqlValue[] = []
): T | undefined {
  return sqlAll<T>(db, sql, params)[0];
}
