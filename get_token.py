#!/usr/bin/env python3
"""
Helper script to get a fresh Keycloak access token.

Usage:
    python get_token.py
    python get_token.py USERNAME PASSWORD
"""
import sys
from app.managers.keycloak_manager import KeycloakManager

def get_token(username: str = "acika", password: str = None):
    """Get access token from Keycloak."""
    if password is None:
        password = input(f"Enter password for {username}: ")

    try:
        kc = KeycloakManager()
        token_response = kc.login(username, password)
        access_token = token_response["access_token"]

        print("\n" + "=" * 60)
        print("✅ Successfully obtained access token")
        print("=" * 60)
        print(f"\nAccess Token (copy this):\n{access_token}\n")
        print("=" * 60)
        print("\nTo test WebSocket:")
        print(f"  python test_protobuf_websocket.py both {access_token}")
        print("\nOr use in Postman URL:")
        print(f"  ws://localhost:8000/web?Authorization=Bearer%20{access_token}")
        print("=" * 60)

        return access_token

    except Exception as e:
        print(f"\n❌ Error getting token: {e}")
        print("\nMake sure:")
        print("  1. Keycloak is running (make start)")
        print("  2. Username and password are correct")
        print("  3. User exists in Keycloak realm 'HW-App'")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) == 3:
        username = sys.argv[1]
        password = sys.argv[2]
    elif len(sys.argv) == 2:
        username = sys.argv[1]
        password = None
    else:
        username = "acika"
        password = None

    get_token(username, password)
