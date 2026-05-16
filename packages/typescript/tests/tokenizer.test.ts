import { Tokenizer } from "../src/tokenizer";
import { Vault }     from "../src/vault";
import { Entity }    from "../src/models";

const KEY = "test-secret-key-do-not-use-in-prod";

function entity(text: string, entityType: string, start: number): Entity {
  return { text, entityType, start, end: start + text.length, score: 0.9 };
}

let vault: Vault;
let tokenizer: Tokenizer;

beforeEach(() => {
  vault     = new Vault(":memory:");
  tokenizer = new Tokenizer(vault, KEY);
});

test("tokenize single entity", () => {
  const text     = "Contact John Smith for details.";
  const entities = [entity("John Smith", "PERSON", 8)];
  const result   = tokenizer.tokenize(text, entities);

  expect(result).not.toContain("John Smith");
  expect(result).toMatch(/PERSON_[0-9a-f]{8}/);
});

test("tokenize is deterministic", () => {
  const text     = "Email alice@acme.com please.";
  const entities = [entity("alice@acme.com", "EMAIL", 6)];
  expect(tokenizer.tokenize(text, entities)).toBe(tokenizer.tokenize(text, entities));
});

test("dehydrate restores original", () => {
  const text     = "Contact John Smith at john@acme.com.";
  const entities = [
    entity("John Smith",   "PERSON", 8),
    entity("john@acme.com", "EMAIL", 22),
  ];
  const tokenized  = tokenizer.tokenize(text, entities);
  const dehydrated = tokenizer.dehydrate(tokenized);
  expect(dehydrated).toBe(text);
});

test("multiple entities no overlap", () => {
  const text     = "Alice (alice@corp.com) and Bob (bob@corp.com).";
  const entities = [
    entity("Alice",          "PERSON",  0),
    entity("alice@corp.com", "EMAIL",   7),
    entity("Bob",            "PERSON", 27),
    entity("bob@corp.com",   "EMAIL",  32),
  ];
  const tokenized  = tokenizer.tokenize(text, entities);
  expect(tokenized).not.toContain("Alice");
  expect(tokenized).not.toContain("alice@corp.com");
  expect(tokenized).not.toContain("Bob");

  const dehydrated = tokenizer.dehydrate(tokenized);
  expect(dehydrated).toBe(text);
});

test("opaque mode uses TOK prefix", () => {
  const t = new Tokenizer(new Vault(":memory:"), KEY, "opaque");
  const result = t.tokenize("John Smith called.", [entity("John Smith", "PERSON", 0)]);
  expect(result).toMatch(/TOK_[0-9a-f]{8}/);
  expect(result).not.toContain("PERSON");
});

test("tokenize messages", () => {
  const messages = [
    { role: "system", content: "You are a helpful assistant." },
    { role: "user",   content: "Summarise the case for John Smith." },
  ];
  const fakeDetector = {
    analyze: (text: string) =>
      text.includes("John Smith")
        ? [entity("John Smith", "PERSON", text.indexOf("John Smith"))]
        : [],
  };
  const tokenized = tokenizer.tokenizeMessages(messages, fakeDetector);
  expect(tokenized[1].content).not.toContain("John Smith");
  expect(tokenized[0].content).toBe("You are a helpful assistant.");
});

test("split stream safe — partial token held back", () => {
  const [safe, rem] = tokenizer.splitStreamSafe("Hello PERSON_a3f");
  expect(safe).toBe("Hello ");
  expect(rem).toBe("PERSON_a3f");
});

test("split stream safe — complete token yields everything", () => {
  const [, rem] = tokenizer.splitStreamSafe("Hello PERSON_a3f2b1c4 world");
  expect(rem).toBe("");
});

test("HMAC matches Python output for same key and value", () => {
  // Python: hmac.new(b"test-key", b"John Smith", hashlib.sha256).hexdigest()[:8] == "7fdd13cc"
  const t     = new Tokenizer(new Vault(":memory:"), "test-key");
  const result = t.tokenize("John Smith", [entity("John Smith", "PERSON", 0)]);
  expect(result).toContain("PERSON_7fdd13cc");
});
