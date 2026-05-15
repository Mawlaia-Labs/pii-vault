# PII Vault — Strategy & Development Plan

*Opportunity #2 from infrastructure_opportunities.md*
*"The Resend of data privacy for AI pipelines"*

---

## 1. Market Opportunity

### Problem
Every AI feature shipped today silently pushes customer data — names, addresses, medical notes, financial transactions, chat logs — into model provider APIs. Prompts are logged, retained, sometimes used for training, replicated across vector stores. Engineering ships; legal finds out later.

### Market size
- Every company shipping AI to end-users is a potential customer. That's tens of thousands of startups today, scaling to hundreds of thousands as AI adoption accelerates.
- Regulated verticals (healthtech, fintech, legaltech, insurtech, HR tech) are the immediate TAM — highest willingness to pay, fastest procurement.
- Realistic SOM at 3 years: 500–2000 paying companies × €500–5000/month = €3M–120M ARR.

### Forcing functions (all active now)
- **EU AI Act** — phased enforcement 2025–2027, Article 10 data governance obligations
- **GDPR enforcement** — DPA fines increasingly AI-specific (Italy blocked ChatGPT, Spain/France investigations)
- **ISO 42001** — AI management system standard, data handling required for certification
- **Cyber insurance** — insurers now asking "where does your AI send data?"
- **US state AI laws** — Colorado, Texas, Illinois, California all active or pending
- **HIPAA** — healthcare AI features need BAA with every data processor

### Buyer profile
- **Primary:** Head of Engineering or CTO at an AI-shipping startup (Series A–C)
- **Secondary:** CISO, Head of Security (SOC 2 audit triggers the conversation)
- **Tertiary:** DPO / Data Protection Officer (GDPR review)
- **Budget:** €500–5000/month self-serve; €20K–100K/year enterprise

---

## 2. Competition Landscape

| Player | Positioning | Gap |
|---|---|---|
| **Skyflow** | Enterprise vault, data privacy platform | $100K+ contracts, not developer-first, no AI-specific proxy |
| **Piiano** | Developer-friendly vault API | Small team, limited ecosystem, no multi-provider AI proxy |
| **Evervault** | Encryption-as-a-service | Narrower scope, not AI pipeline focused |
| **OpenAI ZDR / Anthropic private** | Zero data retention on single provider | Only one provider, no tokenization, no audit trail, no cross-provider routing |
| **AWS Macie / Azure Purview** | Data discovery and classification | Not a proxy, not developer-first, no AI pipeline integration |
| **Nightfall AI** | DLP for SaaS apps | Scan-and-alert model, not inline proxy tokenization |

### Competitive gap
No product today offers: **open-source SDK + multi-provider AI proxy + deterministic tokenization + regional vault + DSAR automation**, packaged as a single developer-first API with per-call pricing. This is the gap.

