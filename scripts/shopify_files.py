#!/usr/bin/env python3
"""
Shopify Files Management using Admin GraphQL API

Usage:
    python scripts/shopify_files.py list              # List all files
    python scripts/shopify_files.py pull [output_dir]  # Download all files (default: ./files)
    python scripts/shopify_files.py push [input_dir]    # Upload files (default: ./files)

Environment:
    - SHOPIFY_SHOP: Shop domain (e.g., turboship-uat.myshopify.com)
    - SHOPIFY_ACCESS_TOKEN: 1Password reference (op://...) or direct token
"""

import asyncio
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List, Dict, Any

API_VERSION = "2026-01"


def get_secret(token_ref: str) -> str:
    """Get secret from 1Password or return token directly."""
    if not token_ref.startswith("op://"):
        return token_ref

    import subprocess

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

    try:
        result = subprocess.run(
            ["op", "read", token_ref], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass

    print("Error: Could not resolve 1Password secret")
    sys.exit(1)


def load_env():
    """Load environment based on current git branch."""
    import subprocess

    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], text=True
        ).strip()
    except:
        branch = "unknown"

    env_file = None
    if branch == "main" and Path("prod.env").exists():
        env_file = "prod.env"
    elif branch == "uat" and Path("uat.env").exists():
        env_file = "uat.env"

    if env_file:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.replace("export ", "")
                    os.environ[key] = value.strip("\"'")

    return branch


