from typing import Iterator, Optional

from ..detector import Detector
from ..tokenizer import Tokenizer
from ..vault import Vault


class SafeOpenAI:
    """
    Drop-in replacement for openai.OpenAI.

    Usage::

        from pii_vault import SafeOpenAI

        client = SafeOpenAI(api_key="sk-...", vault_key="my-secret")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Summarise case for John Smith, john@acme.com"}],
        )
        # PII was tokenised before leaving the process; response is already restored.
    """

    def __init__(
        self,
        api_key:     str,
        vault_key:   str,
        vault_path:  str = ":memory:",
        entities:    Optional[list[str]] = None,
        llm_fallback: bool = False,
        token_mode:  str = "typed",
        **openai_kwargs,
    ):
        from openai import OpenAI

        self._raw    = OpenAI(api_key=api_key, **openai_kwargs)
        vault        = Vault(path=vault_path)
        detector     = Detector(
            entities=entities,
            llm_fallback=llm_fallback,
            openai_api_key=api_key if llm_fallback else None,
        )
        tokenizer    = Tokenizer(vault=vault, key=vault_key, mode=token_mode)

        self.chat    = _ChatNamespace(self._raw, detector, tokenizer)
        self.models  = self._raw.models

    def __getattr__(self, name: str):
        return getattr(self._raw, name)


class _ChatNamespace:
    def __init__(self, client, detector: Detector, tokenizer: Tokenizer):
        self.completions = _Completions(client, detector, tokenizer)


class _Completions:
    def __init__(self, client, detector: Detector, tokenizer: Tokenizer):
        self._client    = client
        self._detector  = detector
        self._tokenizer = tokenizer

    def create(self, *, messages: list[dict], subject_id: Optional[str] = None, **kwargs):
        tokenized = self._tokenizer.tokenize_messages(
            messages, self._detector, subject_id=subject_id
        )

        if kwargs.get("stream"):
            return _StreamingResponse(
                self._client.chat.completions.create(messages=tokenized, **kwargs),
                self._tokenizer,
            )

        response = self._client.chat.completions.create(messages=tokenized, **kwargs)

        for choice in response.choices:
            if choice.message and choice.message.content:
                choice.message.content = self._tokenizer.dehydrate(choice.message.content)

        return response


class _StreamingResponse:
    """
    Wraps a streaming OpenAI response.
    Buffers output to avoid yielding partial tokens, dehydrates complete text.
    """

    def __init__(self, stream, tokenizer: Tokenizer):
        self._stream    = stream
        self._tokenizer = tokenizer
        self._buffer    = ""

    def __iter__(self) -> Iterator:
        for chunk in self._stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                self._buffer += delta.content
                safe, self._buffer = self._tokenizer.split_stream_safe(self._buffer)
                if safe:
                    chunk.choices[0].delta.content = self._tokenizer.dehydrate(safe)
                    yield chunk
            else:
                yield chunk

        # Flush remaining buffer in a final synthetic yield
        if self._buffer:
            # Build a minimal chunk-like object to carry the flushed content
            import copy
            final = copy.deepcopy(chunk)  # type: ignore[possibly-unbound]
            final.choices[0].delta.content = self._tokenizer.dehydrate(self._buffer)
            self._buffer = ""
            yield final

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if hasattr(self._stream, "__exit__"):
            self._stream.__exit__(*args)
