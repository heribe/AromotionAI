import sys
import pytest

if __name__ == "__main__":
    # Run pytest programmatically on the e2e test directory
    print("Starting E2E Test Suite...")
    exit_code = pytest.main(["-v", "backend/tests/e2e/"])
    print(f"Pytest exited with code: {exit_code}")
    sys.exit(exit_code)
