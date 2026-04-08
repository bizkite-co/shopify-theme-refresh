#!/usr/bin/env bash
.PHONY: help
help: ## Display this help screen
	@echo "Available commands:"
	@echo ""
	@echo "  Environment:"
	@echo "    env-info           Show current environment info (auto-detects based on branch)"
	@echo ""
	@echo "  Theme Operations:"
	@echo "    pull               Pull theme from current environment (auto-detects based on branch)"
	@echo "    push               Push theme to current environment (auto-detects based on branch)"
	@echo "    push-unpublished   Push as new unpublished theme (prompts for name)"
	@echo "    publish            Publish current theme to make it live"
	@echo ""
	@echo "  Page Operations:"
	@echo "    create-page        Create a Shopify page (usage: make create-page TITLE=\"x\" HANDLE=\"x\" TEMPLATE=\"x\")"
	@echo "    create-address-update-page  Create the invalid address update page"
	@echo ""
	@echo "  Git Operations:"
	@echo "    branch-status      Show git status and current branch"

# ==============================================================================
# Environment Info
# ==============================================================================

env-info: ## Show current environment info (auto-detects based on branch)
	@bash -c 'source <(direnv export bash 2>/dev/null) && echo "Current branch: $$(git branch --show-current)" && echo "SHOPIFY_SHOP: $${SHOPIFY_SHOP:-<not set>}" && echo "SHOPIFY_THEME_ID: $${SHOPIFY_THEME_ID:-<not set>}"'

# ==============================================================================
# Theme Operations (auto-detect environment based on branch)
# ==============================================================================

pull: ## Pull theme from current environment (auto-detects based on branch)
	@bash -c 'source <(direnv export bash 2>/dev/null) && echo "Pulling from $$SHOPIFY_SHOP..." && npx shopify theme pull --store=$$SHOPIFY_SHOP'

push: ## Push theme to current environment (auto-detects based on branch)
	@bash -c 'source <(direnv export bash 2>/dev/null) && echo "Pushing to $$SHOPIFY_SHOP (theme: $$SHOPIFY_THEME_ID)..." && npx shopify theme push --store=$$SHOPIFY_SHOP --theme=$$SHOPIFY_THEME_ID'

push-unpublished: ## Push as new unpublished theme (prompts for name)
	@bash -c 'source <(direnv export bash 2>/dev/null) && echo "Pushing as new unpublished theme to $$SHOPIFY_SHOP..." && npx shopify theme push --store=$$SHOPIFY_SHOP --unpublished'

push-named: ## Push as new unpublished theme with name (usage: make push-named NAME="my-theme")
	@bash -c 'source <(direnv export bash 2>/dev/null) && echo "Pushing as $$NAME to $$SHOPIFY_SHOP..." && npx shopify theme push --store=$$SHOPIFY_SHOP --unpublished --name="$${NAME:-preview-theme}"'

publish: ## Publish current theme to make it live
	@bash -c 'source <(direnv export bash 2>/dev/null) && echo "Publishing theme on $$SHOPIFY_SHOP..." && npx shopify theme publish --store=$$SHOPIFY_SHOP'

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

.PHONY: help env-info pull push push-unpublished push-named publish create-page create-address-update-page branch-status