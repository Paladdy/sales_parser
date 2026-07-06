class EnrichmentError(Exception):
    """Base enrichment error."""


class RateLimitExceeded(EnrichmentError):
    def __init__(self, domain: str) -> None:
        self.domain = domain
        super().__init__(f"Rate limit exceeded for domain: {domain}")


class DatabaseUnavailable(EnrichmentError):
    pass
