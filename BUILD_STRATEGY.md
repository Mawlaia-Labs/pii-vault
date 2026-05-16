# PII Vault — Build Strategy

*How we build it, in what order, with what tech.*

---

## 1. Architecture Overview

Two repos, two separate concerns:

```
mawlaia/pii-vault          (public OSS)
├── packages/python/       → PyPI: pii-vault
├── packages/typescript/   → npm: pii-vault
└── proxy/                 → Docker: mawlaia/pii-vault-proxy

mawlaia/pii-vault-cloud    (private)
├── api/                   → Hosted vault REST API (FastAPI)
├── dashboard/             → Next.js dashboard
└── infra/                 → Fly.io / Terraform config
```

The open-source repo contains everything needed to **self-host**. The cloud repo adds managed vault, key rotation, multi-region, compliance, and billing.

---

## 2. Core Components

```
                    ┌─────────────────────────────────┐
  App code          │         pii-vault SDK            │
  ─────────────     │                                  │
  SafeOpenAI()  ──► │  1. Detect   spaCy NER           │
  SafeAnthropic()   │  2. Tokenize  token ↔ value map  │
                    │  3. Proxy     forward to LLM      │
                    │  4. Dehydrate restore tokens      │
                    └──────────────┬──────────────────-┘
                                   │
                    ┌──────────────▼──────────────────-┐
                    │            Vault                  │
                    │   SQLite (local / OSS)            │
                    │   Postgres + KMS (hosted)         │
                    └──────────────────────────────────┘
```

### Component 1 — Detector
Identifies PII entities in text before sending to LLM.
- **Library:** spaCy `en_core_web_sm` + custom rule patterns
- **Entities:** PERSON, EMAIL, PHONE, ADDRESS, ORG, DATE, MEDICAL_ID, FINANCIAL_ID, IP_ADDRESS
- **Output:** list of `{text, entity_type, start, end, confidence}`
- **Latency target:** <20ms per 1K tokens (CPU, no GPU needed)

### Component 2 — Tokenizer
Deterministic mapping from PII value → opaque token.
- **Token format:** `<TYPE>_<8-char-hash>` e.g. `PERSON_a3f2b1c4`, `EMAIL_9d1e2f3a`
- **Deterministic:** same value always maps to same token (HMAC-based, keyed per vault)
- **Format-preserving option:** email-shaped token for emails, phone-shaped for phones
- **Storage:** `{token → encrypted_value}` in vault

### Component 3 — Proxy
Intercepts LLM API calls, tokenizes input, dehydrates output.
- **In-process:** Python/TypeScript SDK wraps provider client directly
- **Sidecar:** HTTP proxy for language-agnostic use (Phase 1)
- **Providers (Phase 0):** OpenAI, Anthropic
- **Providers (Phase 1):** Google Gemini, Cohere, Mistral, Bedrock, Azure OpenAI
- **Compatibility:** drop-in replacement, same return types as native SDKs

### Component 4 — Vault
Stores and retrieves token↔value mappings.
- **Local (OSS):** SQLite, single file, zero config
- **Hosted:** PostgreSQL + AWS KMS envelope encryption
- **API:** `vault.store(token, value)`, `vault.retrieve(token)`, `vault.delete_subject(subject_id)`

---

## 3. Technology Decisions

| Decision | Choice | Why |
|---|---|---|
| NER engine | spaCy `en_core_web_sm` | Fast, local, CPU-only, no API cost, good enough for Phase 0 |
| Token hashing | HMAC-SHA256 (truncated 8 chars) | Deterministic, keyed, irreversible without the vault key |
| Local vault | SQLite via `sqlite3` stdlib | Zero deps, embedded, works offline |
| Hosted vault | PostgreSQL + AWS KMS | Industry standard, auditable, envelope encryption |
| Python HTTP | `httpx` (async-first) | Async support, connection pooling, clean API |
| TypeScript HTTP | native `fetch` + OpenAI SDK wrapping | Minimal deps |
| Proxy style | In-process SDK first, sidecar later | Simpler DX for Phase 0; sidecar in Phase 1 for polyglot support |
| Packaging | `pyproject.toml` (Poetry) + `package.json` | Standard, works with PyPI + npm |

---

## 4. Python SDK Interface (Phase 0 target)

```python
# Drop-in for OpenAI
from pii_vault import SafeOpenAI

client = SafeOpenAI(
    api_key="sk-...",
    vault_key="vault-key-...",   # key for HMAC + encryption
    vault_path="./vault.db",     # SQLite path (or URL for hosted)
    entities=["PERSON", "EMAIL", "PHONE"],  # optional: limit detection scope
)

# Exact same interface as openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarize the case for John Smith, john@acme.com"}]
)
# "John Smith" was sent as "PERSON_a3f2b1c4", restored in response

# Drop-in for Anthropic
from pii_vault import SafeAnthropic

client = SafeAnthropic(api_key="...", vault_key="...")
# Same pattern

# Low-level API if needed
from pii_vault import Vault, Detector, Tokenizer

vault = Vault(path="./vault.db", key="vault-key-...")
detector = Detector(entities=["PERSON", "EMAIL"])
tokenizer = Tokenizer(vault=vault)

text = "Contact Alice at alice@corp.com"
tokenized, spans = tokenizer.tokenize(text)
# "Contact PERSON_a3f2b1c4 at EMAIL_9d1e2f3a"

restored = tokenizer.dehydrate(tokenized)
# "Contact Alice at alice@corp.com"
```

