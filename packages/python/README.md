# pii-vault

> PII tokenization SDK and proxy for AI pipelines.

Every AI feature you ship today silently sends customer data to LLM providers. **pii-vault** sits between your application and any LLM API — tokenizing PII outbound, re-hydrating inbound — so sensitive data never leaves your infrastructure.

```python
from pii_vault import SafeOpenAI

client = SafeOpenAI(api_key="...", vault_key="...")

# PII is tokenized before leaving your server, re-hydrated in the response
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarize the case for John Smith, john@acme.com"}]
)
```

## Status

🚧 **Early development.** Star to follow progress.

## What it does

- **Deterministic tokenization** — names, emails, phones, addresses, medical IDs → opaque tokens
- **Drop-in proxy** — replace `OpenAI()` with `SafeOpenAI()`, same interface, zero architecture change
- **Multi-provider** — OpenAI, Anthropic, Google, and more
- **Regional vault** — EU and US residency, GDPR-ready from day one
- **DSAR automation** — one-call data subject export and deletion
- **Format-preserving** — emails stay email-shaped, phones stay phone-shaped

## Roadmap

- [ ] Python SDK
- [ ] TypeScript SDK
- [ ] Self-hostable vault
- [ ] Hosted service ([mawlaia.com](https://mawlaia.com))
- [ ] SOC 2 Type II
- [ ] HIPAA BAA

## License

MIT
