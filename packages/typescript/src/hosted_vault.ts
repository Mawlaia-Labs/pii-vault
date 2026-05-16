export interface HostedVaultOptions {
  apiKey: string;
  vaultUrl?: string;
  timeout?: number;
}

interface PendingEntry {
  token: string;
  value: string;
  entity_type: string;
  subject_id?: string;
}

export class HostedVault {
  private readonly base: string;
  private readonly headers: Record<string, string>;
  private readonly timeout: number;
  private pending: PendingEntry[] = [];

  constructor({ apiKey, vaultUrl = "https://api.mawlaia.com", timeout = 10_000 }: HostedVaultOptions) {
    this.base = vaultUrl.replace(/\/$/, "");
    this.headers = {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    };
    this.timeout = timeout;
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), this.timeout);
    try {
      const res = await fetch(`${this.base}${path}`, {
        method: "POST",
        headers: this.headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Mawlaia API error: ${res.status} ${await res.text()}`);
      return res.json() as Promise<T>;
    } finally {
      clearTimeout(id);
    }
  }

  private async get<T>(path: string): Promise<T> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), this.timeout);
    try {
      const res = await fetch(`${this.base}${path}`, {
        headers: this.headers,
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Mawlaia API error: ${res.status} ${await res.text()}`);
      return res.json() as Promise<T>;
    } finally {
      clearTimeout(id);
    }
  }

  store(token: string, value: string, entityType: string, subjectId?: string): void {
    this.pending.push({ token, value, entity_type: entityType, subject_id: subjectId });
  }

  async flush(): Promise<number> {
    if (this.pending.length === 0) return 0;
    const entries = this.pending.splice(0);
    const data = await this.post<{ stored: number }>("/v1/pii-vault/tokens", { entries });
    return data.stored;
  }

  async retrieve(token: string): Promise<string | null> {
    const map = await this.batchRetrieve([token]);
    return map[token] ?? null;
  }

  async batchRetrieve(tokens: string[]): Promise<Record<string, string | null>> {
    if (tokens.length === 0) return {};
    const data = await this.post<{ values: Record<string, string | null> }>("/v1/pii-vault/tokens/lookup", { tokens });
    return data.values;
  }

  async deleteSubject(subjectId: string): Promise<number> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), this.timeout);
    try {
      const res = await fetch(`${this.base}/v1/pii-vault/subjects/${subjectId}`, {
        method: "DELETE",
        headers: this.headers,
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Mawlaia API error: ${res.status}`);
      const data = await res.json() as { deleted_count: number };
      return data.deleted_count;
    } finally {
      clearTimeout(id);
    }
  }

  async listSubject(subjectId: string): Promise<Record<string, unknown>[]> {
    const data = await this.get<{ tokens: Record<string, unknown>[] }>(`/v1/pii-vault/subjects/${subjectId}`);
    return data.tokens;
  }

  async count(): Promise<number> {
    const data = await this.get<{ total_entries: number }>("/v1/pii-vault/stats");
    return data.total_entries;
  }
}
