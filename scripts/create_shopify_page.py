#!/usr/bin/env python3
"""
Shopify Page Creator with 1Password Integration

Usage:
    python scripts/create_shopify_page.py "Page Title" page-handle page-template
    python scripts/create_shopify_page.py "Invalid Address Update" order-address-update order-address-update

Environment:
    - SHOPIFY_SHOP: Shop domain (e.g., turboship-uat.myshopify.com)
    - SHOPIFY_ACCESS_TOKEN: 1Password reference (op://vault/item/field) or direct token
"""

import asyncio
import os
import sys
import requests
from onepassword.client import Client, DesktopAuth


def get_secret(token_ref: str) -> str:
    """Get secret from 1Password or return token directly if not a reference."""
    if not token_ref.startswith("op://"):
        return token_ref
    
    # Check for service account token first
    service_token = os.environ.get("OP_SERVICE_ACCOUNT_TOKEN")
    if service_token:
        async def resolve_with_service():
            client = await Client.authenticate(
                auth=service_token,
                integration_name="shopify-theme-deploy",
                integration_version="1.0.0"
            )
            return await client.secrets.resolve(token_ref)
        return asyncio.run(resolve_with_service())
    
    # Try Windows op.exe via subprocess
    import subprocess
    windows_op = "/mnt/c/Program Files/1Password CLI/op.exe"
    if os.path.exists(windows_op):
        try:
            result = subprocess.run(
                [windows_op, "read", token_ref],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
    
    # Try desktop auth (for local development with Windows Hello)
    try:
        async def resolve_desktop():
            client = await Client.authenticate(
                auth=DesktopAuth(account_name="my"),
                integration_name="shopify-theme-deploy",
                integration_version="1.0.0"
            )
            return await client.secrets.resolve(token_ref)
        return asyncio.run(resolve_desktop())
    except FileNotFoundError:
        print("Error: Could not resolve 1Password secret.")
        print("Options:")
        print("  1. Set OP_SERVICE_ACCOUNT_TOKEN environment variable")
        print("  2. Ensure 1Password desktop app is running with CLI integration enabled")
        print("  3. Use direct token instead of op:// reference in your .env file")
        sys.exit(1)


def create_shopify_page(shop: str, title: str, handle: str, template_suffix: str, token: str) -> dict:
    """Create a page in Shopify via REST API."""
    url = f"https://{shop}/admin/api/2026-01/pages.json"
    
    payload = {
        "page": {
            "title": title,
            "handle": handle,
            "template_suffix": template_suffix
        }
    }
    
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def load_env():
    """Load environment based on current git branch."""
    import subprocess
    
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            text=True
        ).strip()
    except:
        branch = "unknown"
    
    env_file = None
    if branch == "main" and os.path.exists("prod.env"):
        env_file = "prod.env"
    elif branch == "uat" and os.path.exists("uat.env"):
        env_file = "uat.env"
    
    if env_file:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
    
    return branch


def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts/create_shopify_page.py <title> <handle> <template_suffix> [body_html]")
        print("Example: python scripts/create_shopify_page.py 'Invalid Address Update' order-address-update order-address-update")
        sys.exit(1)
    
    title = sys.argv[1]
    handle = sys.argv[2]
    template_suffix = sys.argv[3]
    
    branch = load_env()
    
    shop = os.environ.get("SHOPIFY_SHOP")
    token_ref = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    
    if not shop:
        print(f"Error: SHOPIFY_SHOP not set (branch: {branch})")
        sys.exit(1)
    
    if not token_ref:
        print(f"Error: SHOPIFY_ACCESS_TOKEN not set (branch: {branch})")
        sys.exit(1)
    
    print(f"Creating page in {shop}...")
    print(f"  Title: {title}")
    print(f"  Handle: {handle}")
    print(f"  Template: {template_suffix}")
    
    # Get token from 1Password if needed
    print("Resolving 1Password reference...")
    token = get_secret(token_ref)
    
    # Create page
    result = create_shopify_page(shop, title, handle, template_suffix, token)
    
    page = result["page"]
    page_url = f"https://{shop}/pages/{handle}"
    
    print(f"\nSuccess! Page created:")
    print(f"  ID: {page['id']}")
    print(f"  URL: {page_url}")


if __name__ == "__main__":
    main()
