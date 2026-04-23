#!/usr/bin/env python3
"""
List Shopify themes with their roles to identify the live theme.

Usage:
    python scripts/list_themes.py [--shop turboship-uat.myshopify.com]

Environment:
    - SHOPIFY_SHOP: Shop domain (overridden by --shop flag)
    - SHOPIFY_ACCESS_TOKEN: 1Password reference (op://...) or direct token
"""

import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path


def get_secret(token_ref: str) -> str:
    """Get secret from 1Password or return token directly."""
    if not token_ref.startswith("op://"):
        return token_ref

    windows_op = "/mnt/c/Program Files/1Password CLI/op.exe"
    if Path(windows_op).exists():
        try:
            result = subprocess.run(
                [windows_op, "read", token_ref],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

    print("Error: Could not resolve 1Password secret")
    sys.exit(1)


def list_themes(shop: str, token: str) -> list:
    """Query GraphQL API to list all themes with roles."""
    query = """
    {
      themes(first: 50) {
        edges {
          node {
            id
            name
            role
          }
        }
      }
    }
    """

    base_url = f"https://{shop}/admin/api/2026-01/graphql.json"
    data = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        base_url,
        data=data,
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        print("GraphQL Errors:", json.dumps(result["errors"], indent=2))
        return []

    return result.get("data", {}).get("themes", {}).get("edges", [])


def main():
    parser = argparse.ArgumentParser(description="List Shopify themes with roles")
    parser.add_argument(
        "--shop", help="Shop domain (e.g., turboship-uat.myshopify.com)"
    )
    parser.add_argument("--token-ref", help="1Password reference for token")
    args = parser.parse_args()

    # Determine shop
    shop = args.shop
    if not shop:
        # Check environment
        env_override = os.environ.get("SHOPIFY_ENV")
        if env_override:
            branch = env_override
        else:
            try:
                branch = subprocess.check_output(
                    ["git", "branch", "--show-current"], text=True
                ).strip()
            except:
                branch = "unknown"

        # Load env file
        env_file = None
        if branch in ("main", "prod") and Path("prod.env").exists():
            env_file = "prod.env"
        elif branch == "uat" and Path("uat.env").exists():
            env_file = "uat.env"

        if env_file:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key] = value.strip("\"'")

        shop = os.environ.get("SHOPIFY_SHOP")

    if not shop:
        print("Error: No shop specified. Use --shop flag or set SHOPIFY_SHOP")
        return

    # Get token - use appropriate token based on shop domain
    token_ref = args.token_ref
    if not token_ref:
        if "turboship-uat" in shop:
            token_ref = "op://Private/Shopify_UAT_Admin/Admin_API_access_token"
        elif "turbo-heat-welding" in shop:
            token_ref = "op://TurboHeatWelding/SHOPIFY_API_KEY/Turboship_app_Admin_API_secret_token"
        else:
            token_ref = os.environ.get("SHOPIFY_ACCESS_TOKEN")

    if not token_ref:
        print("Error: No token specified. Use --token-ref or set SHOPIFY_ACCESS_TOKEN")
        return

    print(f"Shop: {shop}")
    print()

    token = get_secret(token_ref)
    themes = list_themes(shop, token)

    print("THEMES:")
    print("=" * 70)
    for edge in themes:
        node = edge["node"]
        theme_id = node["id"].split("/")[-1]
        role = node["role"]
        name = node["name"]

        if role == "main":
            marker = " ← *** LIVE ***"
        elif role == "development":
            marker = " (development)"
        else:
            marker = ""

        print(f"{theme_id}: {name} [{role}]{marker}")


if __name__ == "__main__":
    import sys

    main()
