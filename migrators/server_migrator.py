"""Server migration from Discord to Fluxer."""

from typing import Any
import asyncio
import aiohttp


class ServerMigrator:
    """Handles migration of Discord servers to Fluxer."""

    def __init__(self, discord_http, fluxer_http, logger):
        self.discord_http = discord_http
        self.fluxer_http = fluxer_http
        self.logger = logger
        # Maps Discord IDs to Fluxer IDs
        self.guild_id_map: dict[str, str] = {}
        self.role_id_map: dict[str, str] = {}
        self.category_id_map: dict[str, str] = {}
        self.channel_id_map: dict[str, str] = {}

    async def _download_image(self, url: str) -> bytes | None:
        """Download an image from URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            self.logger.log(f"Failed to download image: {e}", "ERROR")
        return None

    async def migrate_server(
        self,
        discord_guild: dict[str, Any],
        existing_fluxer_guild_id: str | None = None,
        migration_options: dict[str, bool] | None = None
    ) -> bool:
        """Migrate a single Discord server to Fluxer.

        Args:
            discord_guild: Discord guild data to migrate from
            existing_fluxer_guild_id: Optional ID of existing Fluxer guild to migrate into.
                                     If None, creates a new guild.
            migration_options: Dict specifying what to migrate. Keys:
                              - 'roles': Migrate roles (default True)
                              - 'channels': Migrate channels (default True)
                              - 'emojis': Migrate emojis (default True)
                              - 'permissions': Migrate channel permissions (default True)
        """
        if migration_options is None:
            migration_options = {
                'roles': True,
                'channels': True,
                'emojis': True,
                'permissions': True
            }
        guild_name = discord_guild["name"]
        guild_id = discord_guild["id"]

        self.logger.log(f"\n=== Migrating Server: {guild_name} ===")

        if not self.fluxer_http or not self.discord_http:
            self.logger.log("Clients not initialized", "ERROR")
            return False

        try:
            # Create or use existing guild on Fluxer
            if existing_fluxer_guild_id:
                fluxer_guild_id = existing_fluxer_guild_id
                self.logger.log(f"Using existing Fluxer guild: {fluxer_guild_id}")
                self.logger.log("(Will add roles and channels, won't delete anything)")
            else:
                self.logger.log(f"Creating new guild: {guild_name}")

                guild_icon = None
                if discord_guild.get("icon"):
                    self.logger.log("Downloading guild icon...")
                    icon_hash = discord_guild["icon"]
                    icon_ext = "gif" if icon_hash.startswith("a_") else "png"
                    icon_url = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.{icon_ext}?size=4096"
                    guild_icon = await self._download_image(icon_url)

                fluxer_guild = await self.fluxer_http.create_guild(
                    name=guild_name,
                    icon=guild_icon,
                )

                fluxer_guild_id = fluxer_guild["id"]
                self.logger.log(f"✓ Guild created with ID: {fluxer_guild_id}")

            self.guild_id_map[guild_id] = fluxer_guild_id

            # Fetch full guild data from Discord
            self.logger.log("Fetching server data from Discord...")

            # Fetch data based on what we need to migrate
            roles = []
            channels = []
            emojis = []

            if migration_options.get('roles', True):
                roles = await self.discord_http.get_guild_roles(guild_id)

            if migration_options.get('channels', True) or migration_options.get('permissions', True):
                channels = await self.discord_http.get_guild_channels(guild_id)

            if migration_options.get('emojis', True):
                emojis = await self.discord_http.get_guild_emojis(guild_id)

            # Migrate in order: roles -> channels -> emojis
            if migration_options.get('roles', True):
                await self._migrate_roles(roles, fluxer_guild_id)

            if migration_options.get('channels', True):
                await self._migrate_channels(
                    channels,
                    fluxer_guild_id,
                    migrate_permissions=migration_options.get('permissions', True)
                )

            if migration_options.get('emojis', True):
                await self._migrate_emojis(emojis, guild_id, fluxer_guild_id)

            self.logger.log(f"✓ Server '{guild_name}' migrated successfully!")
            return True

        except Exception as e:
            self.logger.log(f"Server migration failed: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

    async def _migrate_roles(self, roles: list[dict[str, Any]], fluxer_guild_id: str):
        """Migrate roles from Discord to Fluxer."""
        self.logger.log("\n--- Migrating Roles ---")

        # Skip @everyone role
        roles = [r for r in roles if r.get("name") != "@everyone"]

        # Sort by position (lowest first)
        for role in sorted(roles, key=lambda r: r.get("position", 0)):
            role_name = role["name"]
            role_id = role["id"]
            color = role.get("color", 0)
            permissions = int(role.get("permissions", 0))
            hoist = role.get("hoist", False)
            mentionable = role.get("mentionable", False)

            self.logger.log(f"Creating role: {role_name}")
            self.logger.log(f"  Color: #{color:06x}")
            self.logger.log(f"  Permissions: {permissions}")

            try:
                fluxer_role = await self.fluxer_http.create_guild_role(
                    fluxer_guild_id,
                    name=role_name,
                    permissions=permissions,
                    color=color,
                    hoist=hoist,
                    mentionable=mentionable,
                )

                fluxer_role_id = fluxer_role["id"]
                self.role_id_map[role_id] = fluxer_role_id
                self.logger.log(f"  ✓ Role created with ID: {fluxer_role_id}")

                # Add delay to avoid rate limiting (Fluxer is strict!)
                await asyncio.sleep(2.0)

            except Exception as e:
                self.logger.log(f"  Failed to create role '{role_name}': {e}", "WARN")

        self.logger.log(f"✓ Migrated {len(roles)} roles")

    async def _apply_channel_permissions(
        self,
        discord_channel: dict[str, Any],
        fluxer_channel_id: str
    ):
        """Apply permission overwrites to a Fluxer channel.

        Args:
            discord_channel: Discord channel data with permission_overwrites
            fluxer_channel_id: ID of the Fluxer channel to apply permissions to
        """
        permission_overwrites = discord_channel.get("permission_overwrites", [])

        if not permission_overwrites:
            return

        for overwrite in permission_overwrites:
            # Get the target ID and type (role or member)
            target_id = overwrite.get("id")
            target_type = overwrite.get("type")  # 0 = role, 1 = member

            # Only handle role permissions for now (member permissions would need user ID mapping)
            if target_type != 0:
                continue

            # Map Discord role ID to Fluxer role ID
            fluxer_role_id = self.role_id_map.get(target_id)
            if not fluxer_role_id:
                continue

            allow = int(overwrite.get("allow", 0))
            deny = int(overwrite.get("deny", 0))

            try:
                await self.fluxer_http.edit_channel_permissions(
                    fluxer_channel_id,
                    fluxer_role_id,
                    allow=allow,
                    deny=deny,
                    type=0  # Role
                )
                self.logger.log(f"    Applied permission overwrite for role")
            except Exception as e:
                self.logger.log(f"    Failed to apply permission: {e}", "WARN")

    async def _migrate_channels(
        self,
        channels: list[dict[str, Any]],
        fluxer_guild_id: str,
        migrate_permissions: bool = True
    ):
        """Migrate channels from Discord to Fluxer."""
        self.logger.log("\n--- Migrating Channels ---")

        # Channel types: 0=text, 2=voice, 4=category, 5=announcement, 13=stage, 15=forum
        # First pass: Create categories
        categories = [ch for ch in channels if ch.get("type") == 4]

        for category in sorted(categories, key=lambda c: c.get("position", 0)):
            category_name = category["name"]
            category_id = category["id"]
            self.logger.log(f"Creating category: {category_name}")

            try:
                fluxer_category = await self.fluxer_http.create_guild_channel(
                    fluxer_guild_id,
                    name=category_name,
                    type=4,  # Category type
                    position=category.get("position", 0),
                )

                fluxer_category_id = fluxer_category["id"]
                self.category_id_map[category_id] = fluxer_category_id
                self.logger.log(f"  ✓ Category created")

                # Add delay to avoid rate limiting
                await asyncio.sleep(1.0)

            except Exception as e:
                self.logger.log(f"  Failed to create category '{category_name}': {e}", "WARN")

        # Second pass: Create channels
        channel_count = 0

        for channel in sorted(channels, key=lambda c: c.get("position", 0)):
            channel_type = channel.get("type", 0)
            channel_name = channel.get("name", "unnamed")
            channel_id = channel["id"]

            # Skip categories (already done)
            if channel_type == 4:
                continue

            parent_id = None
            if channel.get("parent_id"):
                parent_id = self.category_id_map.get(channel["parent_id"])

            # Text channels (0) or Announcement channels (5)
            if channel_type in [0, 5]:
                self.logger.log(f"Creating text channel: #{channel_name}")

                try:
                    fluxer_channel = await self.fluxer_http.create_guild_channel(
                        fluxer_guild_id,
                        name=channel_name,
                        type=0,  # Text channel
                        topic=channel.get("topic"),
                        nsfw=channel.get("nsfw", False),
                        position=channel.get("position", 0),
                        parent_id=parent_id,
                    )
                    fluxer_channel_id = fluxer_channel["id"]
                    self.channel_id_map[channel_id] = fluxer_channel_id
                    self.logger.log(f"  ✓ Text channel created")

                    # Apply permissions if enabled
                    if migrate_permissions:
                        await self._apply_channel_permissions(channel, fluxer_channel_id)

                    channel_count += 1
                    await asyncio.sleep(1.0)
                except Exception as e:
                    self.logger.log(f"  Failed to create text channel '{channel_name}': {e}", "WARN")

            # Voice channels (2)
            elif channel_type == 2:
                self.logger.log(f"Creating voice channel: {channel_name}")

                try:
                    fluxer_channel = await self.fluxer_http.create_guild_channel(
                        fluxer_guild_id,
                        name=channel_name,
                        type=2,  # Voice channel
                        bitrate=channel.get("bitrate", 64000),
                        user_limit=channel.get("user_limit", 0),
                        position=channel.get("position", 0),
                        parent_id=parent_id,
                    )
                    fluxer_channel_id = fluxer_channel["id"]
                    self.channel_id_map[channel_id] = fluxer_channel_id
                    self.logger.log(f"  ✓ Voice channel created")

                    # Apply permissions if enabled
                    if migrate_permissions:
                        await self._apply_channel_permissions(channel, fluxer_channel_id)

                    channel_count += 1
                    await asyncio.sleep(1.0)
                except Exception as e:
                    self.logger.log(f"  Failed to create voice channel '{channel_name}': {e}", "WARN")

            # Forum channels (15) -> Convert to text channel
            elif channel_type == 15:
                self.logger.log(f"Converting forum channel to text: {channel_name}")
                self.logger.log_unsupported("Forum channel", f"Converting '{channel_name}' to text channel")

                try:
                    topic = f"Converted from forum. {channel.get('topic', '')}".strip()
                    fluxer_channel = await self.fluxer_http.create_guild_channel(
                        fluxer_guild_id,
                        name=channel_name,
                        type=0,  # Text channel
                        topic=topic,
                        nsfw=channel.get("nsfw", False),
                        position=channel.get("position", 0),
                        parent_id=parent_id,
                    )
                    fluxer_channel_id = fluxer_channel["id"]
                    self.channel_id_map[channel_id] = fluxer_channel_id
                    self.logger.log(f"  ✓ Converted to text channel")

                    # Apply permissions if enabled
                    if migrate_permissions:
                        await self._apply_channel_permissions(channel, fluxer_channel_id)

                    channel_count += 1
                    await asyncio.sleep(1.0)
                except Exception as e:
                    self.logger.log(f"  Failed to convert forum '{channel_name}': {e}", "WARN")

            # Stage channels (13)
            elif channel_type == 13:
                self.logger.log(f"Skipping stage channel: {channel_name}")
                self.logger.log_unsupported("Stage channel", f"Skipped '{channel_name}'")

            # Threads (10, 11, 12)
            elif channel_type in [10, 11, 12]:
                self.logger.log(f"Skipping thread: {channel_name}")
                self.logger.log_unsupported("Thread", f"Skipped '{channel_name}'")

            # Other types
            else:
                self.logger.log(f"Unknown channel type {channel_type}: {channel_name}")
                self.logger.log_unsupported(f"Channel type: {channel_type}", f"Skipped '{channel_name}'")

        self.logger.log(f"✓ Migrated {channel_count} channels")

    async def _migrate_emojis(
        self,
        emojis: list[dict[str, Any]],
        discord_guild_id: str,
        fluxer_guild_id: str
    ):
        """Migrate emojis from Discord to Fluxer."""
        self.logger.log("\n--- Migrating Emojis ---")

        if not emojis:
            self.logger.log("No emojis to migrate")
            return

        emoji_count = 0

        for emoji in emojis:
            emoji_name = emoji.get("name", "unnamed")
            emoji_id = emoji["id"]
            animated = emoji.get("animated", False)

            # Build emoji URL
            emoji_ext = "gif" if animated else "png"
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{emoji_ext}?size=128"

            self.logger.log(f"Migrating emoji: :{emoji_name}: {'(animated)' if animated else ''}")

            try:
                # Download emoji image
                emoji_data = await self._download_image(emoji_url)

                if not emoji_data:
                    self.logger.log(f"  Failed to download emoji", "WARN")
                    continue

                # Upload to Fluxer
                await self.fluxer_http.create_guild_emoji(
                    fluxer_guild_id,
                    name=emoji_name,
                    image=emoji_data
                )

                self.logger.log(f"  ✓ Emoji created")
                emoji_count += 1

                # Rate limiting - emojis are usually more restricted
                await asyncio.sleep(2.0)

            except Exception as e:
                self.logger.log(f"  Failed to create emoji '{emoji_name}': {e}", "WARN")

        self.logger.log(f"✓ Migrated {emoji_count} emojis")
