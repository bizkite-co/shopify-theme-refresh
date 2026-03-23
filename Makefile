#!/usr/bin/env bash
.PHONY: help
help: ## Display this help screen
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z_-]+:.*?## / {printf "  \033[32m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ==============================================================================
# Environment Info
# ==============================================================================

env-info: ## Show current environment info (branch, shop, theme ID)
	@echo "Current branch: $$(git branch --show-current)"
	@echo "SHOPIFY_SHOP: $${SHOPIFY_SHOP:-<not set>}"
	@echo "SHOPIFY_THEME_ID: $${SHOPIFY_THEME_ID:-<not set>}"

# ==============================================================================
# Shopify Theme Operations
# ==============================================================================

pull-prod: ## Pull theme from PROD (requires main branch)
	@if [ "$$(git branch --show-current)" != "main" ]; then \
		echo "Error: Must be on main branch for PROD pull"; \
		exit 1; \
	fi
	@echo "Pulling from PROD ($$SHOPIFY_SHOP)..."
	shopify theme pull

pull-uat: ## Pull theme from UAT (requires uat branch)
	@if [ "$$(git branch --show-current)" != "uat" ]; then \
		echo "Error: Must be on uat branch for UAT pull"; \
		exit 1; \
	fi
	@echo "Pulling from UAT ($$SHOPIFY_SHOP)..."
	shopify theme pull

push: ## Push theme to current environment (based on branch)
	@echo "Pushing to $$SHOPIFY_SHOP (theme: $$SHOPIFY_THEME_ID)..."
	shopify theme push

push-unpublished: ## Push as a new unpublished theme
	@echo "Pushing as new unpublished theme to $$SHOPIFY_SHOP..."
	shopify theme push --unpublished

publish: ## Publish the current theme to make it live
	@echo "Publishing theme on $$SHOPIFY_SHOP..."
	shopify theme publish

# ==============================================================================
# Git Branch Operations
# ==============================================================================

branch-status: ## Show git status and current branch
	@echo "Current branch: $$(git branch --show-current)"
	@git status --short

# ==============================================================================
# Help
# ==============================================================================

.PHONY: env-info pull-prod pull-uat push push-unpublished publish branch-status
