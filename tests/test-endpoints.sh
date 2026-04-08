#!/bin/bash
# Simple HTTP tests using curl
# Usage: ./tests/test-endpoints.sh [env]
# Example: ./tests/test-endpoints.sh prod

ENV="${1:-uat}"
SHOP=""
THEME_ID=""
BASE_URL=""

case "$ENV" in
    prod)
        SHOP="turbo-heat-welding-tools.myshopify.com"
        # Can add theme preview support
        ;;
    uat)
        SHOP="turboship-uat.myshopify.com"
        ;;
    *)
        echo "Unknown environment: $ENV"
        exit 1
        ;;
esac

BASE_URL="https://$SHOP"
PASS=0
FAIL=0

echo "=== Testing $ENV environment: $BASE_URL ==="
echo ""

test_endpoint() {
    local path="$1"
    local expected_contains="$2"
    local url="$BASE_URL$path"
    
    echo -n "Testing $path... "
    
    # Get status and content (follow redirects)
    response=$(curl -s -w "\n%{http_code}" -L "$url" 2>/dev/null)
    status=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status" = "200" ]; then
        if [ -n "$expected_contains" ]; then
            if echo "$body" | grep -q "$expected_contains"; then
                echo "✓ PASS (200, contains '$expected_contains')"
                ((PASS++))
            else
                echo "✗ FAIL (200, but missing '$expected_contains')"
                ((FAIL++))
            fi
        else
            echo "✓ PASS (200)"
            ((PASS++))
        fi
    else
        echo "✗ FAIL (HTTP $status)"
        ((FAIL++))
    fi
}

# Test basic pages
test_endpoint "/" "Turbo"
test_endpoint "/collections/all" "Products"
test_endpoint "/cart" "Cart"
test_endpoint "/pages/order-address-update" "Order"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ $FAIL -gt 0 ]; then
    exit 1
fi
exit 0