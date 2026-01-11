#!/usr/bin/env python3
"""
Helper script to obtain Keycloak access tokens for testing.

Usage:
    python scripts/get_token.py <username> <password>
    python scripts/get_token.py acika 12345

Options:
    --json: Output full token response as JSON
    --refresh: Also display refresh token
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.managers.keycloak_manager import KeycloakManager


def get_token(username: str, password: str, show_json: bool = False):
    """
    Get access token from Keycloak for given credentials.

    Args:
        username (str): Keycloak username
        password (str): Keycloak password
        show_json (bool): If True, output full JSON response

    Returns:
        dict: Token response from Keycloak
    """
    try:
        kc_manager = KeycloakManager()
        token_response = kc_manager.login(username, password)

        if show_json:
            print(json.dumps(token_response, indent=2))
        else:
            print("\n=== Access Token ===")
            print(token_response["access_token"])
            print("\n=== Token Info ===")
            print(f"Expires in: {token_response.get('expires_in')} seconds")
            print(
                f"Refresh expires in: "
                f"{token_response.get('refresh_expires_in')} seconds"
            )

            # Decode and show user info
            user_data = kc_manager.openid.decode_token(
                token_response["access_token"]
            )
            print(f"\nUser: {user_data.get('preferred_username')}")
            print(f"Roles: {user_data.get('realm_access', {}).get('roles')}")

        return token_response

    except Exception as ex:
        print(f"Error: {ex}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Get Keycloak access token for testing"
    )
    parser.add_argument("username", help="Keycloak username")
    parser.add_argument("password", help="Keycloak password")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output full token response as JSON",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Also display refresh token",
    )

    args = parser.parse_args()

    token_response = get_token(args.username, args.password, args.json)

    if args.refresh and not args.json:
        print("\n=== Refresh Token ===")
        print(token_response["refresh_token"])


if __name__ == "__main__":
    main()
