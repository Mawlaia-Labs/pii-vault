# How to stop sending PII to OpenAI in 5 minutes

_Published by Mawlaia · May 2026_

---

Every time you call `client.chat.completions.create(messages=[...])`, you probably send names, emails, phone numbers, and IP addresses straight to OpenAI's servers. That's a GDPR Article 28 violation unless you have a DPA signed and your users consented to cross-border processing.

Most teams know this. Most teams ship anyway because the fix sounds hard.

It's not. Here's what it looks like with `pii-vault`:

```python
# Before
from openai import OpenAI
client = OpenAI(api_key="sk-...")

# After
from pii_vault import SafeOpenAI
client = SafeOpenAI(api_key="sk-...", vault_key="my-local-secret")
```

That's the entire diff. The rest of your code — `client.chat.completions.create(...)`, streaming, function calls — stays identical. PII never leaves your process.

---

## What actually happens

When you call `.create()`, pii-vault intercepts the messages before they hit the wire:

1. **Detect**: Microsoft Presidio (battle-tested, 50+ recognizers) scans each message for emails, names, phone numbers, addresses, IPs, financial IDs, URLs.
2. **Tokenize**: Each detected entity is replaced with a deterministic HMAC token — `alice@corp.com` becomes `EMAIL_7fdd13cc`. The original value is stored in a local SQLite vault, encrypted.
3. **Send**: The sanitized messages go to OpenAI. The model never sees the real values.
4. **Restore**: When the response comes back, tokens in the output are replaced back with originals. Your app sees `alice@corp.com`, not `EMAIL_7fdd13cc`.

Streaming works the same way — we buffer partial tokens at the stream boundary before dehydrating.

---

## Why typed tokens?

We could have used opaque UUIDs (`tok_a1b2c3d4`). We chose typed prefixes (`EMAIL_7fdd13cc`) because the model needs context to reason correctly.

Compare:

```
# Opaque — model loses context
"Please respond to tok_a1b2c3d4"           # is this a name? email? ID?

# Typed — model still works correctly
"Please respond to EMAIL_7fdd13cc"          # model knows it's an email-shaped thing
```

You can switch to opaque mode for HIPAA/high-security contexts where entity-type leakage matters:

```python
client = SafeOpenAI(api_key="...", vault_key="...", token_mode="opaque")
```

---

## DSAR compliance in one call

Under GDPR Article 17, users can request deletion of their personal data. With pii-vault, you honour that in one line:

```python
vault.delete_subject("user-123")  # deletes all PII for this user from the vault
```

All tokens for that user become unresolvable. Historical logs that reference those tokens are effectively anonymized.

---

## What it doesn't do

- **It's not encryption at rest** of your app data — it's a tokenization layer for LLM calls
- **It doesn't handle structured output** where PII appears in JSON fields (coming in Phase 2)
- **It doesn't sign a DPA for you** — you still need agreements with OpenAI for the (now PII-free) data

---

## Installation

```bash
pip install pii-vault[openai]
python -m spacy download en_core_web_sm
```

TypeScript:

```bash
npm install pii-vault
```

Source, docs, and the full test suite: [github.com/mawlaia/pii-vault](https://github.com/mawlaia/pii-vault)

---

_pii-vault is open-source (MIT). The hosted version with a managed vault, EU+US regions, and SOC 2 audit trail is coming in Q3 2026. If you want early access, email dev@mawlaia.com._