### Defensibility
- Switching cost: once a company has tokenized a year of data flows, re-tokenizing is painful
- Data accumulation: NER model improves with customer feedback
- Compliance certifications: SOC 2, HIPAA BAA, ISO 27001 become a moat for enterprise buyers
- Bundle: natural expansion into Guardrails (#7) and Eval (#5) — same proxy, same buyer

---

## 3. Customer Needs Map

### Jobs to be done
1. **"I need to send PII to OpenAI without it leaving the EU"** — regional vault + proxy
2. **"I need to prove to our DPO that customer data doesn't hit LLM logs"** — audit trail + tokenization
3. **"Our security review flagged prompt logging"** — SDK drop-in, no architecture change
4. **"We need a DSAR response in 30 days"** — automated data subject export/deletion
5. **"We're adding a healthcare AI feature and need HIPAA"** — BAA + PHI tokenization

### Integration points
- LLM calls: OpenAI SDK, Anthropic SDK, LangChain, LlamaIndex, Vercel AI SDK, raw HTTP
- Vector stores: Pinecone, Weaviate, Qdrant, pgvector (store tokenized embeddings only)
- Storage: any database — tokenized values stored, vault holds the mapping

### Must-have on day one
- TypeScript/Python SDKs with a one-line integration
- Support for OpenAI and Anthropic (covers 80% of market)
- EU and US vault regions
- Free tier: first 100K tokenizations/month free
- Audit log viewable in dashboard

---

## 4. Staged Development Plan

### Phase 0 — Open-source kernel (weeks 1–4)
**Goal:** be the canonical GitHub answer for "how to handle PII in LLM calls"

- [ ] Open-source `pii-vault` monorepo
- [ ] TypeScript SDK: `tokenize(text)` → tokens, `dehydrate(response)` → original
- [ ] Python SDK: same interface
- [ ] NER detection layer: GPT-4o-mini or spaCy hybrid for PII categories (PERSON, EMAIL, PHONE, ADDRESS, MEDICAL_ID, FINANCIAL_ID)
- [ ] Proxy wrapper for OpenAI SDK (drop-in: replace `new OpenAI()` with `new SafeOpenAI()`)
- [ ] Local vault option (SQLite) for self-hosting
- [ ] README with clear GDPR/HIPAA positioning
- [ ] Publish: GitHub, HN Show HN, dev.to post "How to stop sending PII to OpenAI"

**Success metric:** 200+ GitHub stars, 5 design partner conversations started

---

### Phase 1 — Hosted MVP (months 1–3)
**Goal:** first paying customers

- [ ] Hosted vault API (Postgres + AWS KMS envelope encryption)
- [ ] EU region (Frankfurt) + US region (us-east-1)
- [ ] Dashboard: tokenization stats, audit log, active consents
- [ ] Anthropic proxy (in addition to OpenAI)
- [ ] Free tier (100K tokenizations/month)
- [ ] Paid tier: €99/month for 1M tokenizations, unlimited vault storage
- [ ] GDPR DPA template auto-generated on signup
- [ ] Onboard 5–10 design partners from AI startup ecosystem

**Success metric:** 5 paying customers, €500–2000 MRR

---

### Phase 2 — Production-grade (months 3–6)
**Goal:** trustworthy enough for Series A/B AI startups

- [ ] Google Gemini + Cohere + Mistral proxy support
- [ ] LangChain / LlamaIndex native integration
- [ ] Vercel AI SDK integration
- [ ] Vector store tokenization (Pinecone, pgvector)
- [ ] DSAR automation: identify all tokens for a data subject, export or delete
- [ ] Format-preserving tokenization for emails, phone numbers (maintains format, not value)
- [ ] Custom PII categories (customer-defined entity types)
- [ ] SOC 2 Type I process started
- [ ] Enterprise tier: €999/month, custom residency, SLA

**Success metric:** 30–50 paying customers, €10K MRR

---

### Phase 3 — Compliance tier (months 6–12)
**Goal:** close regulated-industry deals

- [ ] SOC 2 Type II (requires 6 months observed controls from Phase 2)
- [ ] HIPAA BAA available
- [ ] AWS Marketplace listing
- [ ] Synthetic data generation (replace real PII with realistic fake data for dev/test)
- [ ] ISO 27001 process started
- [ ] Volume pricing (enterprise 10M+ tokenizations/month)
- [ ] Start bundling with Guardrails (#7): same proxy, add runtime safety layer

**Success metric:** 100–200 paying customers, €30–50K MRR, seed raise

---

### Phase 4 — Platform (months 12–24)
**Goal:** become the AI middleware platform

- [ ] AI Guardrails fully bundled (Opportunity #7)
- [ ] AI Eval integration (Opportunity #5)
- [ ] ISO 27001 complete
- [ ] HITRUST (healthcare enterprise)
- [ ] Multi-model routing intelligence (route PII-safe calls to cheapest/fastest model)
- [ ] 500+ paying customers
- [ ] Series A raise

---

## 5. Zero-to-revenue path (bootstrap)

**Month 1:** publish open-source SDK → GitHub stars → inbound design partner convos
**Month 2:** hosted MVP live → convert 3–5 design partners to €99/month
**Month 3:** 10 paying customers, €1K MRR → refine proxy, add Anthropic support
**Month 4–5:** 30 customers, €5K MRR → SOC 2 Type I started → enterprise conversations begin
**Month 6:** €10K MRR → seed-raise ready

**Infrastructure cost at €10K MRR:** ~€500–800/month (Fly.io/Render + RDS + KMS + Cloudflare)

---

## 6. Tech stack recommendation

- **Proxy:** Cloudflare Workers (edge latency) or Fly.io (multi-region, simpler ops)
- **Vault:** Postgres (RDS) + AWS KMS for envelope encryption
- **NER:** spaCy medium model + GPT-4o-mini for edge cases (hybrid)
- **Dashboard:** Next.js on Vercel
- **SDKs:** TypeScript + Python (publish to npm + PyPI)
- **Auth:** Clerk or Auth0 for dashboard, API key for SDK auth

---

*Last updated: 2026-05-15*
