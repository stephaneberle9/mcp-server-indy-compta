"""Tests for browser selection in IndyClientProvider."""

import logging

import pytest
from indy_compta.auth.browser import Browser

from mcp_server_indy_compta.indy_client import IndyClientProvider

ENV_VAR = IndyClientProvider.INDY_BROWSER_ENV_VAR_NAME


def test_defaults_to_chrome_when_unset(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert IndyClientProvider._resolve_browser() is Browser.CHROME


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("chrome", Browser.CHROME),
        ("google-chrome", Browser.CHROME),
        ("edge", Browser.EDGE),
        ("msedge", Browser.EDGE),
        ("microsoft-edge", Browser.EDGE),
        ("chromium", Browser.CHROMIUM),
    ],
)
def test_known_values_map_to_channel(monkeypatch, value, expected):
    monkeypatch.setenv(ENV_VAR, value)
    assert IndyClientProvider._resolve_browser() is expected


@pytest.mark.parametrize("value", ["Edge", "  CHROME  ", "ChRoMiUm"])
def test_values_are_case_insensitive_and_trimmed(monkeypatch, value):
    monkeypatch.setenv(ENV_VAR, value)
    # Each maps to its channel regardless of case/whitespace.
    assert IndyClientProvider._resolve_browser() in (
        Browser.EDGE,
        Browser.CHROME,
        Browser.CHROMIUM,
    )


def test_unknown_value_falls_back_to_chrome_with_warning(monkeypatch, caplog):
    monkeypatch.setenv(ENV_VAR, "safari")
    with caplog.at_level(logging.WARNING):
        assert IndyClientProvider._resolve_browser() is Browser.CHROME
    assert ENV_VAR in caplog.text
    assert "safari" in caplog.text
