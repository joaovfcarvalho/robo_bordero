#!/usr/bin/env python3
"""
CBF Robot - One-Time Credential Setup
Run this script once to securely save your API keys.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config_manager import ConfigManager, KEY_ANTHROPIC_API
import getpass


def main():
    """Interactive credential setup."""
    print("\n" + "="*60)
    print("  CBF Robot - Credential Setup")
    print("="*60)
    print()

    # Test if keyring is available
    test_manager = ConfigManager(use_encrypted_config=False)
    has_keyring = test_manager._has_keyring

    if has_keyring:
        print("✓ OS Keyring detected (recommended)")
        print("  • Windows: Credential Manager")
        print("  • macOS: Keychain")
        print("  • Linux: Secret Service API")
        print()
        use_encrypted = input("Use encrypted config file instead? (y/N): ").lower() == 'y'
    else:
        print("⚠️  OS Keyring not available (admin restrictions?)")
        print("  → Using encrypted config file instead")
        print()
        use_encrypted = True

    print()

    # Initialize manager with appropriate backend
    config_password = None
    if use_encrypted:
        print("📝 Encrypted config file will be stored at:")
        print(f"   {Path.home() / '.cbf_robot_config'}")
        print()
        print("💡 This file can sync via OneDrive/Google Drive!")
        print()
        config_password = getpass.getpass("Enter encryption password (hidden): ").strip()
        if not config_password:
            print("\n✗ No password entered. Using default encryption.")
            config_password = "cbf_robot_default"  # Fallback

        # Confirm password
        confirm_password = getpass.getpass("Confirm password (hidden): ").strip()
        if config_password != confirm_password:
            print("\n✗ Passwords don't match. Setup cancelled.")
            return

    manager = ConfigManager(use_encrypted_config=use_encrypted, config_password=config_password)

    print()
    print("="*60)
    print("✓ You only need to do this ONCE")
    print("✓ Credentials persist across sessions")
    print("✓ No .env file needed")
    if use_encrypted:
        print("✓ Works on restricted machines (no admin rights needed)")
    print("✓ Secure (encrypted)")
    print()
    print("="*60)
    print()

    # Check if already configured
    existing_key = manager.get_anthropic_key()
    if existing_key:
        print(f"✓ Anthropic API Key is already configured")
        print(f"  (starts with: {existing_key[:10]}...)")
        print()
        update = input("Do you want to update it? (y/N): ").lower() == 'y'
        print()
    else:
        update = True

    if update:
        print("📝 Please enter your Anthropic Claude API Key")
        print("   Get it from: https://console.anthropic.com/")
        print()
        api_key = getpass.getpass("API Key (hidden): ").strip()

        if not api_key:
            print("\n✗ No API key entered. Setup cancelled.")
            return

        # Validate key format
        if not api_key.startswith('sk-ant-'):
            print("\n⚠️  Warning: API key doesn't match expected format (sk-ant-...)")
            confirm = input("   Continue anyway? (y/N): ").lower() == 'y'
            if not confirm:
                print("\n✗ Setup cancelled.")
                return

        # Save to keyring
        print("\n💾 Saving to OS keyring...")
        if manager.set_credential(KEY_ANTHROPIC_API, api_key, persist=True):
            print("✓ API Key saved successfully!")
            print()
            print("="*60)
            print("  🎉 Setup Complete!")
            print("="*60)
            print()
            print("You can now run CBF Robot:")
            print("  python src/main.py")
            print()
            print("The API key will load automatically every time.")
            print()
        else:
            print("✗ Failed to save API key to keyring.")
            print("  Your OS keyring may not be available.")
            print("  Fallback: Create a .env file with ANTHROPIC_API_KEY")

    # Show current status
    print("\n" + "="*60)
    print("  Current Configuration")
    print("="*60)
    print()
    creds = manager.list_credentials()
    for name, available in creds.items():
        status = "✓ SET" if available else "✗ NOT SET"
        print(f"  {status}  {name}")
    print()

    if not any(creds.values()):
        print("⚠️  No credentials configured!")
        print("   Run this script again to set up.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
