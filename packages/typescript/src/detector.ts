import nlp from "compromise";
import { DEFAULT_ENTITIES, Entity } from "./models";

// High-confidence regex patterns
const PATTERNS: Array<[RegExp, string, number]> = [
  [/\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b/g,                       "EMAIL",        0.95],
  [/(?:\+\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b/g,                 "PHONE",        0.6],
  [/\b(?:\d{1,3}\.){3}\d{1,3}\b/g,                                                  "IP_ADDRESS",   0.95],
  [/\b(?:\d{4}[\s\-]?){3}\d{4}\b/g,                                                 "FINANCIAL_ID", 0.9],
  [/\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]{0,16})\b/g,                        "FINANCIAL_ID", 0.95],
  [/https?:\/\/[^\s]+/g,                                                             "URL",          0.95],
];

export class Detector {
  private entities:        string[];
  private confidenceFloor: number;

  constructor({
    entities,
    confidenceFloor = 0.35,
  }: {
    entities?:        string[];
    confidenceFloor?: number;
  } = {}) {
    this.entities        = entities ?? DEFAULT_ENTITIES;
    this.confidenceFloor = confidenceFloor;
  }

  analyze(text: string): Entity[] {
    if (!text.trim()) return [];

    const results: Entity[] = [];

    // Regex-based detection
    for (const [pattern, entityType, score] of PATTERNS) {
      if (this.entities.includes(entityType)) {
        results.push(...this._regex(text, pattern, entityType, score));
      }
    }

    // NLP-based detection (compromise)
    if (this.entities.includes("PERSON")) {
      results.push(...this._nlpPersons(text));
    }

    return this._deduplicate(results).filter((e) => e.score >= this.confidenceFloor);
  }

  private _regex(text: string, re: RegExp, entityType: string, score: number): Entity[] {
    re.lastIndex = 0;
    const results: Entity[] = [];
    let match: RegExpExecArray | null;
    while ((match = re.exec(text)) !== null) {
      results.push({
        text:       match[0],
        entityType,
        start:      match.index,
        end:        match.index + match[0].length,
        score,
      });
    }
    return results;
  }

  private _nlpPersons(text: string): Entity[] {
    const results: Entity[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const doc = (nlp as any)(text);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    doc.people().forEach((person: any) => {
      const personText: string = person.text();
      const idx = text.indexOf(personText);
      if (idx >= 0) {
        results.push({
          text:       personText,
          entityType: "PERSON",
          start:      idx,
          end:        idx + personText.length,
          score:      0.75,
        });
      }
    });
    return results;
  }

  private _deduplicate(entities: Entity[]): Entity[] {
    const sorted = [...entities].sort((a, b) => b.score - a.score);
    const kept: Entity[] = [];
    for (const e of sorted) {
      if (!kept.some((k) => e.start < k.end && e.end > k.start)) {
        kept.push(e);
      }
    }
    return kept;
  }
}
