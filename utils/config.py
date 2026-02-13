"""Configuration management for migration tool."""

import json
from pathlib import Path


def clean_token(token: str) -> str:
    """Clean and validate token format."""
    # Strip whitespace
    token = token.strip()

    # Remove "Bearer " prefix if present
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    # Remove quotes if present
    token = token.strip('"').strip("'")

    return token


def load_config() -> dict[str, str]:
    """Load tokens from config/config.json if it exists."""
    # Get the migration directory (parent of utils)
    migration_dir = Path(__file__).parent.parent
    config_path = migration_dir / "config" / "config.json"

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return {
                    "discord_token": config.get("discord_token", ""),
                    "fluxer_token": config.get("fluxer_token", "")
                }
        except Exception as e:
            print(f"Warning: Failed to load config/config.json: {e}")

    return {"discord_token": "", "fluxer_token": ""}