class ShopifyFilesClient:
    """Client for Shopify Files GraphQL API operations."""

    def __init__(self, shop: str, token: str):
        self.shop = shop
        self.token = token
        self.endpoint = f"https://{shop}/admin/api/{API_VERSION}/graphql.json"

    def graphql(self, query: str, variables: dict = None) -> dict:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "X-Shopify-Access-Token": self.token,
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(self.endpoint, data=data, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            print(f"HTTP Error {e.code}: {error_body}")
            raise

    def list_files(self, media_type: str = None, limit: int = 250) -> List[Dict]:
        """List all files, optionally filtered by media type."""
        all_files = []
        cursor = None

        while True:
            query_filter = f"media_type:{media_type}" if media_type else None

            query = """
            query($first: Int!, $after: String, $query: String) {
                files(first: $first, after: $after, query: $query) {
                    edges {
                        cursor
                        node {
                            id
                            alt
                            ... on MediaImage {
                                createdAt
                                image {
                                    url
                                    width
                                    height
                                }
                            }
                            ... on GenericFile {
                                createdAt
                                url
                            }
                            ... on Video {
                                createdAt
                                duration
                                sources {
                                    url
                                    format
                                    mimeType
                                }
                            }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
            """

            variables = {"first": limit}
            if query_filter:
                variables["query"] = query_filter
            if cursor:
                variables["after"] = cursor

            result = self.graphql(query, variables)

            if "errors" in result:
                print(f"GraphQL errors: {result['errors']}")
                break

            files_data = result.get("data", {}).get("files", {})
            edges = files_data.get("edges", [])

            for edge in edges:
                all_files.append(edge["node"])

            page_info = files_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")

        return all_files

    def download_file(self, url: str, output_path: Path) -> bool:
        """Download a file from URL to local path."""
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(content)
            return True
        except Exception as e:
            print(f"    Error downloading {url}: {e}")
            return False

    def staged_upload_create(
        self, filename: str, mime_type: str, resource: str = "FILE"
    ) -> dict:
        """Create a staged upload URL for file upload."""
        query = """
        mutation($input: [StagedUploadInput!]!) {
            stagedUploadsCreate(input: $input) {
                stagedTargets {
                    url
                    resource
                    parameters {
                        name
                        value
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        variables = {
            "input": [
                {
                    "filename": filename,
                    "mimeType": mime_type,
                    "resource": resource,
                }
            ]
        }

        result = self.graphql(query, variables)

        if "errors" in result:
            print(f"GraphQL errors: {result['errors']}")
            return None

        staged_data = result.get("data", {}).get("stagedUploadsCreate", {})
        user_errors = staged_data.get("userErrors", [])

        if user_errors:
            for error in user_errors:
                print(f"Error: {error['field']}: {error['message']}")
            return None

        targets = staged_data.get("stagedTargets", [])
        if targets:
            return targets[0]

        return None

    def file_create_from_staged_upload(
        self, staged_upload: dict, alt: str = None
    ) -> dict:
        """Create a file from a staged upload."""
        query = """
        mutation($files: [FileCreateInput!]!) {
            fileCreate(files: $files) {
                files {
                    id
                    alt
                    ... on MediaImage {
                        image {
                            url
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        file_input = {
            "originalSource": {
                "source": "STAGED_UPLOAD",
                "stagedUploadUrl": staged_upload["url"],
            }
        }

        if alt:
            file_input["alt"] = alt

        variables = {"files": [file_input]}

        result = self.graphql(query, variables)

        if "errors" in result:
            print(f"GraphQL errors: {result['errors']}")
            return None

        create_data = result.get("data", {}).get("fileCreate", {})
        user_errors = create_data.get("userErrors", [])

        if user_errors:
            for error in user_errors:
                print(f"Error: {error['field']}: {error['message']}")
            return None

        files = create_data.get("files", [])
        if files:
            return files[0]

        return None

    def upload_file(self, file_path: Path, alt: str = None) -> bool:
        """Upload a file to Shopify."""
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
            ".pdf": "application/pdf",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
        }

        ext = file_path.suffix.lower()
        mime_type = mime_types.get(ext, "application/octet-stream")

        staged_upload = self.staged_upload_create(file_path.name, mime_type)
        if not staged_upload:
            return False

        upload_url = staged_upload["url"]
        params = {p["name"]: p["value"] for p in staged_upload.get("parameters", [])}

        try:
            file_content = file_path.read_bytes()

            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            parts = []

            for name, value in params.items():
                parts.append(
                    f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}'
                )

            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
                f"Content-Type: {mime_type}\r\n\r\n"
            )

            body = (
                "\r\n".join(parts).encode("utf-8")
                + file_content
                + f"\r\n--{boundary}--\r\n".encode("utf-8")
            )

            req = urllib.request.Request(
                upload_url,
                data=body,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status >= 400:
                    print(f"    Upload failed: {response.status}")
                    return False

            result = self.file_create_from_staged_upload(staged_upload, alt)
            return result is not None

        except Exception as e:
            print(f"    Error uploading {file_path}: {e}")
            return False


def cmd_list(client: ShopifyFilesClient, media_type: str = None):
    """List all files."""
    type_filter = f" ({media_type})" if media_type else ""
    print(f"Listing files{type_filter} in {client.shop}...\n")

    files = client.list_files(media_type=media_type)

    images = []
    videos = []
    generic = []

    for f in files:
        file_type = f.get("__typename", "Unknown")
        if file_type == "MediaImage" or "image" in f:
            images.append(f)
        elif file_type == "Video" or "sources" in f:
            videos.append(f)
        else:
            generic.append(f)

    if images:
        print(f"Images ({len(images)}):")
        for img in images:
            url = img.get("image", {}).get("url", "N/A")
            alt = img.get("alt", "")
            print(f"  - {img.get('id', 'unknown')}: {alt[:50] if alt else 'no alt'}")
            print(f"    {url}")

    if videos:
        print(f"\nVideos ({len(videos)}):")
        for vid in videos:
            duration = vid.get("duration", 0)
            print(f"  - {vid.get('id', 'unknown')}: {duration}s")

    if generic:
        print(f"\nGeneric Files ({len(generic)}):")
        for gf in generic:
            url = gf.get("url", "N/A")
            print(f"  - {gf.get('id', 'unknown')}: {url}")

    print(f"\nTotal: {len(files)} files")


def cmd_pull(
    client: ShopifyFilesClient, output_dir: str = "files", media_type: str = "IMAGE"
):
    """Pull files from Shopify."""
    print(f"Pulling files from {client.shop} to {output_dir}/...\n")

    files = client.list_files(media_type=media_type)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    failed = 0

    for f in files:
        file_id = f.get("id", "unknown")

        if "image" in f:
            url = f["image"].get("url", "")
            filename = url.split("/")[-1].split("?")[0]
        elif "url" in f:
            url = f["url"]
            filename = url.split("/")[-1].split("?")[0]
        else:
            print(f"  Skipping {file_id}: no download URL")
            continue

        if not filename:
            filename = f"file_{file_id.split('/')[-1]}"

        if not any(
            filename.endswith(ext)
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]
        ):
            filename += ".jpg"

        print(f"  Downloading {filename}...")
        dest_path = output_path / filename

        if client.download_file(url, dest_path):
            downloaded += 1
        else:
            failed += 1

    print(f"\nDownloaded: {downloaded}, Failed: {failed}")


def cmd_push(client: ShopifyFilesClient, input_dir: str = "files"):
    """Push files to Shopify."""
    print(f"Pushing files from {input_dir}/ to {client.shop}...\n")

    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: Directory {input_dir} does not exist")
        sys.exit(1)

    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]
    files = []
    for ext in image_extensions:
        files.extend(input_path.glob(f"*{ext}"))
        files.extend(input_path.glob(f"**/*{ext}"))

    uploaded = 0
    failed = 0

    for file_path in files:
        print(f"  Uploading {file_path.name}...")

        if client.upload_file(file_path):
            uploaded += 1
        else:
            failed += 1

    print(f"\nUploaded: {uploaded}, Failed: {failed}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/shopify_files.py <command> [args]")
        print("")
        print("Commands:")
        print("  list                    List all files")
        print("  list IMAGE              List only images")
        print("  pull [output_dir]       Download all images (default: ./files)")
        print("  push [input_dir]        Upload files (default: ./files)")
        sys.exit(1)

    command = sys.argv[1]

    branch = load_env()

    shop = os.environ.get("SHOPIFY_SHOP")
    token_ref = os.environ.get("SHOPIFY_ACCESS_TOKEN")

    if not shop:
        print(f"Error: SHOPIFY_SHOP not set (branch: {branch})")
        sys.exit(1)

    if not token_ref:
        print(f"Error: SHOPIFY_ACCESS_TOKEN not set (branch: {branch})")
        sys.exit(1)

    print(f"Environment: {branch}")
    print(f"Shop: {shop}")
    print("")

    print("Resolving Shopify access token...")
    token = get_secret(token_ref)

    client = ShopifyFilesClient(shop, token)

    if command == "list":
        media_type = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_list(client, media_type)

    elif command == "pull":
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "files"
        media_type = sys.argv[3] if len(sys.argv) > 3 else "IMAGE"
        cmd_pull(client, output_dir, media_type)

    elif command == "push":
        input_dir = sys.argv[2] if len(sys.argv) > 2 else "files"
        cmd_push(client, input_dir)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
