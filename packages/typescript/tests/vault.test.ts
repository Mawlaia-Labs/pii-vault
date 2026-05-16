import { Vault } from "../src/vault";

let vault: Vault;

beforeEach(() => {
  vault = new Vault(":memory:");
});

test("store and retrieve", () => {
  vault.store("PERSON_abc12345", "John Smith", "PERSON");
  expect(vault.retrieve("PERSON_abc12345")).toBe("John Smith");
});

test("retrieve missing returns null", () => {
  expect(vault.retrieve("PERSON_unknown0")).toBeNull();
});

test("store is idempotent", () => {
  vault.store("EMAIL_abc12345", "john@acme.com", "EMAIL");
  vault.store("EMAIL_abc12345", "other@value.com", "EMAIL"); // should not overwrite
  expect(vault.retrieve("EMAIL_abc12345")).toBe("john@acme.com");
});

test("delete subject", () => {
  vault.store("PERSON_abc12345", "Alice", "PERSON", "user-1");
  vault.store("EMAIL_def67890", "alice@corp.com", "EMAIL", "user-1");
  vault.store("PERSON_xyz99999", "Bob", "PERSON", "user-2");

  const deleted = vault.deleteSubject("user-1");
  expect(deleted).toBe(2);
  expect(vault.retrieve("PERSON_abc12345")).toBeNull();
  expect(vault.retrieve("EMAIL_def67890")).toBeNull();
  expect(vault.retrieve("PERSON_xyz99999")).toBe("Bob");
});

test("list subject", () => {
  vault.store("PERSON_abc12345", "Alice", "PERSON", "user-1");
  vault.store("EMAIL_def67890", "alice@corp.com", "EMAIL", "user-1");

  const entries = vault.listSubject("user-1");
  expect(entries).toHaveLength(2);
  expect(entries.map((e) => e.token)).toContain("PERSON_abc12345");
});

test("count", () => {
  expect(vault.count()).toBe(0);
  vault.store("PERSON_abc12345", "Alice", "PERSON");
  vault.store("EMAIL_def67890", "alice@corp.com", "EMAIL");
  expect(vault.count()).toBe(2);
});
