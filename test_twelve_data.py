"""Manual smoke test for the Twelve Data integration."""

import sys

from backend.providers.twelve_data import get_daily_prices


def main() -> int:
    try:
        prices = get_daily_prices("AAPL", outputsize=5)
    except Exception as exc:
        # Avoid printing full exception details that could expose request URLs.
        print(f"API test failed: {type(exc).__name__}.")
        print("Check .env, account credits, symbol access, and network access.")
        return 1

    print("API connection successful.")
    print(f"Rows returned: {len(prices)}")
    print(prices.tail(5).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
