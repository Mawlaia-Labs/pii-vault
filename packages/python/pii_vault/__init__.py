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

from .vault         import LocalVault, Vault
from .hosted_vault  import HostedVault
from .detector      import Detector
from .tokenizer     import Tokenizer
from .providers     import SafeOpenAI, SafeAnthropic

__version__ = "0.3.0"
__all__ = ["LocalVault", "Vault", "HostedVault", "Detector", "Tokenizer", "SafeOpenAI", "SafeAnthropic"]
