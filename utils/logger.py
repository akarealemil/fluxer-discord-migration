"""Logger for migration process and unsupported features."""

from datetime import datetime
from pathlib import Path


class MigrationLogger:
    """Logger for migration process and unsupported features."""

    def __init__(self, filename: str | None = None):
        # Get the migration directory and logs folder
        migration_dir = Path(__file__).parent.parent
        logs_dir = migration_dir / "logs"

        # Create logs directory if it doesn't exist
        logs_dir.mkdir(exist_ok=True)

        # Use timestamped filename if not specified
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"migration_{timestamp}.txt"

        self.filename = logs_dir / filename
        self.unsupported_features: list[str] = []
        self.log_entries: list[str] = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message to console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        self.log_entries.append(entry)
        print(f"  {message}")

    def log_unsupported(self, feature: str, details: str = ""):
        """Log an unsupported feature."""
        message = f"Unsupported: {feature}"
        if details:
            message += f" - {details}"
        self.unsupported_features.append(message)
        self.log(message, "WARN")

    def save(self):
        """Save all logs to file."""
        with open(self.filename, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("Discord to Fluxer Migration Log\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            if self.unsupported_features:
                f.write("UNSUPPORTED FEATURES\n")
                f.write("-" * 80 + "\n")
                for feature in self.unsupported_features:
                    f.write(f"  • {feature}\n")
                f.write("\n")

            f.write("MIGRATION LOG\n")
            f.write("-" * 80 + "\n")
            for entry in self.log_entries:
                f.write(entry + "\n")

        print(f"\n✓ Migration log saved to: {self.filename}")
