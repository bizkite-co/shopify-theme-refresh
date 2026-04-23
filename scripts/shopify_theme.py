#!/usr/bin/env python3
"""
Shopify Theme Management using Admin API

Usage:
    python scripts/shopify_theme.py list                    # List all themes
    python scripts/shopify_theme.py pull                    # Pull current theme files
    python scripts/shopify_theme.py push                    # Push files to current theme
    python scripts/shopify_theme.py put <file> [theme_id]  # Push single file to theme
    python scripts/shopify_theme.py create "My Theme"       # Create new unpublished theme
    python scripts/shopify_theme.py duplicate 123 "Name"    # Duplicate existing theme

Environment:
    - SHOPIFY_SHOP: Shop domain (e.g., turboship-uat.myshopify.com)
    - SHOPIFY_ACCESS_TOKEN: 1Password reference (op://...) or direct token
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional
import requests


# Shopify API version
API_VERSION = "2026-01"


def get_secret(token_ref: str) -> str:
    """Get secret from 1Password or return token directly."""
    if not token_ref.startswith("op://"):
        return token_ref

    import subprocess

    # Try Windows op.exe via subprocess
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
        except:
            pass

    # Try Linux op
    try:
        import onepassword.client
        from onepassword.client import Client, DesktopAuth

        async def resolve():
            service_token = os.environ.get("OP_SERVICE_ACCOUNT_TOKEN")
            if service_token:
                client = await Client.authenticate(
                    auth=service_token,
                    integration_name="shopify-theme-deploy",
                    integration_version="1.0.0",
                )
            else:
                client = await Client.authenticate(
                    auth=DesktopAuth(account_name="my"),
                    integration_name="shopify-theme-deploy",
                    integration_version="1.0.0",
                )
            return await client.secrets.resolve(token_ref)

        return asyncio.run(resolve())
    except:
        pass

    # Try Linux op CLI
    try:
        result = subprocess.run(
            ["op", "read", token_ref], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass

    print("Error: Could not resolve 1Password secret")
    print("Options:")
    print("  1. Set OP_SERVICE_ACCOUNT_TOKEN environment variable")
    print("  2. Ensure 1Password desktop app is running with CLI integration")
    print("  3. Use direct token instead of op:// reference")
    sys.exit(1)


def load_env():
    """Load environment based on current git branch, or SHOPIFY_ENV override."""
    import subprocess

    # Allow override via environment variable
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
                    # Remove 'export ' prefix if present
                    key = key.replace("export ", "")
                    os.environ[key] = value.strip("\"'")

    return branch


class ShopifyThemeClient:
    """Client for Shopify Theme API operations."""

    def __init__(self, shop: str, token: str):
        self.shop = shop
        self.token = token
        self.base_url = f"https://{shop}/admin/api/{API_VERSION}"
        self.headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
        }

    def list_themes(self) -> list:
        """List all themes."""
        url = f"{self.base_url}/themes.json"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("themes", [])

    def get_theme(self, theme_id: int) -> dict:
        """Get a specific theme."""
        url = f"{self.base_url}/themes/{theme_id}.json"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("theme", {})

    def create_theme(self, name: str) -> dict:
        """Create a new theme."""
        url = f"{self.base_url}/themes.json"
        payload = {"theme": {"name": name}}
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json().get("theme", {})

    def duplicate_theme(self, source_theme_id: int, name: str) -> dict:
        """Duplicate an existing theme."""
        import urllib.request
        import json

        query = """
        mutation themeDuplicate($id: ID!, $name: String) {
            themeDuplicate(id: $id, name: $name) {
                newTheme {
                    id
                    name
                    role
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        variables = {
            "id": f"gid://shopify/OnlineStoreTheme/{source_theme_id}",
            "name": name,
        }

        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        url = f"{self.base_url}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": self.token,
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        if "errors" in result:
            raise Exception(f"GraphQL errors: {result['errors']}")

        data = result.get("data", {}).get("themeDuplicate", {})
        user_errors = data.get("userErrors", [])
        if user_errors:
            raise Exception(f"User errors: {user_errors}")

        theme = data.get("newTheme", {})
        return {
            "id": theme.get("id", "").split("/")[-1],
            "name": theme.get("name"),
            "role": theme.get("role"),
        }

    def list_assets(self, theme_id: int) -> list:
        """List all assets in a theme."""
        url = f"{self.base_url}/themes/{theme_id}/assets.json"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("assets", [])

    def get_asset(self, theme_id: int, key: str) -> dict:
        """Get a specific asset."""
        url = f"{self.base_url}/themes/{theme_id}/assets.json"
        params = {"asset[key]": key}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get("asset", {})

    def put_asset(
        self, theme_id: int, key: str, content: str = None, attachment: str = None
    ) -> dict:
        """Create or update an asset."""
        url = f"{self.base_url}/themes/{theme_id}/assets.json"
        payload = {"asset": {"key": key}}
        if content:
            payload["asset"]["value"] = content
        elif attachment:
            payload["asset"]["attachment"] = attachment

        response = requests.put(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json().get("asset", {})

    def delete_asset(self, theme_id: int, key: str) -> bool:
        """Delete an asset."""
        url = f"{self.base_url}/themes/{theme_id}/assets.json"
        params = {"asset[key]": key}
        response = requests.delete(url, headers=self.headers, params=params)
        return response.status_code == 200


def cmd_list_themes(client: ShopifyThemeClient):
    """List all themes."""
    print(f"Listing themes in {client.shop}...\n")
    themes = client.list_themes()

    for theme in themes:
        role = theme.get("role", "unpublished")
        name = theme.get("name", "Unnamed")
        theme_id = theme.get("id", "?")
        status = f" [{role}]" if role != "unpublished" else ""
        print(f"  {theme_id}: {name}{status}")


def cmd_pull(client: ShopifyThemeClient, theme_id: int, output_dir: str = "."):
    """Pull theme files from Shopify."""
    print(f"Pulling theme {theme_id} from {client.shop}...\n")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # List all assets
    assets = client.list_assets(theme_id)

    # Pull each asset
    for asset in assets:
        key = asset.get("key")
        if not key:
            continue

        print(f"  Pulling {key}...")
        try:
            asset_data = client.get_asset(theme_id, key)

            # Determine content type and write
            if "value" in asset_data:
                content = asset_data["value"]
                file_path = output_path / key
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
            elif "attachment" in asset_data:
                import base64

                content = base64.b64decode(asset_data["attachment"])
                file_path = output_path / key
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(content)
        except Exception as e:
            print(f"    Error: {e}")

    print(f"\nPulled {len(assets)} files to {output_dir}")


def cmd_push(client: ShopifyThemeClient, theme_id: int, input_dir: str = "."):
    """Push theme files to Shopify."""
    print(f"Pushing theme {theme_id} to {client.shop}...\n")

    input_path = Path(input_dir)

    # Find all theme files
    extensions = [".liquid", ".json", ".css", ".js", ".svg", ".png", ".jpg", ".gif"]
    files = []
    for ext in extensions:
        files.extend(input_path.rglob(f"*{ext}"))

    # Push each file
    import base64

    for file_path in files:
        # Get relative path
        key = str(file_path.relative_to(input_path))
        print(f"  Pushing {key}...")

        try:
            # Determine if binary or text
            if file_path.suffix in [".png", ".jpg", ".gif", ".ico"]:
                content = base64.b64encode(file_path.read_bytes()).decode()
                client.put_asset(theme_id, key, attachment=content)
            else:
                content = file_path.read_text()
                client.put_asset(theme_id, key, content=content)
        except Exception as e:
            print(f"    Error: {e}")

    print(f"\nPushed {len(files)} files")


def cmd_create(client: ShopifyThemeClient, name: str):
    """Create a new unpublished theme."""
    print(f"Creating theme '{name}' in {client.shop}...\n")

    theme = client.create_theme(name)
    theme_id = theme.get("id")
    theme_name = theme.get("name")

    print(f"Created theme:")
    print(f"  ID: {theme_id}")
    print(f"  Name: {theme_name}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/shopify_theme.py <command> [args]")
        print("")
        print("Commands:")
        print("  list                          List all themes")
        print(
            "  pull [theme_id] [output_dir]  Pull theme files (default: theme_id from env)"
        )
        print(
            "  push [theme_id] [input_dir]   Push theme files (default: theme_id from env)"
        )
        print("  create <name>                  Create new unpublished theme")
        print("  duplicate <source_id> <name>  Duplicate an existing theme")
        sys.exit(1)

    command = sys.argv[1]

    # Load environment
    branch = load_env()

    shop = os.environ.get("SHOPIFY_SHOP")
    token_ref = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    theme_id = os.environ.get("SHOPIFY_THEME_ID")

    if not shop:
        print(f"Error: SHOPIFY_SHOP not set (branch: {branch})")
        sys.exit(1)

    if not token_ref:
        print(f"Error: SHOPIFY_ACCESS_TOKEN not set (branch: {branch})")
        sys.exit(1)

    print(f"Environment: {branch}")
    print(f"Shop: {shop}")
    print("")

    # Resolve token
    print("Resolving Shopify access token...")
    token = get_secret(token_ref)

    # Create client
    client = ShopifyThemeClient(shop, token)

    # Execute command
    if command == "list":
        cmd_list_themes(client)

    elif command == "pull":
        tid = (
            int(sys.argv[2])
            if len(sys.argv) > 2
            else int(theme_id)
            if theme_id
            else None
        )
        if not tid:
            print("Error: No theme ID specified and SHOPIFY_THEME_ID not set")
            sys.exit(1)
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "."
        cmd_pull(client, tid, output_dir)

    elif command == "push":
        tid = (
            int(sys.argv[2])
            if len(sys.argv) > 2
            else int(theme_id)
            if theme_id
            else None
        )
        if not tid:
            print("Error: No theme ID specified and SHOPIFY_THEME_ID not set")
            sys.exit(1)
        input_dir = sys.argv[3] if len(sys.argv) > 3 else "."
        cmd_push(client, tid, input_dir)

    elif command == "create":
        if len(sys.argv) < 3:
            print("Error: Theme name required")
            print("Usage: python scripts/shopify_theme.py create <name>")
            sys.exit(1)
        name = sys.argv[2]
        cmd_create(client, name)

    elif command == "duplicate":
        if len(sys.argv) < 4:
            print("Error: Source theme ID and name required")
            print(
                "Usage: python scripts/shopify_theme.py duplicate <source_theme_id> <new_name>"
            )
            sys.exit(1)
        source_id = int(sys.argv[2])
        name = sys.argv[3]
        print(f"Duplicating theme {source_id} as '{name}'...\n")
        result = client.duplicate_theme(source_id, name)
        print(f"Created theme:")
        print(f"  ID: {result['id']}")
        print(f"  Name: {result['name']}")
        print(f"  Role: {result['role']}")

    elif command == "put":
        if len(sys.argv) < 3:
            print("Error: File path required")
            print("Usage: python scripts/shopify_theme.py put <file_path> [theme_id]")
            sys.exit(1)
        file_path = sys.argv[2]
        tid = (
            int(sys.argv[3])
            if len(sys.argv) > 3
            else int(theme_id)
            if theme_id
            else None
        )
        if not tid:
            print("Error: No theme ID specified and SHOPIFY_THEME_ID not set")
            sys.exit(1)

        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)

        print(f"Pushing {file_path} to theme {tid}...")

        if path.suffix in [".png", ".jpg", ".gif", ".ico"]:
            content = base64.b64encode(path.read_bytes()).decode()
            client.put_asset(tid, file_path, attachment=content)
        else:
            client.put_asset(tid, file_path, content=path.read_text())

        print(f"Pushed {file_path} successfully")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
