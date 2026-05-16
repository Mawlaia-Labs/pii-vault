from typing import Optional

import httpx


class HostedVault:
    """
    Cloud-backed vault — stores token↔value mappings in the Mawlaia hosted API.

    Usage::

        from pii_vault import SafeOpenAI, HostedVault

        client = SafeOpenAI(
            api_key="sk-...",
            vault_key="my-hmac-secret",
            vault=HostedVault(api_key="mwl_live_..."),
        )

    Values are encrypted at rest using per-user Fernet keys on the server.
    In transit they travel over HTTPS only.
    """

    DEFAULT_URL = "https://api.mawlaia.com"

    def __init__(self, api_key: str, vault_url: str = DEFAULT_URL, timeout: float = 10.0):
        self._base = vault_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._client = httpx.Client(headers=self._headers, timeout=timeout)
        self._pending: list[dict] = []  # batched before flush()

    # ── Batch store (called by Tokenizer) ─────────────────────────────────────

    def store(
        self,
        token:       str,
        value:       str,
        entity_type: str,
        subject_id:  Optional[str] = None,
    ) -> None:
        """Queue an entry for batch upload. Call flush() after tokenize() completes."""
        self._pending.append({
            "token":       token,
            "value":       value,
            "entity_type": entity_type,
            "subject_id":  subject_id,
        })

    def flush(self) -> int:
        """Upload all pending entries to the hosted vault in one API call."""
        if not self._pending:
            return 0
        resp = self._client.post(
            f"{self._base}/v1/pii-vault/tokens",
            json={"entries": self._pending},
        )
        resp.raise_for_status()
        self._pending.clear()
        return resp.json().get("stored", 0)

    # ── Retrieve (called by Tokenizer) ────────────────────────────────────────

    def retrieve(self, token: str) -> Optional[str]:
        values = self.batch_retrieve([token])
        return values.get(token)

    def batch_retrieve(self, tokens: list[str]) -> dict[str, Optional[str]]:
        if not tokens:
            return {}
        resp = self._client.post(
            f"{self._base}/v1/pii-vault/tokens/lookup",
            json={"tokens": tokens},
        )
        resp.raise_for_status()
        return resp.json().get("values", {})

    # ── DSAR ──────────────────────────────────────────────────────────────────

    def delete_subject(self, subject_id: str) -> int:
        resp = self._client.delete(f"{self._base}/v1/pii-vault/subjects/{subject_id}")
        resp.raise_for_status()
        return resp.json().get("deleted_count", 0)

    def list_subject(self, subject_id: str) -> list[dict]:
        resp = self._client.get(f"{self._base}/v1/pii-vault/subjects/{subject_id}")
        resp.raise_for_status()
        return resp.json().get("tokens", [])

    def count(self) -> int:
        resp = self._client.get(f"{self._base}/v1/pii-vault/stats")
        resp.raise_for_status()
        return resp.json().get("total_entries", 0)

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass
