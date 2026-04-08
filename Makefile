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

# Override environment with: make ENV=prod list-themes
ENV := $(shell echo "${SHOPIFY_ENV}")

# ==============================================================================
# Theme Operations (Python SDK - no interactive login)
# ==============================================================================

list-themes: ## List all themes in current environment
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/shopify_theme.py list

pull: ## Pull theme files from current environment
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/shopify_theme.py pull

push: ## Push theme files to current environment
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/shopify_theme.py push

create-theme: ## Create new unpublished theme (usage: make create-theme NAME="My Theme")
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/shopify_theme.py create "$${NAME:-New Theme}"

duplicate-theme: ## Duplicate an existing theme (usage: make duplicate-theme SOURCE=125943676989 NAME="PROD-baseline")
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/shopify_theme.py duplicate "$${SOURCE}" "$${NAME:-Duplicate}"

snapshot: ## Create a snapshot of the current live theme (auto-names with date)
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/shopify_theme.py duplicate "$${SOURCE}" "PROD-snapshot-$$(date +%Y-%m-%d)"

publish: ## Publish current theme to make it live
	@echo "Publishing theme via Shopify CLI..."
	@bash -c 'source <(direnv export bash 2>/dev/null) && npx shopify theme publish --store=$$SHOPIFY_SHOP'

# ==============================================================================
# Files Operations (Shopify Files via GraphQL API)
# ==============================================================================

list-files: ## List all files (images, videos, etc.) in current environment
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/shopify_files.py list

pull-files: ## Pull all Shopify Files (images) from store to ./files/
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/shopify_files.py pull

push-files: ## Push local files from ./files/ to Shopify store
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/shopify_files.py push

# ==============================================================================
# Page Operations (Python script with 1Password SDK)
# ==============================================================================

create-page: ## Create a Shopify page (usage: make create-page TITLE="x" HANDLE="x" TEMPLATE="x")
	@SHOPIFY_ENV=$(ENV) mise exec -- python scripts/create_shopify_page.py "$${TITLE:-Page Title}" "$${HANDLE:-page-handle}" "$${TEMPLATE:-page}"

create-address-update-page: ## Create the invalid address update page
	@mise exec -- python scripts/create_shopify_page.py "Invalid Address Update" order-address-update order-address-update

# ==============================================================================
# Testing
# ==============================================================================

test-endpoints: ## Run simple curl tests (usage: make test-endpoints ENV=uat|prod)
	@bash tests/test-endpoints.sh $(ENV)

test: ## Run Playwright tests on UAT
	@SHOPIFY_ENV=uat npx playwright test --config=playwright.uat.config.ts

test:prod: ## Run Playwright tests against PROD
	@SHOPIFY_ENV=prod npx playwright test --config=playwright.prod.config.ts

test:uat: ## Run Playwright tests against UAT
	@SHOPIFY_ENV=uat npx playwright test --config=playwright.uat.config.ts

# ==============================================================================
# Git Operations
# ==============================================================================

branch-status: ## Show git status and current branch
	@echo "Current branch: $$(git branch --show-current)"
	@git status --short

.PHONY: help env-info list-themes pull push create-theme duplicate-theme publish list-files pull-files push-files create-page create-address-update-page branch-status
