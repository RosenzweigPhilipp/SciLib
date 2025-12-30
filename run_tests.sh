#!/usr/bin/env bash
#
# Quick test runner for SciLib
#
# Usage:
#   ./run_tests.sh              # Run all tests
#   ./run_tests.sh -v           # Verbose output
#   ./run_tests.sh --cov        # With coverage report
#   ./run_tests.sh config       # Run only config tests
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🧪 SciLib Test Runner${NC}"
echo "================================"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}⚠️  pytest not found. Installing test dependencies...${NC}"
    pip install pytest pytest-asyncio pytest-cov pytest-mock httpx
fi

# Parse arguments
VERBOSE=""
COVERAGE=""
TEST_FILE=""

for arg in "$@"; do
    case $arg in
        -v|--verbose)
            VERBOSE="-v"
            ;;
        --cov|--coverage)
            COVERAGE="--cov=app --cov-report=html --cov-report=term"
            ;;
        config|database|api|utils|confidence|pipeline)
            TEST_FILE="tests/test_${arg}*.py"
            ;;
        *)
            TEST_FILE="$arg"
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest ${TEST_FILE:-tests/} ${VERBOSE} ${COVERAGE}"

echo -e "${BLUE}Running: ${PYTEST_CMD}${NC}"
echo ""

# Run tests
$PYTEST_CMD

# Show coverage report location if generated
if [ -n "$COVERAGE" ]; then
    echo ""
    echo -e "${GREEN}✓ Coverage report generated: htmlcov/index.html${NC}"
fi

echo ""
echo -e "${GREEN}✓ Tests complete!${NC}"
