from typing import Iterator, Optional

from ..detector import Detector
from ..tokenizer import Tokenizer
from ..vault import LocalVault


class SafeAnthropic:
    """
    Drop-in replacement for anthropic.Anthropic.

    Local vault (default)::

        client = SafeAnthropic(api_key="sk-ant-...", vault_key="my-secret")

    Hosted vault (Mawlaia cloud)::

        client = SafeAnthropic(
            api_key="sk-ant-...",
            vault_key="my-hmac-secret",
            mawlaia_api_key="mwl_live_...",
        )
    """

    def __init__(
        self,
        api_key:          str,
        vault_key:        str = "",
        vault_path:       str = ":memory:",
        mawlaia_api_key:  Optional[str] = None,
        mawlaia_vault_url: str = "https://api.mawlaia.com",
        vault=None,
        entities:         Optional[list[str]] = None,
        llm_fallback:     bool = False,
        token_mode:       str = "typed",
        **anthropic_kwargs,
    ):
        from anthropic import Anthropic

        self._raw = Anthropic(api_key=api_key, **anthropic_kwargs)

        if vault is not None:
            _vault = vault
        elif mawlaia_api_key:
            from ..hosted_vault import HostedVault
            _vault = HostedVault(api_key=mawlaia_api_key, vault_url=mawlaia_vault_url)
        else:
            _vault = LocalVault(path=vault_path)

        detector  = Detector(entities=entities, llm_fallback=llm_fallback, openai_api_key=None)
        tokenizer = Tokenizer(vault=_vault, key=vault_key or "default", mode=token_mode)

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
