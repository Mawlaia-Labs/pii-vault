import Database from "better-sqlite3";

interface TokenRow {
  token:      string;
  value:      string;
  entityType: string;
  createdAt:  string;
}

export class Vault {
  private db: Database.Database;

  constructor(path: string = ":memory:") {
    this.db = new Database(path);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS tokens (
        token       TEXT PRIMARY KEY,
        value       TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        subject_id  TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  store(token: string, value: string, entityType: string, subjectId?: string): void {
    this.db
      .prepare("INSERT OR IGNORE INTO tokens (token, value, entity_type, subject_id) VALUES (?, ?, ?, ?)")
      .run(token, value, entityType, subjectId ?? null);
  }

  retrieve(token: string): string | null {
    const row = this.db
      .prepare("SELECT value FROM tokens WHERE token = ?")
      .get(token) as { value: string } | undefined;
    return row?.value ?? null;
  }

  deleteSubject(subjectId: string): number {
    return this.db
      .prepare("DELETE FROM tokens WHERE subject_id = ?")
      .run(subjectId).changes;
  }

  listSubject(subjectId: string): TokenRow[] {
    return this.db
      .prepare("SELECT token, value, entity_type as entityType, created_at as createdAt FROM tokens WHERE subject_id = ?")
      .all(subjectId) as TokenRow[];
  }

  count(): number {
    return (this.db.prepare("SELECT COUNT(*) as n FROM tokens").get() as { n: number }).n;
  }
}
