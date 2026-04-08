#!/usr/bin/env bash
.PHONY: help
help: ## Display this help screen
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z_-]+:.*?## / {printf "  \033[32m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ==============================================================================
# Application Tasks
# ==============================================================================

# ==============================================================================
# Environment Info
# ==============================================================================

env-info: ## Show current environment info (auto-detects based on branch)
	@bash -c 'source <(direnv export bash 2>/dev/null) && echo "Current branch: $$(git branch --show-current)" && echo "SHOPIFY_SHOP: $${SHOPIFY_SHOP:-<not set>}" && echo "SHOPIFY_THEME_ID: $${SHOPIFY_THEME_ID:-<not set>}"'

# ==============================================================================
# Theme Operations (Python SDK - no interactive login)
# ==============================================================================

list-themes: ## List all themes in current environment
	@mise exec -- python scripts/shopify_theme.py list

pull: ## Pull theme files from current environment
	@mise exec -- python scripts/shopify_theme.py pull

push: ## Push theme files to current environment
	@mise exec -- python scripts/shopify_theme.py push

create-theme: ## Create new unpublished theme (usage: make create-theme NAME="My Theme")
	@mise exec -- python scripts/shopify_theme.py create "$${NAME:-New Theme}"

publish: ## Publish current theme to make it live
	@echo "Publishing theme via Shopify CLI..."
	@bash -c 'source <(direnv export bash 2>/dev/null) && npx shopify theme publish --store=$$SHOPIFY_SHOP'

# ==============================================================================
# Files Operations (Shopify Files via GraphQL API)
# ==============================================================================

list-files: ## List all files (images, videos, etc.) in current environment
	@mise exec -- python scripts/shopify_files.py list

pull-files: ## Pull all Shopify Files (images) from store to ./files/
	@mise exec -- python scripts/shopify_files.py pull

push-files: ## Push local files from ./files/ to Shopify store
	@mise exec -- python scripts/shopify_files.py push

# ==============================================================================
# Page Operations (Python script with 1Password SDK)
# ==============================================================================

create-page: ## Create a Shopify page (usage: make create-page TITLE="x" HANDLE="x" TEMPLATE="x")
	@mise exec -- python scripts/create_shopify_page.py "$${TITLE:-Page Title}" "$${HANDLE:-page-handle}" "$${TEMPLATE:-page}"

create-address-update-page: ## Create the invalid address update page
	@mise exec -- python scripts/create_shopify_page.py "Invalid Address Update" order-address-update order-address-update

# ==============================================================================
# Git Operations
# ==============================================================================

branch-status: ## Show git status and current branch
	@echo "Current branch: $$(git branch --show-current)"
	@git status --short

.PHONY: help env-info list-themes pull push create-theme publish list-files pull-files push-files create-page create-address-update-page branch-status
