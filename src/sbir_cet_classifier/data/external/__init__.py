"""External API clients for solicitation enrichment."""

from sbir_cet_classifier.data.external.grants_gov import GrantsGovClient
from sbir_cet_classifier.data.external.nih import NIHClient
from sbir_cet_classifier.data.external.nsf import NSFClient

__all__ = ["GrantsGovClient", "NIHClient", "NSFClient"]
