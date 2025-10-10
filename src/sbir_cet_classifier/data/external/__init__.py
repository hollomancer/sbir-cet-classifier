"""External API clients for solicitation enrichment."""

from sbir_cet_classifier.data.external.grants_gov import GrantsGovClient
from sbir_cet_classifier.data.external.nih import NIHClient

__all__ = ["GrantsGovClient", "NIHClient"]
