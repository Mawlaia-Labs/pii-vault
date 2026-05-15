from pydantic import BaseModel
from typing import Optional


# Presidio uses different names — we normalise to these
ENTITY_TYPE_MAP: dict[str, str] = {
    "EMAIL_ADDRESS":    "EMAIL",
    "PHONE_NUMBER":     "PHONE",
    "LOCATION":         "ADDRESS",
    "ORGANIZATION":     "ORG",
    "DATE_TIME":        "DATE",
    "MEDICAL_LICENSE":  "MEDICAL_ID",
    "CREDIT_CARD":      "FINANCIAL_ID",
    "IBAN_CODE":        "FINANCIAL_ID",
    "US_SSN":           "FINANCIAL_ID",
    "US_BANK_NUMBER":   "FINANCIAL_ID",
}

DEFAULT_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "DATE_TIME",
    "MEDICAL_LICENSE",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "URL",
]


class Entity(BaseModel):
    text:        str
    entity_type: str    # normalised type (PERSON, EMAIL, …)
    start:       int
    end:         int
    score:       float

    @classmethod
    def from_presidio(cls, result, text: str) -> "Entity":
        normalised = ENTITY_TYPE_MAP.get(result.entity_type, result.entity_type)
        return cls(
            text=text[result.start:result.end],
            entity_type=normalised,
            start=result.start,
            end=result.end,
            score=result.score,
        )


class VaultEntry(BaseModel):
    token:       str
    value:       str
    entity_type: str
    subject_id:  Optional[str] = None
