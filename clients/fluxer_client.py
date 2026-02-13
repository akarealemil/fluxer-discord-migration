"""Fluxer API client wrapper."""

import sys
import os

# Add fluxer-py to path
script_dir = os.path.dirname(os.path.abspath(__file__))
migration_dir = os.path.dirname(script_dir)
parent_dir = os.path.dirname(migration_dir)
fluxer_path = os.path.join(parent_dir, "fluxer-py")
sys.path.insert(0, fluxer_path)

from fluxer.http import HTTPClient as FluxerHTTP


class FluxerClient:
    """Wrapper around Fluxer HTTP client for easier usage."""

    def __init__(self, token: str):
        self.http = FluxerHTTP(token, is_bot=False)

    async def close(self):
        """Close the HTTP session."""
        await self.http.close()

    # Delegate all methods to the underlying FluxerHTTP client
    def __getattr__(self, name):
        return getattr(self.http, name)