---

## 5. TypeScript SDK Interface (Phase 0 target)

```typescript
import { SafeOpenAI } from 'pii-vault';
import OpenAI from 'openai';

const client = new SafeOpenAI({
  openai: new OpenAI({ apiKey: '...' }),
  vaultKey: 'vault-key-...',
  vaultPath: './vault.db',
  entities: ['PERSON', 'EMAIL', 'PHONE'],
});

// Exact same interface as OpenAI client
const response = await client.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Summarize the case for John Smith, john@acme.com' }],
});
```

---

## 6. Repo Structure (pii-vault public)

```
pii-vault/
├── packages/
│   ├── python/
│   │   ├── pii_vault/
│   │   │   ├── __init__.py          # SafeOpenAI, SafeAnthropic, Vault, Detector, Tokenizer
│   │   │   ├── detector.py          # spaCy NER + rule patterns
│   │   │   ├── tokenizer.py         # HMAC tokenization + dehydration
│   │   │   ├── vault.py             # SQLite vault (local) + API vault (hosted)
│   │   │   ├── providers/
│   │   │   │   ├── openai.py        # SafeOpenAI wrapper
│   │   │   │   └── anthropic.py     # SafeAnthropic wrapper
│   │   │   └── models.py            # Pydantic models (Entity, Token, VaultEntry)
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── typescript/
│       ├── src/
│       │   ├── index.ts
│       │   ├── detector.ts
│       │   ├── tokenizer.ts
│       │   ├── vault.ts
│       │   └── providers/
│       │       ├── openai.ts
│       │       └── anthropic.ts
│       ├── tests/
│       ├── package.json
│       └── tsconfig.json
├── proxy/                           # Phase 1 — HTTP sidecar proxy
│   ├── Dockerfile
│   └── src/
├── README.md
├── LICENSE
└── .gitignore
```

---

## 7. Build Sequence (Phase 0 — 4 weeks)

### Week 1 — Python core
- [ ] `packages/python/` scaffolded with `pyproject.toml`
- [ ] `Detector` class — spaCy NER + rule patterns for 9 entity types
- [ ] `Vault` class — SQLite backend, CRUD, `delete_subject()`
- [ ] `Tokenizer` class — HMAC-SHA256 tokenization + dehydration
- [ ] Unit tests for all three (pytest, 90%+ coverage)
- [ ] `make test` passes

### Week 2 — Provider wrappers (Python)
- [ ] `SafeOpenAI` — wraps `openai.OpenAI`, intercepts `chat.completions.create`
- [ ] `SafeAnthropic` — wraps `anthropic.Anthropic`, intercepts `messages.create`
- [ ] Streaming support (SSE) for both providers
- [ ] Integration tests (mocked provider responses)
- [ ] `pip install pii-vault` works locally

### Week 3 — TypeScript SDK
- [ ] Mirror Python interface in TypeScript
- [ ] SQLite via `better-sqlite3`
- [ ] `SafeOpenAI` TypeScript wrapper
- [ ] `SafeAnthropic` TypeScript wrapper
- [ ] Unit + integration tests (jest)
- [ ] `npm install pii-vault` works locally

### Week 4 — Polish + publish
- [ ] README with copy-paste quickstart (< 5 minutes to first tokenized call)
- [ ] `CONTRIBUTING.md`
- [ ] GitHub Actions CI (test on push, Python 3.10/3.11/3.12, Node 18/20)
- [ ] Publish to PyPI (`pii-vault`)
- [ ] Publish to npm (`pii-vault`)
- [ ] Blog post draft: "How to stop sending PII to OpenAI in 5 minutes"
- [ ] HN Show HN post

---

## 8. Key Design Constraints

1. **Zero required external services in Phase 0.** Everything runs locally. Vault is SQLite. No cloud account needed.
2. **Drop-in, not wrap-in.** `SafeOpenAI` must be a true drop-in — same method signatures, same return types. If the user's code uses `client.chat.completions.create(...)`, it stays exactly that.
3. **Streaming must work.** Most production apps use streaming. If we break streaming, adoption fails.
4. **spaCy model must be bundled or auto-downloaded on first use.** No manual setup.
5. **Vault key is mandatory.** No insecure defaults. If no vault key is provided, raise a clear error with a setup guide link.
6. **Token determinism is per-vault.** Same value in vault A → different token than vault B. Prevents cross-customer correlation.

---

## 9. What Phase 0 does NOT include

- HTTP sidecar proxy (Phase 1)
- Multi-provider routing (Phase 1)
- DSAR automation (Phase 2)
- Hosted vault / cloud API (Phase 1 cloud)
- Dashboard (Phase 1 cloud)
- Format-preserving encryption (Phase 2)
- Vector store integration (Phase 2)
- SOC 2 / compliance (Phase 3)

---

## 10. Success criteria for Phase 0

- `pip install pii-vault` + 5 lines of code → first tokenized OpenAI call
- All tests passing, CI green
- Published to PyPI + npm
- README gets 10+ GitHub issues / questions (signal of real interest)
- 3 design partner conversations started from the HN post

---

*Last updated: 2026-05-15*
