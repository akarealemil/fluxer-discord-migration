"""Profile migration from Discord to Fluxer."""

from typing import Any
import aiohttp


class ProfileMigrator:
    """Handles migration of user profile from Discord to Fluxer."""

    def __init__(self, discord_user: dict[str, Any], discord_http, fluxer_http, logger):
        self.discord_user = discord_user
        self.discord_http = discord_http
        self.fluxer_http = fluxer_http
        self.logger = logger

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

    async def migrate(self) -> bool:
        """Migrate user profile from Discord to Fluxer."""
        if not self.discord_user or not self.fluxer_http:
            self.logger.log("Clients not initialized", "ERROR")
            return False

        self.logger.log("\n=== Migrating Profile ===")

        try:
            # Get current Fluxer user
            fluxer_user = await self.fluxer_http.get_current_user()
            self.logger.log(f"Current Fluxer user: {fluxer_user.get('username', 'Unknown')}")

            # Extract all Discord profile fields
            discord_avatar = self.discord_user.get("avatar")
            discord_banner = self.discord_user.get("banner")
            discord_global_name = self.discord_user.get("global_name")
            discord_bio = self.discord_user.get("bio")
            discord_pronouns = self.discord_user.get("pronouns")

            # Get colors from Discord - theme_colors is the actual profile colors
            theme_colors = self.discord_user.get("theme_colors")  # [primary, secondary]

            chosen_color = None
            if theme_colors and len(theme_colors) > 0:
                self.logger.log("\nColor Migration:")
                self.logger.log(f"  Discord has {len(theme_colors)} profile colors:")
                for i, color in enumerate(theme_colors, 1):
                    self.logger.log(f"    Color {i}: #{color:06x}")

                # Show current Fluxer color
                current_fluxer_color = fluxer_user.get("accent_color")
                if current_fluxer_color:
                    self.logger.log(f"  Current Fluxer Color: #{current_fluxer_color:06x}")
                else:
                    self.logger.log(f"  Current Fluxer Color: None")

                # Let user choose which color to use
                if len(theme_colors) == 1:
                    chosen_color = theme_colors[0]
                    self.logger.log(f"  → Using #{chosen_color:06x}")
                elif len(theme_colors) >= 2:
                    self.logger.log(f"\n  Which color do you want to use on Fluxer?")
                    self.logger.log(f"    [1] Primary: #{theme_colors[0]:06x}")
                    self.logger.log(f"    [2] Secondary: #{theme_colors[1]:06x}")

                    choice = input("  Your choice (1 or 2): ").strip()
                    if choice == "2":
                        chosen_color = theme_colors[1]
                    else:
                        chosen_color = theme_colors[0]

                    self.logger.log(f"  → Selected #{chosen_color:06x}")

            # Prepare update payload
            updates: dict[str, Any] = {}

            # Migrate avatar
            if discord_avatar:
                self.logger.log("Downloading avatar...")
                user_id = self.discord_user["id"]
                # Discord CDN avatar URL - use size=4096 for max quality
                avatar_ext = "gif" if discord_avatar.startswith("a_") else "png"
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{discord_avatar}.{avatar_ext}?size=4096"
                avatar_data = await self._download_image(avatar_url)

                if avatar_data:
                    self.logger.log("Uploading avatar to Fluxer...")
                    try:
                        await self.fluxer_http.modify_current_user(avatar=avatar_data)
                        self.logger.log("✓ Avatar updated")
                    except Exception as e:
                        self.logger.log(f"Failed to upload avatar: {e}", "WARN")
                else:
                    self.logger.log("Failed to download avatar", "WARN")

            # Banner (if available)
            if discord_banner:
                self.logger.log("Downloading banner...")
                user_id = self.discord_user["id"]
                # Discord CDN banner URL - use size=4096 for max quality
                banner_ext = "gif" if discord_banner.startswith("a_") else "png"
                banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{discord_banner}.{banner_ext}?size=4096"
                banner_data = await self._download_image(banner_url)

                if banner_data:
                    self.logger.log("Uploading banner to Fluxer...")
                    try:
                        await self.fluxer_http.modify_current_user(banner=banner_data)
                        self.logger.log("✓ Banner updated")
                    except Exception as e:
                        self.logger.log(f"Failed to upload banner: {e}", "WARN")
                        self.logger.log_unsupported("Banner", "Fluxer may not support banners yet")

            # Build update payload for text fields and colors
            # Bio
            if discord_bio and discord_bio != fluxer_user.get("bio"):
                self.logger.log(f"Bio: {discord_bio[:50]}..." if len(discord_bio) > 50 else f"Bio: {discord_bio}")
                updates["bio"] = discord_bio

            # Display name - always log what we found
            current_fluxer_name = fluxer_user.get("global_name")
            self.logger.log(f"Display name check: Discord='{discord_global_name}' vs Fluxer='{current_fluxer_name}'")
            if discord_global_name and discord_global_name != current_fluxer_name:
                self.logger.log(f"Will update display name: {discord_global_name}")
                updates["global_name"] = discord_global_name
            elif discord_global_name == current_fluxer_name:
                self.logger.log(f"Display name already matches: {discord_global_name}")

            # Pronouns
            if discord_pronouns and discord_pronouns != fluxer_user.get("pronouns"):
                self.logger.log(f"Pronouns: {discord_pronouns}")
                updates["pronouns"] = discord_pronouns

            # Accent color (Fluxer only has this field)
            if chosen_color is not None and chosen_color != fluxer_user.get("accent_color"):
                updates["accent_color"] = chosen_color

            # Send all updates in one request
            if updates:
                try:
                    self.logger.log(f"Updating {len(updates)} profile fields...")
                    result = await self.fluxer_http.modify_current_user(**updates)

                    # Verify what actually changed
                    for field, expected_value in updates.items():
                        actual_value = result.get(field)
                        if actual_value == expected_value:
                            self.logger.log(f"  ✓ {field} updated")
                        else:
                            self.logger.log(f"  ⚠ {field}: API accepted but value is '{actual_value}' (expected '{expected_value}')", "WARN")

                except Exception as e:
                    self.logger.log(f"Failed to update profile fields: {e}", "ERROR")
                    import traceback
                    traceback.print_exc()
            else:
                self.logger.log("All profile fields already match - no updates needed")

            self.logger.log("✓ Profile migration complete")
            return True

        except Exception as e:
            self.logger.log(f"Profile migration failed: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False
