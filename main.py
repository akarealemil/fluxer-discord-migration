"""Discord to Fluxer Migration Tool

This tool helps you migrate your Discord profile and servers to Fluxer.
Uses user tokens for both Discord and Fluxer - no bots required!

Features:
- Migrate profile (display name, avatar, banner, bio, pronouns, colors)
- Migrate servers you own (channels, voice channels, roles)
- Skip unsupported features and log them
"""

from __future__ import annotations

import asyncio
from typing import Any

from utils import MigrationLogger, load_config, clean_token
from clients import DiscordHTTPClient, FluxerClient
from migrators import ProfileMigrator, ServerMigrator


class MigrationOrchestrator:
    """Main orchestrator for Discord to Fluxer migration."""

    def __init__(self):
        self.discord_http: DiscordHTTPClient | None = None
        self.fluxer_http: FluxerClient | None = None
        self.logger = MigrationLogger()
        self.discord_user: dict[str, Any] | None = None
        self.discord_guilds: list[dict[str, Any]] = []

    async def setup_discord(self, token: str):
        """Initialize Discord HTTP client."""
        # Clean the token
        token = clean_token(token)

        # Basic validation - just check it's not empty
        if not token or len(token) < 20:
            raise ValueError(
                "Token appears to be too short or empty.\n"
                "Make sure you copied the ENTIRE token from the Authorization header."
            )

        self.discord_http = DiscordHTTPClient(token)

        try:
            # Test connection and get user info
            self.discord_user = await self.discord_http.get_current_user()
            username = self.discord_user.get("username", "Unknown")
            discriminator = self.discord_user.get("discriminator")

            if discriminator and discriminator != "0":
                user_display = f"{username}#{discriminator}"
            else:
                user_display = username

            self.logger.log(f"Connected to Discord as {user_display}")

            # Fetch guilds
            self.discord_guilds = await self.discord_http.get_guilds()
            self.logger.log(f"Found {len(self.discord_guilds)} Discord servers")

        except ValueError as e:
            raise ValueError(
                f"Discord connection failed: {e}\n\n"
                "Your token may be invalid or expired.\n"
                "How to get a fresh token:\n"
                "  1. Open Discord in browser (discord.com/app)\n"
                "  2. Press F12 → Network tab\n"
                "  3. Press F5 to refresh\n"
                "  4. Type 'api' in filter\n"
                "  5. Click any request → Headers → Look for 'authorization:'\n"
                "  6. Copy the ENTIRE value after 'authorization:' or 'Bearer '"
            )
        except Exception as e:
            raise ValueError(f"Unexpected error connecting to Discord: {e}")

    async def setup_fluxer(self, token: str):
        """Initialize Fluxer HTTP client with user token."""
        # Clean the token
        token = clean_token(token)

        self.fluxer_http = FluxerClient(token)

        # Test connection
        try:
            user_data = await self.fluxer_http.get_current_user()
            self.logger.log(f"Connected to Fluxer as {user_data.get('username', 'Unknown')}")
        except Exception as e:
            self.logger.log(f"Failed to connect to Fluxer: {e}", "ERROR")
            raise ValueError(
                "Fluxer connection failed. Your token may be invalid or expired.\n"
                "Get a fresh Fluxer token the same way as Discord:\n"
                "  1. Open Fluxer in browser\n"
                "  2. Press F12 → Network tab\n"
                "  3. Press F5 to refresh\n"
                "  4. Find any API request\n"
                "  5. Look for 'authorization:' header\n"
                "  6. Copy the entire token"
            )

    async def migrate_profile(self):
        """Migrate user profile from Discord to Fluxer."""
        migrator = ProfileMigrator(self.discord_user, self.discord_http, self.fluxer_http, self.logger)
        return await migrator.migrate()

    def select_servers(self) -> list[dict[str, Any]]:
        """Interactive server selection."""
        if not self.discord_guilds or not self.discord_user:
            return []

        # Get only servers the user owns
        user_id = self.discord_user["id"]
        owned_guilds = [g for g in self.discord_guilds if g.get("owner") or g.get("owner_id") == user_id]

        if not owned_guilds:
            self.logger.log("You don't own any servers", "WARN")
            return []

        print("\n" + "=" * 80)
        print("SERVERS YOU OWN")
        print("=" * 80)

        for i, guild in enumerate(owned_guilds, 1):
            member_count = guild.get("approximate_member_count", "?")
            print(f"  [{i}] {guild['name']} ({member_count} members)")

        print("\nOptions:")
        print("  • Enter numbers separated by commas (e.g., 1,3,5)")
        print("  • Enter 'all' to select all servers")
        print("  • Enter 'cancel' to skip server migration")

        while True:
            choice = input("\nYour choice: ").strip().lower()

            if choice == "cancel":
                return []

            if choice == "all":
                return owned_guilds

            try:
                indices = [int(x.strip()) for x in choice.split(",")]
                selected = [owned_guilds[i - 1] for i in indices if 1 <= i <= len(owned_guilds)]

                if selected:
                    return selected
                else:
                    print("Invalid selection. Please try again.")
            except (ValueError, IndexError):
                print("Invalid input. Please try again.")

    def select_migration_options(self, discord_guild: dict[str, Any]) -> dict[str, bool] | None:
        """Ask user what to migrate for a specific server.

        Returns:
            Dict with migration options, or None if cancelled
        """
        print("\n" + "=" * 80)
        print(f"Migration Options for: {discord_guild['name']}")
        print("=" * 80)
        print("\nWhat would you like to migrate?")
        print("  [1] Everything (roles, channels, permissions, emojis)")
        print("  [2] Custom selection")
        print("  [3] Cancel")

        choice = input("\nYour choice: ").strip()

        if choice == "1":
            return {
                'roles': True,
                'channels': True,
                'permissions': True,
                'emojis': True
            }

        elif choice == "2":
            print("\n" + "=" * 80)
            print("Custom Selection (y/n for each)")
            print("=" * 80)

            options = {}

            # Ask about each migration option
            migrate_roles = input("Migrate roles? (y/n): ").strip().lower() == 'y'
            options['roles'] = migrate_roles

            migrate_channels = input("Migrate channels? (y/n): ").strip().lower() == 'y'
            options['channels'] = migrate_channels

            if migrate_channels:
                migrate_permissions = input("Migrate channel permissions? (y/n): ").strip().lower() == 'y'
                options['permissions'] = migrate_permissions
            else:
                options['permissions'] = False

            migrate_emojis = input("Migrate emojis? (y/n): ").strip().lower() == 'y'
            options['emojis'] = migrate_emojis

            # Summary
            print("\n" + "=" * 80)
            print("Migration Summary:")
            print(f"  • Roles: {'✓' if options['roles'] else '✗'}")
            print(f"  • Channels: {'✓' if options['channels'] else '✗'}")
            print(f"  • Channel Permissions: {'✓' if options['permissions'] else '✗'}")
            print(f"  • Emojis: {'✓' if options['emojis'] else '✗'}")
            print("=" * 80)

            confirm = input("\nProceed with this configuration? (y/n): ").strip().lower()
            if confirm == 'y':
                return options
            else:
                return None

        elif choice == "3":
            return None

        else:
            print("Invalid choice. Cancelling.")
            return None

    async def select_fluxer_guild_for_migration(
        self,
        discord_guild: dict[str, Any]
    ) -> str | None:
        """Ask user if they want to create new or use existing Fluxer guild.

        Returns:
            Fluxer guild ID if using existing, None if creating new
        """
        print("\n" + "=" * 80)
        print(f"Discord Server: {discord_guild['name']}")
        print("=" * 80)
        print("\nWhere do you want to migrate this server?")
        print("  [1] Create a NEW Fluxer server")
        print("  [2] Add to an EXISTING Fluxer server")
        print("  [3] Skip this server")

        choice = input("\nYour choice: ").strip()

        if choice == "1":
            return None  # Create new

        elif choice == "2":
            # Fetch Fluxer guilds
            try:
                fluxer_guilds = await self.fluxer_http.get_current_user_guilds()

                if not fluxer_guilds:
                    print("\nYou're not in any Fluxer servers yet!")
                    print("Creating a new server instead...")
                    return None

                print("\n" + "=" * 80)
                print("YOUR FLUXER SERVERS")
                print("=" * 80)

                for i, guild in enumerate(fluxer_guilds, 1):
                    owner_mark = " [OWNER]" if guild.get("owner") else ""
                    print(f"  [{i}] {guild['name']}{owner_mark}")

                while True:
                    guild_choice = input("\nSelect a server (or 'cancel'): ").strip()

                    if guild_choice.lower() == "cancel":
                        return None

                    try:
                        idx = int(guild_choice) - 1
                        if 0 <= idx < len(fluxer_guilds):
                            selected_guild = fluxer_guilds[idx]
                            print(f"\n✓ Will migrate into: {selected_guild['name']}")
                            print("  (Roles and channels will be ADDED, nothing will be deleted)")
                            return selected_guild["id"]
                        else:
                            print("Invalid selection. Try again.")
                    except ValueError:
                        print("Invalid input. Try again.")

            except Exception as e:
                print(f"\nError fetching Fluxer servers: {e}")
                print("Creating a new server instead...")
                return None

        elif choice == "3":
            return "SKIP"

        else:
            print("Invalid choice. Skipping this server.")
            return "SKIP"

    async def migrate_servers(self, servers: list[dict[str, Any]]):
        """Migrate multiple servers."""
        server_migrator = ServerMigrator(self.discord_http, self.fluxer_http, self.logger)

        for guild in servers:
            # Ask what to migrate for this guild
            migration_options = self.select_migration_options(guild)

            if migration_options is None:
                print(f"\nSkipping {guild['name']}")
                continue

            # Ask where to migrate this guild
            fluxer_guild_id = await self.select_fluxer_guild_for_migration(guild)

            if fluxer_guild_id == "SKIP":
                print(f"\nSkipping {guild['name']}")
                continue

            await server_migrator.migrate_server(
                guild,
                existing_fluxer_guild_id=fluxer_guild_id,
                migration_options=migration_options
            )
            # Small delay between servers
            await asyncio.sleep(1)

    async def run(self):
        """Main migration flow."""
        print("=" * 80)
        print(" " * 20 + "Discord to Fluxer Migration Tool")
        print("=" * 80)
        print()

        # Try to load from config
        config = load_config()
        discord_token = config["discord_token"]
        fluxer_token = config["fluxer_token"]

        # Prompt if not in config
        if not discord_token:
            print("This tool uses USER TOKENS (not bot tokens) for easy migration.")
            print()
            print("Enter your Discord user token:")
            print("  (How to get it: Discord Web → F12 → Network tab → Refresh →")
            print("   Find any 'api' request → Look for 'Authorization' header)")
            print("  (Or create config/config.json - see config/config.example.json)")
            discord_token = input("Discord Token: ").strip()

            if not discord_token:
                print("Error: Discord token is required")
                return
        else:
            print("✓ Loaded Discord token from config.json")

        if not fluxer_token:
            print("\nEnter your Fluxer user token:")
            print("  (Get it the same way from Fluxer web app)")
            print("  (Or create config/config.json - see config/config.example.json)")
            fluxer_token = input("Fluxer Token: ").strip()

            if not fluxer_token:
                print("Error: Fluxer token is required")
                return
        else:
            print("✓ Loaded Fluxer token from config.json")

        print("\n" + "=" * 80)
        print("Connecting to Discord and Fluxer...")
        print("=" * 80)

        try:
            # Setup clients
            await self.setup_discord(discord_token)
            await self.setup_fluxer(fluxer_token)

            # Main menu
            while True:
                print("\n" + "=" * 80)
                print("MIGRATION OPTIONS")
                print("=" * 80)
                print("  [1] Migrate Profile")
                # print("  [2] Migrate Servers")
                # print("  [3] Migrate Profile + Servers")
                print("  [2] Exit")

                choice = input("\nYour choice: ").strip()

                if choice == "1":
                    await self.migrate_profile()

                # elif choice == "2":
                #     servers = self.select_servers()
                #     if servers:
                #         await self.migrate_servers(servers)

                # elif choice == "3":
                #     await self.migrate_profile()
                #     print("\n")
                #     servers = self.select_servers()
                #     if servers:
                #         await self.migrate_servers(servers)

                elif choice == "2":
                    break

                else:
                    print("Invalid choice. Please try again.")

        except Exception as e:
            self.logger.log(f"Migration failed: {e}", "ERROR")
            import traceback
            traceback.print_exc()

        finally:
            # Save log
            self.logger.save()

            # Cleanup
            if self.discord_http:
                await self.discord_http.close()
            if self.fluxer_http:
                await self.fluxer_http.close()

            # Give async cleanup time to finish (Windows fix)
            await asyncio.sleep(0.25)

            print("\n" + "=" * 80)
            print("Migration complete!")
            print("=" * 80)


async def main():
    """Entry point."""
    orchestrator = MigrationOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
