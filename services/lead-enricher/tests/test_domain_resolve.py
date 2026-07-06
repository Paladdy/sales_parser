import pytest

from app.domain.domain_resolver import DomainResolver


class TestFreeEmail:
    @pytest.mark.parametrize("domain", ["gmail.com", "yandex.ru", "mail.ru", "outlook.com"])
    def test_free_domains(self, domain: str):
        assert DomainResolver.is_free_email_domain(domain)

    def test_corporate_not_free(self):
        assert not DomainResolver.is_free_email_domain("logistics-de.ru")


class TestDomainResolve:
    def test_from_corporate_email(self):
        assert DomainResolver.extract_from_email("ivan@logistics-de.ru") == "logistics-de.ru"

    def test_free_email_returns_none(self):
        assert DomainResolver.extract_from_email("user@gmail.com") is None

    def test_website_takes_priority(self):
        assert DomainResolver.resolve("user@gmail.com", "https://logistics-de.ru") == "logistics-de.ru"

    def test_normalize_website_strips_www(self):
        assert DomainResolver.normalize_website("www.digital-agency.io/about") == "digital-agency.io"

    def test_no_domain_without_website_or_corporate_email(self):
        assert DomainResolver.resolve("user@gmail.com") is None

    def test_email_when_no_website(self):
        assert DomainResolver.resolve("ceo@acme-corp.com") == "acme-corp.com"

    def test_invalid_email_returns_none(self):
        assert DomainResolver.extract_from_email("not-an-email") is None

    def test_empty_website_falls_back_to_email(self):
        assert DomainResolver.resolve("ceo@corp.io", "") == "corp.io"
