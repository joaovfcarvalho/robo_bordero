#!/usr/bin/env python3
"""
Dashboard Connection Test
Run this to verify Supabase connection before deploying
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    """Test Supabase database connection."""
    print("\n" + "="*60)
    print("DASHBOARD CONNECTION TEST")
    print("="*60)

    # Step 1: Check environment variables
    print("\n1. Checking environment variables...")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url:
        print("   ✗ SUPABASE_URL not found!")
        return False
    else:
        print(f"   ✓ SUPABASE_URL: {supabase_url[:30]}...")

    if not supabase_key:
        print("   ✗ SUPABASE_KEY not found!")
        return False
    else:
        print(f"   ✓ SUPABASE_KEY: {supabase_key[:20]}...")

    # Step 2: Test database connection
    print("\n2. Testing Supabase database connection...")

    try:
        from src.database import get_database_client

        db = get_database_client()
        print("   ✓ Database client initialized")

        # Try to query (will work even with empty database)
        matches = db.get_all_matches(limit=5)
        print(f"   ✓ Database query successful! Found {len(matches)} matches")

        if len(matches) == 0:
            print("\n   ⚠️  Database is EMPTY - no matches found")
            print("   → This is why your dashboard is blank!")
            print("   → Run test_manual_run.py to add some data")
        else:
            print(f"\n   ✓ Found {len(matches)} matches in database")
            print("\n   Sample match:")
            if matches:
                match = matches[0]
                print(f"     - ID: {match.get('id_jogo_cbf')}")
                print(f"     - Teams: {match.get('time_mandante')} vs {match.get('time_visitante')}")
                print(f"     - Date: {match.get('data_jogo')}")

        return True

    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        print("\n   Possible issues:")
        print("   - SUPABASE_URL or SUPABASE_KEY incorrect")
        print("   - Database schema not created yet")
        print("   - Network/firewall issue")
        return False

    # Step 3: Test storage connection
    print("\n3. Testing Supabase storage connection...")

    try:
        from src.storage import get_storage_client

        storage = get_storage_client()
        print("   ✓ Storage client initialized")

        pdfs = storage.list_pdfs()
        print(f"   ✓ Storage query successful! Found {len(pdfs)} PDFs")

        if len(pdfs) == 0:
            print("   → No PDFs in storage yet (this is OK for initial setup)")

        return True

    except Exception as e:
        print(f"   ✗ Storage connection failed: {e}")
        return False


if __name__ == "__main__":
    print("\nThis script tests your Supabase connection")
    print("Make sure you have:")
    print("  1. Created Supabase project")
    print("  2. Run migrations/001_initial_schema.sql")
    print("  3. Set SUPABASE_URL and SUPABASE_KEY in .env")

    success = test_connection()

    print("\n" + "="*60)
    if success:
        print("✓ CONNECTION TEST PASSED")
        print("\nNext steps:")
        print("  1. Run: python test_manual_run.py --max-pdfs 3")
        print("  2. Then run: streamlit run src/dashboard.py")
        print("  3. Dashboard should show your 3 test matches!")
    else:
        print("✗ CONNECTION TEST FAILED")
        print("\nPlease fix the issues above before deploying")
    print("="*60 + "\n")
