"""
Secure configuration manager for CBF Robot.
Supports multiple storage backends for different scenarios.
"""

import os
import keyring
import json
from pathlib import Path
from typing import Optional, Dict, Any
import structlog
from cryptography.fernet import Fernet
import base64
import hashlib

logger = structlog.get_logger(__name__)

# Keyring service name (namespace for credentials)
SERVICE_NAME = "cbf_robot"

# Credential keys
KEY_ANTHROPIC_API = "anthropic_api_key"
KEY_SUPABASE_URL = "supabase_url"
KEY_SUPABASE_KEY = "supabase_key"
KEY_SUPABASE_SERVICE_KEY = "supabase_service_key"


class EncryptedConfigFile:
    """
    Encrypted configuration file for environments without keyring access.
    Perfect for work machines with admin restrictions!

    Stores credentials encrypted in ~/.cbf_robot_config (or cloud-synced folder).
    """

    def __init__(self, config_path: Optional[Path] = None, password: Optional[str] = None):
        """
        Initialize encrypted config.

        Args:
            config_path: Path to encrypted config file (default: ~/.cbf_robot_config)
            password: Encryption password (will prompt if not provided)
        """
        # Default to user's home directory (can be synced via OneDrive/Google Drive)
        if config_path is None:
            self.config_path = Path.home() / ".cbf_robot_config"
        else:
            self.config_path = Path(config_path)

        self.password = password
        self._cipher = None

    def _get_cipher(self) -> Fernet:
        """Get or create Fernet cipher from password."""
        if self._cipher is None:
            if self.password is None:
                raise ValueError("Password required for encrypted config")

            # Derive encryption key from password
            key = base64.urlsafe_b64encode(
                hashlib.sha256(self.password.encode()).digest()
            )
            self._cipher = Fernet(key)

        return self._cipher

    def save(self, credentials: Dict[str, str]):
        """
        Save credentials to encrypted file.

        Args:
            credentials: Dict of credential key -> value
        """
        try:
            cipher = self._get_cipher()

            # Serialize and encrypt
            data = json.dumps(credentials).encode()
            encrypted = cipher.encrypt(data)

            # Write to file
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_bytes(encrypted)

            logger.info(f"Saved encrypted config to {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save encrypted config: {e}")
            return False

    def load(self) -> Optional[Dict[str, str]]:
        """
        Load credentials from encrypted file.

        Returns:
            Dict of credentials or None if file doesn't exist/can't decrypt
        """
        if not self.config_path.exists():
            return None

        try:
            cipher = self._get_cipher()

            # Read and decrypt
            encrypted = self.config_path.read_bytes()
            decrypted = cipher.decrypt(encrypted)

            # Deserialize
            credentials = json.loads(decrypted.decode())

            logger.info(f"Loaded encrypted config from {self.config_path}")
            return credentials

        except Exception as e:
            logger.error(f"Failed to load encrypted config: {e}")
            return None

    def delete(self):
        """Delete encrypted config file."""
        if self.config_path.exists():
            self.config_path.unlink()
            logger.info(f"Deleted encrypted config: {self.config_path}")


