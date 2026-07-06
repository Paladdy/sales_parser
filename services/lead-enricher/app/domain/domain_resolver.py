import re
from typing import Optional

FREE_EMAIL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com",
    "yandex.ru", "yandex.com", "ya.ru",
    "mail.ru", "inbox.ru", "list.ru", "bk.ru",
    "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "icloud.com", "proton.me", "protonmail.com",
    "rambler.ru",
})


class DomainResolver:
    """Resolves company domain from lead email or explicit website."""

    @staticmethod
    def is_free_email_domain(domain: str) -> bool:
        return domain.lower().strip() in FREE_EMAIL_DOMAINS

    @classmethod
    def extract_from_email(cls, email: str) -> Optional[str]:
        match = re.search(r"@([^@]+)$", email.strip())
        if not match:
            return None
        domain = match.group(1).lower()
        if cls.is_free_email_domain(domain):
            return None
        return domain

    @staticmethod
    def normalize_website(website: str) -> Optional[str]:
        if not website or not website.strip():
            return None
        url = website.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        match = re.search(r"https?://(?:www\.)?([^/\s?#]+)", url, re.IGNORECASE)
        if not match:
            return None
        return match.group(1).lower()

    @classmethod
    def resolve(cls, email: str, website: Optional[str] = None) -> Optional[str]:
        if website:
            domain = cls.normalize_website(website)
            if domain:
                return domain
        return cls.extract_from_email(email)


# Backward-compatible module-level functions
def is_free_email_domain(domain: str) -> bool:
    return DomainResolver.is_free_email_domain(domain)


def extract_domain_from_email(email: str) -> Optional[str]:
    return DomainResolver.extract_from_email(email)


def normalize_website(website: str) -> Optional[str]:
    return DomainResolver.normalize_website(website)


def resolve_domain(email: str, website: Optional[str] = None) -> Optional[str]:
    return DomainResolver.resolve(email, website)
