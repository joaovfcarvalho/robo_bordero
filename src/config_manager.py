"""
Secure configuration manager for CBF Robot.
Uses OS keyring for persistent, secure credential storage.
"""

import os
import keyring
import json
from pathlib import Path
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)

# Keyring service name (namespace for credentials)
SERVICE_NAME = "cbf_robot"

# Credential keys
KEY_ANTHROPIC_API = "anthropic_api_key"
KEY_SUPABASE_URL = "supabase_url"
KEY_SUPABASE_KEY = "supabase_key"
KEY_SUPABASE_SERVICE_KEY = "supabase_service_key"


class ConfigManager:
    """
    Manages application configuration with secure credential storage.

    Priority order for loading credentials:
    1. OS Keyring (most secure, persistent)
    2. Environment variables (.env file)
    3. Legacy config.json (for backward compatibility)
    4. User prompt (saves to keyring)
    """

    def __init__(self):
        self.config_file = Path("config.json")
        self._cache = {}

    def get_credential(self, key: str, prompt_if_missing: bool = False) -> Optional[str]:
        """
        Get a credential using priority order: keyring -> env -> config.json

        Args:
            key: Credential key (e.g., KEY_ANTHROPIC_API)
            prompt_if_missing: If True, prompt user if credential not found

        Returns:
            Credential value or None
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # 1. Try OS keyring first (most secure)
        try:
            value = keyring.get_password(SERVICE_NAME, key)
            if value:
                logger.debug(f"Loaded {key} from OS keyring")
                self._cache[key] = value
                return value
        except Exception as e:
            logger.warning(f"Failed to access keyring for {key}: {e}")

        # 2. Try environment variables (.env file)
        env_key_map = {
            KEY_ANTHROPIC_API: "ANTHROPIC_API_KEY",
            KEY_SUPABASE_URL: "SUPABASE_URL",
            KEY_SUPABASE_KEY: "SUPABASE_KEY",
            KEY_SUPABASE_SERVICE_KEY: "SUPABASE_SERVICE_KEY"
        }

        env_key = env_key_map.get(key)
        if env_key:
            value = os.getenv(env_key)
            if value:
                logger.debug(f"Loaded {key} from environment variable {env_key}")
                self._cache[key] = value
                return value

        # 3. Try legacy config.json
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)

                # Map legacy keys
                legacy_key_map = {
                    KEY_ANTHROPIC_API: ["api_key", "anthropic_api_key", "gemini_api_key"],
                    KEY_SUPABASE_URL: ["supabase_url"],
                    KEY_SUPABASE_KEY: ["supabase_key"],
                    KEY_SUPABASE_SERVICE_KEY: ["supabase_service_key"]
                }

                for legacy_key in legacy_key_map.get(key, []):
                    if legacy_key in config and config[legacy_key]:
                        value = config[legacy_key]
                        logger.info(f"Loaded {key} from config.json (legacy)")
                        logger.warning("Consider migrating to keyring with: python -m src.config_manager set")
                        self._cache[key] = value
                        return value
            except Exception as e:
                logger.warning(f"Failed to load from config.json: {e}")

        # 4. Not found anywhere
        if prompt_if_missing:
            logger.warning(f"Credential {key} not found anywhere")

        return None

    def set_credential(self, key: str, value: str, persist: bool = True) -> bool:
        """
        Set a credential and optionally save to OS keyring.

        Args:
            key: Credential key
            value: Credential value
            persist: If True, save to OS keyring for future sessions

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update cache
            self._cache[key] = value

            # Save to keyring if requested
            if persist:
                keyring.set_password(SERVICE_NAME, key, value)
                logger.info(f"Saved {key} to OS keyring")

            return True
        except Exception as e:
            logger.error(f"Failed to set credential {key}: {e}")
            return False

    def delete_credential(self, key: str) -> bool:
        """
        Delete a credential from OS keyring and cache.

        Args:
            key: Credential key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from cache
            if key in self._cache:
                del self._cache[key]

            # Remove from keyring
            try:
                keyring.delete_password(SERVICE_NAME, key)
                logger.info(f"Deleted {key} from OS keyring")
            except keyring.errors.PasswordDeleteError:
                logger.debug(f"Credential {key} not found in keyring")

            return True
        except Exception as e:
            logger.error(f"Failed to delete credential {key}: {e}")
            return False

    def get_anthropic_key(self) -> Optional[str]:
        """Get Anthropic API key."""
        return self.get_credential(KEY_ANTHROPIC_API)

    def get_supabase_url(self) -> Optional[str]:
        """Get Supabase project URL."""
        return self.get_credential(KEY_SUPABASE_URL)

    def get_supabase_key(self) -> Optional[str]:
        """Get Supabase anon key."""
        return self.get_credential(KEY_SUPABASE_KEY)

    def get_supabase_service_key(self) -> Optional[str]:
        """Get Supabase service role key (admin)."""
        return self.get_credential(KEY_SUPABASE_SERVICE_KEY)

    def list_credentials(self) -> Dict[str, bool]:
        """
        List which credentials are available.

        Returns:
            Dict mapping credential keys to availability status
        """
        creds = {
            "Anthropic API Key": self.get_anthropic_key() is not None,
            "Supabase URL": self.get_supabase_url() is not None,
            "Supabase Anon Key": self.get_supabase_key() is not None,
            "Supabase Service Key": self.get_supabase_service_key() is not None
        }
        return creds


# Global config manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get or create the global ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# CLI interface for managing credentials
if __name__ == "__main__":
    import sys
    import getpass

    manager = ConfigManager()

    def cmd_set():
        """Set credentials interactively."""
        print("=== CBF Robot - Secure Credential Setup ===\n")
        print("This will save your credentials securely in your OS keyring.")
        print("You only need to do this once!\n")

        # Anthropic API Key
        current_anthropic = manager.get_anthropic_key()
        if current_anthropic:
            print(f"✓ Anthropic API Key is already set (starts with: {current_anthropic[:8]}...)")
            update = input("  Update? (y/N): ").lower() == 'y'
        else:
            update = True

        if update:
            anthropic_key = getpass.getpass("Enter Anthropic API Key (hidden): ").strip()
            if anthropic_key:
                if manager.set_credential(KEY_ANTHROPIC_API, anthropic_key):
                    print("✓ Anthropic API Key saved!")
                else:
                    print("✗ Failed to save Anthropic API Key")

        print()

        # Supabase (optional)
        setup_supabase = input("Set up Supabase credentials? (y/N): ").lower() == 'y'

        if setup_supabase:
            # Supabase URL
            current_url = manager.get_supabase_url()
            if current_url:
                print(f"✓ Supabase URL is already set: {current_url}")
                update = input("  Update? (y/N): ").lower() == 'y'
            else:
                update = True

            if update:
                supabase_url = input("Enter Supabase URL (e.g., https://xxx.supabase.co): ").strip()
                if supabase_url:
                    manager.set_credential(KEY_SUPABASE_URL, supabase_url)
                    print("✓ Supabase URL saved!")

            # Supabase anon key
            supabase_key = getpass.getpass("Enter Supabase anon key (hidden): ").strip()
            if supabase_key:
                manager.set_credential(KEY_SUPABASE_KEY, supabase_key)
                print("✓ Supabase anon key saved!")

            # Supabase service key (optional)
            service_key = input("Enter Supabase service key (optional, press Enter to skip): ")
            if service_key.strip():
                manager.set_credential(KEY_SUPABASE_SERVICE_KEY, service_key.strip())
                print("✓ Supabase service key saved!")

        print("\n=== Setup Complete! ===")
        print("Your credentials are now stored securely in your OS keyring.")
        print("Run the application normally - credentials will load automatically.")

    def cmd_list():
        """List available credentials."""
        print("=== CBF Robot - Credential Status ===\n")
        creds = manager.list_credentials()
        for name, available in creds.items():
            status = "✓ SET" if available else "✗ NOT SET"
            print(f"{status}  {name}")
        print()

    def cmd_delete():
        """Delete credentials."""
        print("=== CBF Robot - Delete Credentials ===\n")
        print("WARNING: This will delete credentials from your OS keyring.")
        confirm = input("Are you sure? (type 'yes' to confirm): ")

        if confirm.lower() == 'yes':
            manager.delete_credential(KEY_ANTHROPIC_API)
            manager.delete_credential(KEY_SUPABASE_URL)
            manager.delete_credential(KEY_SUPABASE_KEY)
            manager.delete_credential(KEY_SUPABASE_SERVICE_KEY)
            print("\n✓ All credentials deleted from keyring.")
        else:
            print("\n✗ Cancelled.")

    def cmd_help():
        """Show help."""
        print("""
=== CBF Robot - Credential Manager ===

Secure credential storage using your OS keyring.

Commands:
  set     - Set up credentials (interactive, recommended)
  list    - Show which credentials are configured
  delete  - Delete all credentials from keyring
  help    - Show this help message

Examples:
  python -m src.config_manager set      # First-time setup
  python -m src.config_manager list     # Check status
  python -m src.config_manager delete   # Remove credentials

Your credentials are stored in:
  Windows: Credential Manager
  macOS:   Keychain
  Linux:   Secret Service API
        """)

    # Parse command
    if len(sys.argv) < 2:
        cmd_help()
    else:
        command = sys.argv[1].lower()

        if command == "set":
            cmd_set()
        elif command == "list":
            cmd_list()
        elif command == "delete":
            cmd_delete()
        elif command in ["help", "-h", "--help"]:
            cmd_help()
        else:
            print(f"Unknown command: {command}")
            print("Run with 'help' for usage information.")
