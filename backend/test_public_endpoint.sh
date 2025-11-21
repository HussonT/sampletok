#!/bin/bash

# Test script for public sample endpoint (TPERS-465)
# This script validates the public endpoint implementation

echo "==================================="
echo "Public Sample Endpoint Test Suite"
echo "==================================="
echo ""

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000/api/v1}"
SAMPLE_ID="${SAMPLE_ID:-e1248719-5e8f-440f-a36b-06cf526dad27}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Get public sample without authentication
echo "Test 1: Get public sample without authentication"
echo "------------------------------------------------"
response=$(curl -s -w "\n%{http_code}" "${API_BASE_URL}/samples/${SAMPLE_ID}/public")
http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC}: HTTP 200 response received"

    # Verify response contains essential fields
    if echo "$body" | jq -e '.id' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}: Response contains sample ID"
    else
        echo -e "${RED}✗ FAIL${NC}: Response missing sample ID"
    fi

    # Verify only completed samples returned
    status=$(echo "$body" | jq -r '.status')
    if [ "$status" = "completed" ]; then
        echo -e "${GREEN}✓ PASS${NC}: Sample status is 'completed'"
    else
        echo -e "${RED}✗ FAIL${NC}: Sample status is not 'completed' (got: $status)"
    fi

    # Verify user-specific fields are null
    is_favorited=$(echo "$body" | jq -r '.is_favorited')
    is_downloaded=$(echo "$body" | jq -r '.is_downloaded')
    if [ "$is_favorited" = "null" ] && [ "$is_downloaded" = "null" ]; then
        echo -e "${GREEN}✓ PASS${NC}: User-specific fields are null (no authentication)"
    else
        echo -e "${RED}✗ FAIL${NC}: User-specific fields not null (is_favorited: $is_favorited, is_downloaded: $is_downloaded)"
    fi

    # Verify creator attribution included
    creator_username=$(echo "$body" | jq -r '.creator_username')
    if [ "$creator_username" != "null" ] && [ -n "$creator_username" ]; then
        echo -e "${GREEN}✓ PASS${NC}: Creator attribution included (username: $creator_username)"
    else
        echo -e "${YELLOW}⚠ WARN${NC}: Creator username missing"
    fi
else
    echo -e "${RED}✗ FAIL${NC}: HTTP $http_code response received (expected 200)"
    echo "Response body: $body"
fi

echo ""

# Test 2: Verify non-existent sample returns 404
echo "Test 2: Verify non-existent sample returns 404"
echo "------------------------------------------------"
fake_id="00000000-0000-0000-0000-000000000000"
http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}/samples/${fake_id}/public")

if [ "$http_code" = "404" ]; then
    echo -e "${GREEN}✓ PASS${NC}: HTTP 404 for non-existent sample"
else
    echo -e "${RED}✗ FAIL${NC}: HTTP $http_code (expected 404)"
fi

echo ""

# Test 3: Rate limiting test
echo "Test 3: Rate limiting (100 requests/minute)"
echo "------------------------------------------------"
echo "Sending 105 requests rapidly to test rate limiting..."

rate_limit_hit=false
for i in {1..105}; do
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}/samples/${SAMPLE_ID}/public")

    if [ "$http_code" = "429" ]; then
        rate_limit_hit=true
        echo -e "${GREEN}✓ PASS${NC}: Rate limit hit at request #$i (HTTP 429)"
        break
    fi

    # Print progress every 10 requests
    if [ $((i % 10)) -eq 0 ]; then
        echo "  Sent $i requests... (HTTP $http_code)"
    fi
done

if [ "$rate_limit_hit" = false ]; then
    echo -e "${YELLOW}⚠ WARN${NC}: Rate limit not hit after 105 requests (may need more requests or wait time)"
fi

echo ""
echo "==================================="
echo "Test Suite Complete"
echo "==================================="