class ConfigManager:
    """
    Manages application configuration with multiple secure storage backends.

    Priority order for loading credentials:
    1. Encrypted config file (best for work machines without admin rights)
    2. OS Keyring (best for personal machines)
    3. Environment variables (.env file)
    4. Legacy config.json (backward compatibility)
    5. User prompt (saves to best available storage)

    Storage Selection:
    - Encrypted file: Works everywhere, can sync via OneDrive/Google Drive
    - OS Keyring: Most secure, but requires permissions
    """

    def __init__(self, use_encrypted_config: bool = True, config_password: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            use_encrypted_config: If True, try encrypted config file first
            config_password: Password for encrypted config (will prompt if needed)
        """
        self.config_file = Path("config.json")
        self._cache = {}
        self.use_encrypted_config = use_encrypted_config
        self._encrypted_config = None
        self._config_password = config_password

        # Detect if we have keyring access
        self._has_keyring = self._test_keyring_access()

    def _test_keyring_access(self) -> bool:
        """Test if we can access OS keyring."""
        try:
            # Try to set and get a test value
            test_key = f"{SERVICE_NAME}_test"
            keyring.set_password(SERVICE_NAME, test_key, "test")
            result = keyring.get_password(SERVICE_NAME, test_key)
            keyring.delete_password(SERVICE_NAME, test_key)
            return result == "test"
        except Exception as e:
            logger.debug(f"Keyring not available: {e}")
            return False

    def _get_encrypted_config(self) -> EncryptedConfigFile:
        """Get or create encrypted config instance."""
        if self._encrypted_config is None:
            self._encrypted_config = EncryptedConfigFile(password=self._config_password)
        return self._encrypted_config

    def get_credential(self, key: str, prompt_if_missing: bool = False) -> Optional[str]:
        """
        Get a credential using priority order: encrypted config -> keyring -> env -> config.json

        Args:
            key: Credential key (e.g., KEY_ANTHROPIC_API)
            prompt_if_missing: If True, prompt user if credential not found

        Returns:
            Credential value or None
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # 1. Try encrypted config file first (works on work machines!)
        if self.use_encrypted_config:
            try:
                encrypted_config = self._get_encrypted_config()
                credentials = encrypted_config.load()
                if credentials and key in credentials:
                    value = credentials[key]
                    logger.debug(f"Loaded {key} from encrypted config")
                    self._cache[key] = value
                    return value
            except Exception as e:
                logger.debug(f"Encrypted config not available: {e}")

        # 2. Try OS keyring (if available and we have permissions)
        if self._has_keyring:
            try:
                value = keyring.get_password(SERVICE_NAME, key)
                if value:
                    logger.debug(f"Loaded {key} from OS keyring")
                    self._cache[key] = value
                    return value
            except Exception as e:
                logger.debug(f"Failed to access keyring for {key}: {e}")

        # 3. Try environment variables (.env file)
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

        # 4. Try legacy config.json
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
                        logger.warning("Consider migrating to encrypted config with: python setup_credentials.py")
                        self._cache[key] = value
                        return value
            except Exception as e:
                logger.warning(f"Failed to load from config.json: {e}")

        # 5. Not found anywhere
        if prompt_if_missing:
            logger.warning(f"Credential {key} not found anywhere")

        return None

    def set_credential(self, key: str, value: str, persist: bool = True) -> bool:
        """
        Set a credential and save to best available storage.

        Args:
            key: Credential key
            value: Credential value
            persist: If True, save persistently (encrypted config or keyring)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update cache
            self._cache[key] = value

            if not persist:
                return True

            # Try encrypted config first (works everywhere!)
            if self.use_encrypted_config:
                try:
                    encrypted_config = self._get_encrypted_config()
                    # Load existing credentials
                    all_creds = encrypted_config.load() or {}
                    # Update with new value
                    all_creds[key] = value
                    # Save back
                    if encrypted_config.save(all_creds):
                        logger.info(f"Saved {key} to encrypted config")
                        return True
                except Exception as e:
                    logger.warning(f"Failed to save to encrypted config: {e}")

            # Fall back to keyring if encrypted config failed
            if self._has_keyring:
                try:
                    keyring.set_password(SERVICE_NAME, key, value)
                    logger.info(f"Saved {key} to OS keyring")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to save to keyring: {e}")

            # If both failed, at least we have it in cache for this session
            logger.warning(f"Could not persist {key} - only available for this session")
            return False

        except Exception as e:
            logger.error(f"Failed to set credential {key}: {e}")
            return False

    def delete_credential(self, key: str) -> bool:
        """
        Delete a credential from all storage locations.

        Args:
            key: Credential key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from cache
            if key in self._cache:
                del self._cache[key]

            # Remove from encrypted config
            if self.use_encrypted_config:
                try:
                    encrypted_config = self._get_encrypted_config()
                    all_creds = encrypted_config.load() or {}
                    if key in all_creds:
                        del all_creds[key]
                        encrypted_config.save(all_creds)
                        logger.info(f"Deleted {key} from encrypted config")
                except Exception as e:
                    logger.debug(f"Could not delete from encrypted config: {e}")

            # Remove from keyring
            if self._has_keyring:
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
