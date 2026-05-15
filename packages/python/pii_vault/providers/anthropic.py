from typing import Iterator, Optional

from ..detector import Detector
from ..tokenizer import Tokenizer
from ..vault import Vault


class SafeAnthropic:
    """
    Drop-in replacement for anthropic.Anthropic.

    Usage::

        from pii_vault import SafeAnthropic

        client = SafeAnthropic(api_key="sk-ant-...", vault_key="my-secret")
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Summarise case for Jane Doe, jane@corp.com"}],
        )
    """

    def __init__(
        self,
        api_key:     str,
        vault_key:   str,
        vault_path:  str = ":memory:",
        entities:    Optional[list[str]] = None,
        llm_fallback: bool = False,
        token_mode:  str = "typed",
        **anthropic_kwargs,
    ):
        from anthropic import Anthropic

        self._raw   = Anthropic(api_key=api_key, **anthropic_kwargs)
        vault       = Vault(path=vault_path)
        detector    = Detector(
            entities=entities,
            llm_fallback=llm_fallback,
            openai_api_key=None,
        )
        tokenizer   = Tokenizer(vault=vault, key=vault_key, mode=token_mode)

        self.messages = _MessagesNamespace(self._raw, detector, tokenizer)

    def __getattr__(self, name: str):
        return getattr(self._raw, name)


class _MessagesNamespace:
    def __init__(self, client, detector: Detector, tokenizer: Tokenizer):
        self._client    = client
        self._detector  = detector
        self._tokenizer = tokenizer

    def create(self, *, messages: list[dict], subject_id: Optional[str] = None, **kwargs):
        tokenized = self._tokenizer.tokenize_messages(
            messages, self._detector, subject_id=subject_id
        )

        if kwargs.get("stream"):
            return _AnthropicStream(
                self._client.messages.create(messages=tokenized, **kwargs),
                self._tokenizer,
            )

        response = self._client.messages.create(messages=tokenized, **kwargs)

        # Anthropic response: response.content is a list of ContentBlock
        for block in response.content:
            if hasattr(block, "text") and block.text:
                block.text = self._tokenizer.dehydrate(block.text)

        return response


class _AnthropicStream:
    """
    Wraps an Anthropic streaming response and dehydrates text deltas.
    """

    def __init__(self, stream, tokenizer: Tokenizer):
        self._stream    = stream
        self._tokenizer = tokenizer
        self._buffer    = ""

    def __iter__(self) -> Iterator:
        for event in self._stream:
            # Anthropic streams text_delta events
            if hasattr(event, "delta") and hasattr(event.delta, "text"):
                self._buffer += event.delta.text
                safe, self._buffer = self._tokenizer.split_stream_safe(self._buffer)
                if safe:
                    event.delta.text = self._tokenizer.dehydrate(safe)
                    yield event
            else:
                yield event

        if self._buffer:
            import copy
            final = copy.deepcopy(event)  # type: ignore[possibly-unbound]
            final.delta.text = self._tokenizer.dehydrate(self._buffer)
            self._buffer = ""
            yield final

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if hasattr(self._stream, "__exit__"):
            self._stream.__exit__(*args)
