import hashlib
import hmac
import re
from typing import Optional

from .models import Entity
from .vault import Vault

# Matches complete tokens: PERSON_a3f2b1c4 or TOK_a3f2b1c4
_TOKEN_RE = re.compile(r"\b([A-Z][A-Z_]*_[0-9a-f]{8})\b")

# Matches text that could be the *start* of a token (not yet complete)
_PARTIAL_TOKEN_RE = re.compile(r"[A-Z][A-Z_]*(?:_[0-9a-f]{0,7})?$")


class Tokenizer:
    """
    Replaces PII spans with deterministic tokens and restores them.

    mode="typed"  → PERSON_a3f2b1c4   (entity type visible — default)
    mode="opaque" → TOK_a3f2b1c4      (fully opaque — for high-security contexts)
    """

    def __init__(self, vault: Vault, key: str, mode: str = "typed"):
        assert mode in ("typed", "opaque"), "mode must be 'typed' or 'opaque'"
        self._vault = vault
        self._key   = key.encode() if isinstance(key, str) else key
        self._mode  = mode

    # ── Core operations ───────────────────────────────────────────────────

    def tokenize(
        self,
        text:       str,
        entities:   list[Entity],
        subject_id: Optional[str] = None,
    ) -> str:
        if not entities:
            return text

        # Replace from right to left so indices stay valid
        sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)
        result = text
        for entity in sorted_entities:
            value = text[entity.start:entity.end]
            token = self._make_token(value, entity.entity_type)
            self._vault.store(token, value, entity.entity_type, subject_id)
            result = result[:entity.start] + token + result[entity.end:]

        return result

    def dehydrate(self, text: str) -> str:
        """Restore all tokens in text back to their original values."""
        def replace(match: re.Match) -> str:
            value = self._vault.retrieve(match.group(1))
            return value if value is not None else match.group(1)

        return _TOKEN_RE.sub(replace, text)

    # ── Message-list helpers (OpenAI / Anthropic format) ──────────────────

    def tokenize_messages(
        self,
        messages:   list[dict],
        detector,
        subject_id: Optional[str] = None,
    ) -> list[dict]:
        result = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                entities = detector.analyze(content)
                tokenized = self.tokenize(content, entities, subject_id)
                result.append({**msg, "content": tokenized})
            else:
                result.append(msg)
        return result

    def dehydrate_messages(self, messages: list[dict]) -> list[dict]:
        result = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                result.append({**msg, "content": self.dehydrate(content)})
            else:
                result.append(msg)
        return result

    # ── Streaming helpers ─────────────────────────────────────────────────

    def split_stream_safe(self, text: str) -> tuple[str, str]:
        """
        Split buffered stream text into:
          - safe:      text that cannot be the start of an incomplete token
          - remainder: text to keep buffered (potential partial token)
        """
        match = _PARTIAL_TOKEN_RE.search(text)
        if match:
            return text[:match.start()], text[match.start():]
        return text, ""

    # ── Internal ──────────────────────────────────────────────────────────

    def _make_token(self, value: str, entity_type: str) -> str:
        sig    = hmac.new(self._key, value.encode("utf-8"), hashlib.sha256).hexdigest()[:8]
        prefix = entity_type if self._mode == "typed" else "TOK"
        return f"{prefix}_{sig}"
