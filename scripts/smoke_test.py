"""Smoke test: verify service account auth and MCC access.

Run with:
    uv run python scripts/smoke_test.py

Exit 0 on success. Prints each accessible customer resource name.
"""

import sys

try:
    from ads_mcp.client import get_client
except EnvironmentError as exc:
    print(f"Configuration error: {exc}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    print("Building Google Ads client...")
    try:
        client = get_client()
    except (EnvironmentError, FileNotFoundError) as exc:
        print(f"Failed to build client: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Calling CustomerService.list_accessible_customers()...")
    try:
        customer_service = client.get_service("CustomerService")
        response = customer_service.list_accessible_customers()
    except Exception as exc:
        print(f"API call failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\nSuccess -- {len(response.resource_names)} accessible customer(s):\n")
    for resource_name in response.resource_names:
        print(f"  {resource_name}")

    print("\nAuth is working. You are ready to run the MCP server.")


if __name__ == "__main__":
    main()
