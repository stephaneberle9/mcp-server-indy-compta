import logging

from indy_compta import BrowserAuth, IndyClient, TokenAuth
from indy_compta.auth.browser import Browser

from fastmcp_creds import CredentialsProviderChain, CustomHeaderCredentialsProvider, EnvironmentCredentialsProvider
from fastmcp_creds.keyring import KeyringCredentialsProvider

logger = logging.getLogger(__name__)


class IndyClientProvider:
    INDY_KEYRING_SERVICE = "indy-compta"
    INDY_TOKEN_HEADER_NAME = "Indy-Token"
    INDY_TOKEN_ENV_VAR_NAME = "INDY_TOKEN"

    def __init__(self):
        self._client: IndyClient | None = None
        self._credentials = CredentialsProviderChain([
            # 1. OS keyring  (keyring set indy-compta token <jwt>)
            KeyringCredentialsProvider.for_token(self.INDY_KEYRING_SERVICE),
            # 2. Custom MCP client header
            CustomHeaderCredentialsProvider.for_token(self.INDY_TOKEN_HEADER_NAME),
            # 3. Environment variable
            EnvironmentCredentialsProvider.for_token(self.INDY_TOKEN_ENV_VAR_NAME),
        ])

    def _build(self) -> IndyClient:
        token, _ = self._credentials.get_credentials()
        if token:
            logger.debug("Creating IndyClient with TokenAuth from credentials chain")
            return IndyClient(auth=TokenAuth(token))

        # No token from chain — fall back to BrowserAuth
        # (reads INDY_TOKEN_CACHE_PATH env var, cached JWT, then interactive browser login)
        logger.debug("Creating IndyClient with BrowserAuth")
        return IndyClient(auth=BrowserAuth(browser=Browser.CHROME))

    def get_client(self) -> IndyClient:
        """Return the singleton IndyClient, creating it on first call.

        Token resolution order:
        1. OS keyring (service ``indy-compta``).
        2. ``Indy-Token`` MCP client header (HTTP transport only).
        3. ``INDY_TOKEN`` environment variable.
        4. BrowserAuth fallback: cached HS512 JWT from
           ``~/.cache/indy-compta/token.json``
           (or ``INDY_TOKEN_CACHE_PATH`` if set), then interactive browser login.

        On HTTP 401 the browser is reopened to acquire a fresh token.
        """
        if self._client is None:
            self._client = self._build()
        return self._client
