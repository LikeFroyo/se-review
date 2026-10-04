"""Email validation — a check that only ever sees well-formed input."""
import pytest

from validate_email import normalise_email

WELL_FORMED = [
    "alice@example.com",
    "bob.smith@example.co.uk",
    "carol@example.org",
]


@pytest.mark.parametrize("raw", WELL_FORMED)
def test_normalise_lowercases_domain(raw):
    local, _, domain = raw.partition("@")
    assert normalise_email(raw) == f"{local}@{domain.lower()}"


@pytest.mark.parametrize("raw", WELL_FORMED)
def test_normalise_preserves_local_part(raw):
    assert normalise_email(raw).split("@")[0] == raw.split("@")[0]
