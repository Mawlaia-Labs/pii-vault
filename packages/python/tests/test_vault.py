import pytest
from pii_vault.vault import Vault


@pytest.fixture
def vault():
    return Vault(path=":memory:")


def test_store_and_retrieve(vault):
    vault.store("PERSON_abc12345", "John Smith", "PERSON")
    assert vault.retrieve("PERSON_abc12345") == "John Smith"


def test_retrieve_missing_returns_none(vault):
    assert vault.retrieve("PERSON_unknown0") is None


def test_store_is_idempotent(vault):
    vault.store("EMAIL_abc12345", "john@acme.com", "EMAIL")
    vault.store("EMAIL_abc12345", "other@value.com", "EMAIL")  # should not overwrite
    assert vault.retrieve("EMAIL_abc12345") == "john@acme.com"


def test_delete_subject(vault):
    vault.store("PERSON_abc12345", "Alice", "PERSON", subject_id="user-1")
    vault.store("EMAIL_def67890", "alice@corp.com", "EMAIL", subject_id="user-1")
    vault.store("PERSON_xyz99999", "Bob", "PERSON", subject_id="user-2")

    deleted = vault.delete_subject("user-1")
    assert deleted == 2
    assert vault.retrieve("PERSON_abc12345") is None
    assert vault.retrieve("EMAIL_def67890") is None
    assert vault.retrieve("PERSON_xyz99999") == "Bob"  # untouched


def test_list_subject(vault):
    vault.store("PERSON_abc12345", "Alice", "PERSON", subject_id="user-1")
    vault.store("EMAIL_def67890", "alice@corp.com", "EMAIL", subject_id="user-1")

    entries = vault.list_subject("user-1")
    assert len(entries) == 2
    tokens = {e["token"] for e in entries}
    assert "PERSON_abc12345" in tokens
    assert "EMAIL_def67890" in tokens


def test_count(vault):
    assert vault.count() == 0
    vault.store("PERSON_abc12345", "Alice", "PERSON")
    vault.store("EMAIL_def67890", "alice@corp.com", "EMAIL")
    assert vault.count() == 2
