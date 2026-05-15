import re
import pytest
from pii_vault.vault import Vault
from pii_vault.tokenizer import Tokenizer
from pii_vault.models import Entity


VAULT_KEY = "test-secret-key-do-not-use-in-prod"


@pytest.fixture
def vault():
    return Vault(path=":memory:")


@pytest.fixture
def tokenizer(vault):
    return Tokenizer(vault=vault, key=VAULT_KEY)


def _entity(text, entity_type, start):
    return Entity(text=text, entity_type=entity_type, start=start, end=start + len(text), score=0.9)


def test_tokenize_single_entity(tokenizer):
    text     = "Contact John Smith for details."
    entities = [_entity("John Smith", "PERSON", 8)]
    result   = tokenizer.tokenize(text, entities)

    assert "John Smith" not in result
    assert re.search(r"PERSON_[0-9a-f]{8}", result)


def test_tokenize_is_deterministic(tokenizer):
    text     = "Email alice@acme.com please."
    entities = [_entity("alice@acme.com", "EMAIL", 6)]
    r1 = tokenizer.tokenize(text, entities)
    r2 = tokenizer.tokenize(text, entities)
    assert r1 == r2


def test_dehydrate_restores_original(tokenizer):
    text     = "Contact John Smith at john@acme.com."
    entities = [
        _entity("John Smith",   "PERSON", 8),
        _entity("john@acme.com", "EMAIL",  22),
    ]
    tokenized  = tokenizer.tokenize(text, entities)
    dehydrated = tokenizer.dehydrate(tokenized)
    assert dehydrated == text


def test_tokenize_multiple_entities_no_overlap(tokenizer):
    text     = "Alice (alice@corp.com) and Bob (bob@corp.com)."
    # Alice=0, alice@corp.com=7, Bob=27, bob@corp.com=32
    entities = [
        _entity("Alice",          "PERSON",  0),
        _entity("alice@corp.com", "EMAIL",   7),
        _entity("Bob",            "PERSON", 27),
        _entity("bob@corp.com",   "EMAIL",  32),
    ]
    tokenized = tokenizer.tokenize(text, entities)
    assert "Alice" not in tokenized
    assert "alice@corp.com" not in tokenized
    assert "Bob" not in tokenized

    dehydrated = tokenizer.dehydrate(tokenized)
    assert dehydrated == text


def test_opaque_mode():
    vault     = Vault(path=":memory:")
    tokenizer = Tokenizer(vault=vault, key=VAULT_KEY, mode="opaque")
    text      = "John Smith called."
    entities  = [_entity("John Smith", "PERSON", 0)]
    result    = tokenizer.tokenize(text, entities)

    assert re.search(r"TOK_[0-9a-f]{8}", result)
    assert "PERSON" not in result


def test_tokenize_messages(tokenizer):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user",   "content": "Summarise the case for John Smith."},
    ]

    class _FakeDetector:
        def analyze(self, text):
            if "John Smith" in text:
                return [_entity("John Smith", "PERSON", text.index("John Smith"))]
            return []

    tokenized = tokenizer.tokenize_messages(messages, _FakeDetector())
    assert "John Smith" not in tokenized[1]["content"]
    assert tokenized[0]["content"] == "You are a helpful assistant."  # system prompt untouched


def test_split_stream_safe(tokenizer):
    # Mid-token: should hold back
    safe, rem = tokenizer.split_stream_safe("Hello PERSON_a3f")
    assert safe == "Hello "
    assert rem == "PERSON_a3f"

    # Complete token: nothing to hold back
    safe, rem = tokenizer.split_stream_safe("Hello PERSON_a3f2b1c4 world")
    assert rem == ""
