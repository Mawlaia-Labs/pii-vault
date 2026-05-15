"""
pii-vault — PII tokenization SDK and proxy for AI pipelines.

Quick start::

    from pii_vault import SafeOpenAI

    client = SafeOpenAI(api_key="sk-...", vault_key="my-vault-secret")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Summarise the case for John Smith, john@acme.com"}],
    )
    # John Smith and john@acme.com never left your infrastructure.
"""

from .vault     import Vault
from .detector  import Detector
from .tokenizer import Tokenizer
from .providers import SafeOpenAI, SafeAnthropic

__version__ = "0.1.0"
__all__ = ["Vault", "Detector", "Tokenizer", "SafeOpenAI", "SafeAnthropic"]
