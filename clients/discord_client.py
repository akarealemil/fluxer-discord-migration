"""Simple Discord HTTP client for reading user data.

This uses the REST API directly with user tokens.
"""

from __future__ import annotations

from typing import Any

import aiohttp


class DiscordHTTPClient:
    """Simple Discord HTTP client using user token."""

    BASE_URL = "https://discord.com/api/v10"

    def __init__(self, token: str):
        self.token = token
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": self.token,  # User token (no "Bot" prefix)
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
            )
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def request(self, method: str, endpoint: str) -> Any:
        """Make a request to Discord API."""
        session = await self._ensure_session()
        url = f"{self.BASE_URL}{endpoint}"

        async with session.request(method, url) as resp:
            if resp.status == 401:
                raise ValueError("Discord token is invalid or expired")
            if resp.status == 403:
                raise ValueError(
                    "Discord token doesn't have permission for this action"
                )
            if resp.status >= 400:
                raise ValueError(f"Discord API error: {resp.status}")

            return await resp.json()

    async def get_current_user(self) -> dict[str, Any]:
        """GET /users/@me - get current user"""
        user_data = await self.request("GET", "/users/@me")

        try:
            profile_data = await self.request(
                "GET", f"/users/{user_data['id']}/profile"
            )
            if "user_profile" in profile_data:
                user_data.update(profile_data["user_profile"])
        except Exception:
            pass

        return user_data

    async def get_guilds(self) -> list[dict[str, Any]]:
        """GET /users/@me/guilds with member counts"""
        return await self.request("GET", "/users/@me/guilds?with_counts=true")

    async def get_guild(self, guild_id: str) -> dict[str, Any]:
        """GET /guilds/{guild_id}"""
        return await self.request("GET", f"/guilds/{guild_id}")

    async def get_guild_channels(self, guild_id: str) -> list[dict[str, Any]]:
        """GET /guilds/{guild_id}/channels"""
        return await self.request("GET", f"/guilds/{guild_id}/channels")

    async def get_guild_roles(self, guild_id: str) -> list[dict[str, Any]]:
        """GET /guilds/{guild_id}/roles"""
        return await self.request("GET", f"/guilds/{guild_id}/roles")

    async def get_guild_emojis(self, guild_id: str) -> list[dict[str, Any]]:
        """GET /guilds/{guild_id}/emojis"""
        return await self.request("GET", f"/guilds/{guild_id}/emojis")

    async def get_guild_stickers(self, guild_id: str) -> list[dict[str, Any]]:
        """GET /guilds/{guild_id}/stickers"""
        return await self.request("GET", f"/guilds/{guild_id}/stickers")
