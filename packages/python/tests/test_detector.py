import pytest
from pii_vault.detector import Detector


@pytest.fixture(scope="module")
def detector():
    return Detector()


def test_detects_person(detector):
    entities = detector.analyze("Contact John Smith for details.")
    types = {e.entity_type for e in entities}
    assert "PERSON" in types
    texts = {e.text for e in entities}
    assert "John Smith" in texts


def test_detects_email(detector):
    entities = detector.analyze("Send it to alice@acme.com please.")
    types = {e.entity_type for e in entities}
    assert "EMAIL" in types


def test_detects_phone(detector):
    entities = detector.analyze("Call me at +1 650 555 0199.")
    types = {e.entity_type for e in entities}
    assert "PHONE" in types


def test_empty_string(detector):
    assert detector.analyze("") == []


def test_no_pii(detector):
    entities = detector.analyze("The sky is blue and the grass is green.")
    # No personal identifiers expected
    person_entities = [e for e in entities if e.entity_type == "PERSON"]
    assert len(person_entities) == 0


def test_multiple_entities(detector):
    text     = "Alice (alice@corp.com) called Bob at +1 650 555 0199."
    entities = detector.analyze(text)
    types    = {e.entity_type for e in entities}
    assert "PERSON" in types
    assert "EMAIL"  in types
    assert "PHONE"  in types


def test_entity_spans_are_correct(detector):
    text     = "My name is John Smith."
    entities = detector.analyze(text)
    persons  = [e for e in entities if e.entity_type == "PERSON"]
    assert any(e.text == "John Smith" for e in persons)
    for e in persons:
        assert text[e.start:e.end] == e.text


def test_dedup_no_overlapping_spans(detector):
    text     = "John Smith john@smith.com"
    entities = detector.analyze(text)
    # No two entities should overlap
    for i, a in enumerate(entities):
        for b in entities[i + 1:]:
            assert not (a.start < b.end and a.end > b.start), f"Overlap: {a} / {b}"
