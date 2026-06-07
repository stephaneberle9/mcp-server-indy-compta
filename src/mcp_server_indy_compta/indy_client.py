import logging
import os

from fastmcp_creds import (
    CredentialsProviderChain,
    CustomHeaderCredentialsProvider,
    EnvironmentCredentialsProvider,
)
from fastmcp_creds.keyring import KeyringCredentialsProvider
from indy_compta import BrowserAuth, IndyClient, TokenAuth
from indy_compta.auth.browser import Browser

logger = logging.getLogger(__name__)


class IndyClientProvider:
    INDY_KEYRING_SERVICE = "indy-compta"
    INDY_TOKEN_HEADER_NAME = "Indy-Token"
    INDY_TOKEN_ENV_VAR_NAME = "INDY_TOKEN"
    INDY_BROWSER_ENV_VAR_NAME = "INDY_BROWSER"

    # User-facing values accepted in INDY_BROWSER, mapped to the library's
    # Playwright channels. The browser-login flow drives this browser using
    # the user's existing profile, so it must be installed.
    _BROWSER_ALIASES = {
        "chrome": Browser.CHROME,
        "google-chrome": Browser.CHROME,
        "edge": Browser.EDGE,
        "msedge": Browser.EDGE,
        "microsoft-edge": Browser.EDGE,
        "chromium": Browser.CHROMIUM,
    }
    _DEFAULT_BROWSER = Browser.CHROME

    def __init__(self):
        self._client: IndyClient | None = None
        self._credentials = CredentialsProviderChain(
            [
                # 1. OS keyring  (keyring set indy-compta token <jwt>)
                KeyringCredentialsProvider.for_token(self.INDY_KEYRING_SERVICE),
                # 2. Custom MCP client header
                CustomHeaderCredentialsProvider.for_token(self.INDY_TOKEN_HEADER_NAME),
                # 3. Environment variable
                EnvironmentCredentialsProvider.for_token(self.INDY_TOKEN_ENV_VAR_NAME),
            ]
        )

    @classmethod
    def _resolve_browser(cls) -> Browser:
        """Pick the Playwright browser channel for :class:`BrowserAuth`.

        Controlled by the ``INDY_BROWSER`` environment variable, accepting
        ``chrome``, ``edge``, or ``chromium`` (case-insensitive; aliases such
        as ``msedge`` are also accepted). Defaults to Chrome when unset. An
        unrecognized value logs a warning and falls back to the default rather
        than failing the server.
        """
        raw = os.getenv(cls.INDY_BROWSER_ENV_VAR_NAME, "").strip()
        if not raw:
            return cls._DEFAULT_BROWSER
        browser = cls._BROWSER_ALIASES.get(raw.lower())
        if browser is None:
            logger.warning(
                "Ignoring unrecognized %s=%r; expected one of chrome, edge, chromium. "
                "Falling back to %s.",
                cls.INDY_BROWSER_ENV_VAR_NAME,
                raw,
                cls._DEFAULT_BROWSER,
            )
            return cls._DEFAULT_BROWSER
        return browser

    def _build(self) -> IndyClient:
        token, _ = self._credentials.get_credentials()
        if token:
            logger.debug("Creating IndyClient with TokenAuth from credentials chain")
            return IndyClient(auth=TokenAuth(token))

        # No token from chain — fall back to BrowserAuth
        # (reads INDY_TOKEN_CACHE_PATH env var, cached JWT, then interactive browser login)
        browser = self._resolve_browser()
        logger.debug("Creating IndyClient with BrowserAuth (browser=%s)", browser)
        return IndyClient(auth=BrowserAuth(browser=browser))

    def get_client(self) -> IndyClient:
        """Return the singleton IndyClient, creating it on first call.

        Token resolution order:
        1. OS keyring (service ``indy-compta``).
        2. ``Indy-Token`` MCP client header (HTTP transport only).
        3. ``INDY_TOKEN`` environment variable.
        4. BrowserAuth fallback: cached HS512 JWT from
           ``~/.cache/indy-compta/token.json``
           (or ``INDY_TOKEN_CACHE_PATH`` if set), then interactive browser login.
           The login browser is selected by ``INDY_BROWSER`` (``chrome`` by
           default; ``edge`` or ``chromium`` also accepted).

        On HTTP 401 the browser is reopened to acquire a fresh token.
        """
        if self._client is None:
            self._client = self._build()
        return self._client
