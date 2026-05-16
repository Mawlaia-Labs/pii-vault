import { createHmac } from "crypto";
import { Entity, Message } from "./models";
import { Vault } from "./vault";

const TOKEN_RE         = /\b([A-Z][A-Z_]*_[0-9a-f]{8})\b/g;
const PARTIAL_TOKEN_RE = /[A-Z][A-Z_]*(?:_[0-9a-f]{0,7})?$/;

export class Tokenizer {
  constructor(
    private vault: Vault,
    private key:   string,
    private mode:  "typed" | "opaque" = "typed",
  ) {}

  // ── Core operations ────────────────────────────────────────────────────

  tokenize(text: string, entities: Entity[], subjectId?: string): string {
    if (entities.length === 0) return text;

    // Replace right-to-left so indices stay valid
    const sorted = [...entities].sort((a, b) => b.start - a.start);
    let result = text;

    for (const entity of sorted) {
      const value = text.slice(entity.start, entity.end);
      const token = this._makeToken(value, entity.entityType);
      this.vault.store(token, value, entity.entityType, subjectId);
      result = result.slice(0, entity.start) + token + result.slice(entity.end);
    }

    return result;
  }

  dehydrate(text: string): string {
    TOKEN_RE.lastIndex = 0;
    return text.replace(TOKEN_RE, (_, token: string) => this.vault.retrieve(token) ?? token);
  }

  // ── Message-list helpers ───────────────────────────────────────────────

  tokenizeMessages(
    messages:   Message[],
    detector:   { analyze(text: string): Entity[] },
    subjectId?: string,
  ): Message[] {
    return messages.map((msg) => {
      if (typeof msg.content === "string") {
        const entities = detector.analyze(msg.content);
        return { ...msg, content: this.tokenize(msg.content, entities, subjectId) };
      }
      return msg;
    });
  }

  dehydrateMessages(messages: Message[]): Message[] {
    return messages.map((msg) => {
      if (typeof msg.content === "string") {
        return { ...msg, content: this.dehydrate(msg.content) };
      }
      return msg;
    });
  }

  // ── Streaming helper ───────────────────────────────────────────────────

  splitStreamSafe(text: string): [string, string] {
    const match = PARTIAL_TOKEN_RE.exec(text);
    if (match) return [text.slice(0, match.index), text.slice(match.index)];
    return [text, ""];
  }

  // ── Internal ───────────────────────────────────────────────────────────

  private _makeToken(value: string, entityType: string): string {
    const sig    = createHmac("sha256", this.key).update(value).digest("hex").slice(0, 8);
    const prefix = this.mode === "typed" ? entityType : "TOK";
    return `${prefix}_${sig}`;
  }
}
