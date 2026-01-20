"""
SimpleFIN Bridge API Client for Finance Tracker

Handles:
- Setup token claiming (one-time exchange for access URL)
- Account and transaction fetching
- Balance retrieval

SimpleFIN API Documentation: https://www.simplefin.org/protocol.html
"""

import httpx
import base64
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class SimpleFINClient:
    """Client for SimpleFIN Bridge API"""

    def __init__(self):
        self.timeout = 120.0  # 2 minutes - SimpleFIN can be slow
        self.max_retries = 3

    def claim_setup_token(self, setup_token: str) -> str:
        """
        Claim a setup token to get an Access URL.

        The setup token is a base64-encoded URL that points to the claim endpoint.
        This can only be done ONCE per token.

        Args:
            setup_token: The setup token from SimpleFIN Bridge

        Returns:
            The Access URL (contains embedded credentials)

        Raises:
            Exception: If token is invalid or already claimed
        """
        try:
            # Decode the setup token to get the claim URL
            claim_url = base64.b64decode(setup_token).decode('utf-8')
            logger.info(f"Claiming token at: {claim_url}")

            # POST to claim URL to get access URL
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(claim_url)

                if response.status_code == 403:
                    raise Exception("Setup token already claimed or invalid")
                elif response.status_code == 402:
                    raise Exception("SimpleFIN subscription required")

                response.raise_for_status()

                # Response body is the Access URL
                access_url = response.text.strip()
                logger.info("Successfully claimed setup token")
                return access_url

        except base64.binascii.Error:
            raise Exception("Invalid setup token format")
        except httpx.HTTPError as e:
            logger.error(f"Failed to claim token: {e}")
            raise Exception(f"Failed to claim token: {e}")

    def get_accounts(
        self,
        access_url: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_pending: bool = True
    ) -> dict:
        """
        Fetch accounts and transactions from SimpleFIN.

        Args:
            access_url: The Access URL with embedded credentials
            start_date: Optional start date for transactions
            end_date: Optional end date for transactions
            include_pending: Whether to include pending transactions

        Returns:
            Dict with 'accounts' list and optional 'errors' list
        """
        import time

        # Build the accounts endpoint URL
        # Access URL format: https://user:pass@host/simplefin
        accounts_url = f"{access_url}/accounts"

        # Build query parameters
        params = {}
        if start_date:
            params['start-date'] = int(start_date.timestamp())
        if end_date:
            params['end-date'] = int(end_date.timestamp())
        if include_pending:
            params['pending'] = '1'

        last_error = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    wait_time = 5 * (2 ** (attempt - 1))  # 5s, 10s, 20s
                    logger.info(f"Retry attempt {attempt + 1}/{self.max_retries} after {wait_time}s wait...")
                    time.sleep(wait_time)

                with httpx.Client(timeout=self.timeout) as client:
                    logger.info(f"Fetching SimpleFIN accounts (attempt {attempt + 1}/{self.max_retries})...")
                    response = client.get(accounts_url, params=params)

                    if response.status_code == 403:
                        raise Exception("Access denied - invalid credentials")
                    elif response.status_code == 402:
                        raise Exception("SimpleFIN subscription expired")

                    response.raise_for_status()

                    data = response.json()
                    logger.info(f"SimpleFIN returned {len(data.get('accounts', []))} accounts")
                    return self._parse_response(data)

            except (httpx.TimeoutException, httpx.ReadTimeout) as e:
                last_error = e
                logger.warning(f"SimpleFIN timeout on attempt {attempt + 1}: {e}")
                continue
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch accounts: {e}")
                raise Exception(f"Failed to fetch accounts: {e}")

        # All retries exhausted
        logger.error(f"SimpleFIN failed after {self.max_retries} attempts: {last_error}")
        raise Exception(f"Failed to fetch accounts after {self.max_retries} attempts: timeout")

    def get_balances_only(self, access_url: str) -> dict:
        """
        Fetch only account balances (no transactions).
        Faster for balance-only updates.
        """
        try:
            accounts_url = f"{access_url}/accounts"
            params = {'balances-only': '1'}

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(accounts_url, params=params)
                response.raise_for_status()

                data = response.json()
                return self._parse_response(data)

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch balances: {e}")
            raise Exception(f"Failed to fetch balances: {e}")

    def _parse_response(self, data: dict) -> dict:
        """
        Parse SimpleFIN response into our internal format.

        SimpleFIN Account structure:
        {
            "id": "account-id",
            "name": "Account Name",
            "currency": "USD",
            "balance": "1234.56",
            "available-balance": "1200.00",
            "balance-date": 1234567890,
            "org": {
                "name": "Bank Name",
                "domain": "bank.com",
                "sfin-url": "..."
            },
            "transactions": [...]
        }

        SimpleFIN Transaction structure:
        {
            "id": "txn-id",
            "posted": 1234567890,
            "amount": "-50.00",
            "description": "GROCERY STORE",
            "payee": "Grocery Store",
            "memo": "optional memo",
            "pending": true/false
        }
        """
        result = {
            "accounts": [],
            "errors": data.get("errors", [])
        }

        for account in data.get("accounts", []):
            parsed_account = {
                "id": account.get("id"),
                "name": account.get("name", "Unknown Account"),
                "currency": account.get("currency", "USD"),
                "balance": float(account.get("balance", 0)),
                "available_balance": float(account.get("available-balance", 0)) if account.get("available-balance") else None,
                "balance_date": datetime.fromtimestamp(account.get("balance-date", 0)) if account.get("balance-date") else None,
                "institution": {
                    "name": account.get("org", {}).get("name", "Unknown"),
                    "domain": account.get("org", {}).get("domain"),
                    "id": account.get("org", {}).get("sfin-url", account.get("org", {}).get("domain", "unknown"))
                },
                "transactions": []
            }

            # Parse transactions
            for txn in account.get("transactions", []):
                parsed_txn = {
                    "id": txn.get("id"),
                    "date": datetime.fromtimestamp(txn.get("posted", 0)).date() if txn.get("posted") else None,
                    "amount": float(txn.get("amount", 0)),
                    "description": txn.get("description", ""),
                    "payee": txn.get("payee"),
                    "memo": txn.get("memo"),
                    "pending": txn.get("pending", False)
                }
                parsed_account["transactions"].append(parsed_txn)

            result["accounts"].append(parsed_account)

        return result

    def test_connection(self, access_url: str) -> bool:
        """Test if the access URL is still valid."""
        try:
            result = self.get_balances_only(access_url)
            return len(result.get("accounts", [])) > 0
        except Exception:
            return False


# Singleton instance
simplefin_client = SimpleFINClient()


if __name__ == "__main__":
    print("SimpleFIN Client")
    print("=" * 40)
    print("To test, you need a setup token from SimpleFIN Bridge")
    print("Visit: https://beta-bridge.simplefin.org")
