import { Detector } from "../src/detector";

let detector: Detector;

beforeAll(() => {
  detector = new Detector();
});

test("detects email", () => {
  const entities = detector.analyze("Send it to alice@acme.com please.");
  const types    = new Set(entities.map((e) => e.entityType));
  expect(types.has("EMAIL")).toBe(true);
});

test("detects phone", () => {
  const entities = detector.analyze("Call me at +1 650 555 0199.");
  const types    = new Set(entities.map((e) => e.entityType));
  expect(types.has("PHONE")).toBe(true);
});

test("detects IP address", () => {
  const entities = detector.analyze("Server is at 192.168.1.100.");
  const types    = new Set(entities.map((e) => e.entityType));
  expect(types.has("IP_ADDRESS")).toBe(true);
});

test("detects URL", () => {
  const entities = detector.analyze("Visit https://acme.com for more.");
  const types    = new Set(entities.map((e) => e.entityType));
  expect(types.has("URL")).toBe(true);
});

test("empty string returns empty", () => {
  expect(detector.analyze("")).toHaveLength(0);
});

test("no PII returns empty or no personal entities", () => {
  const entities = detector.analyze("The sky is blue and the grass is green.");
  const persons  = entities.filter((e) => e.entityType === "PERSON");
  expect(persons).toHaveLength(0);
});

test("entity spans are correct", () => {
  const text     = "Email alice@acme.com today.";
  const entities = detector.analyze(text);
  const emails   = entities.filter((e) => e.entityType === "EMAIL");
  expect(emails.length).toBeGreaterThan(0);
  for (const e of emails) {
    expect(text.slice(e.start, e.end)).toBe(e.text);
  }
});

test("no overlapping spans", () => {
  const entities = detector.analyze("Alice alice@corp.com +1 650 555 0199");
  for (let i = 0; i < entities.length; i++) {
    for (let j = i + 1; j < entities.length; j++) {
      const a = entities[i], b = entities[j];
      expect(a.start < b.end && a.end > b.start).toBe(false);
    }
  }
});
