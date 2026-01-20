"""
SimpleFIN Sync Service

Handles syncing data from SimpleFIN to local database:
- Account balances
- Transactions
- Net worth snapshots
"""

from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
import logging

from database import (
    Institution, Account, Transaction, BalanceHistory,
    NetWorthSnapshot, AccountType, TransactionCategory, ExcludedAccount, get_db
)
from simplefin_client import simplefin_client
from categorizer import categorize_transaction

logger = logging.getLogger(__name__)


def guess_account_type(name: str, balance: float) -> AccountType:
    """Guess account type from name and balance"""
    name_lower = name.lower()

    # Check for common patterns
    if any(word in name_lower for word in ["checking", "chk"]):
        return AccountType.CHECKING
    elif any(word in name_lower for word in ["saving", "sav"]):
        return AccountType.SAVINGS
    elif any(word in name_lower for word in ["credit", "card", "visa", "mastercard", "amex"]):
        return AccountType.CREDIT
    elif any(word in name_lower for word in ["401k", "401(k)", "retirement", "ira", "roth"]):
        return AccountType.RETIREMENT
    elif any(word in name_lower for word in ["brokerage", "investment", "trading", "stock"]):
        return AccountType.BROKERAGE
    elif any(word in name_lower for word in ["loan", "auto", "personal"]):
        return AccountType.LOAN
    elif any(word in name_lower for word in ["mortgage", "home"]):
        return AccountType.MORTGAGE

    # If balance is negative, might be credit
    if balance < 0:
        return AccountType.CREDIT

    return AccountType.OTHER


class SimpleFINSyncService:
    """Service for syncing financial data from SimpleFIN"""

    def __init__(self, db: Session):
        self.db = db

    def sync_institution_quick(self, institution_id: int) -> dict:
        """
        Quick sync - only update account balances, skip transactions.
        Much faster than full sync (~5 seconds vs minutes).
        """
        institution = self.db.query(Institution).filter(
            Institution.id == institution_id
        ).first()

        if not institution:
            raise ValueError(f"Institution {institution_id} not found")

        if not institution.simplefin_access_url:
            raise ValueError(f"No SimpleFIN access URL for institution {institution_id}")

        logger.info(f"Starting QUICK sync for {institution.name} (balances only)")

        results = {
            "institution": institution.name,
            "sync_type": "quick",
            "accounts_synced": 0,
            "errors": []
        }

        try:
            # Fetch balances only (no transactions)
            data = simplefin_client.get_balances_only(institution.simplefin_access_url)

            # Get excluded account IDs
            excluded_ids = {e.simplefin_account_id for e in self.db.query(ExcludedAccount).all()}

            for account_data in data.get("accounts", []):
                account_id = account_data.get("id")
                if account_id in excluded_ids:
                    continue

                # Update account balance
                account = self._upsert_account(institution_id, account_data)
                self._record_balance(account)
                results["accounts_synced"] += 1

            # Update institution status
            institution.last_sync = datetime.utcnow()
            institution.sync_status = "success"
            institution.error_message = None
            self.db.commit()

            # Calculate net worth
            self.calculate_net_worth()

            logger.info(f"Quick sync complete: {results['accounts_synced']} accounts updated")

        except Exception as e:
            logger.error(f"Quick sync error for {institution.name}: {e}")
            institution.sync_status = "error"
            institution.error_message = str(e)
            results["errors"].append(str(e))
            self.db.commit()

        return results

    def sync_institution(self, institution_id: int, full_sync: bool = False) -> dict:
        """
        Sync all data for an institution from SimpleFIN.

        Uses incremental sync by default (from last_sync date).
        Set full_sync=True to force 90-day history fetch.

        Returns summary of what was synced.
        """
        institution = self.db.query(Institution).filter(
            Institution.id == institution_id
        ).first()

        if not institution:
            raise ValueError(f"Institution {institution_id} not found")

        if not institution.simplefin_access_url:
            raise ValueError(f"No SimpleFIN access URL for institution {institution_id}")

        logger.info(f"Starting SimpleFIN sync for {institution.name}")

        results = {
            "institution": institution.name,
            "sync_type": "full" if full_sync else "incremental",
            "accounts_synced": 0,
            "transactions_added": 0,
            "transactions_updated": 0,
            "errors": []
        }

        try:
            # Determine start date: incremental from last_sync or full 90-day
            if full_sync or not institution.last_sync:
                start_date = datetime.now() - timedelta(days=90)
                logger.info(f"Full sync: fetching 90 days from {start_date.date()}")
            else:
                # Incremental: fetch from last sync minus 3 days buffer (for pending transactions)
                start_date = institution.last_sync - timedelta(days=3)
                logger.info(f"Incremental sync: fetching from {start_date.date()} (last sync: {institution.last_sync.date()})")

            data = simplefin_client.get_accounts(
                institution.simplefin_access_url,
                start_date=start_date
            )

            # Log what we received
            for account in data.get("accounts", []):
                txns = account.get("transactions", [])
                if txns:
                    dates = [t.get("date") for t in txns if t.get("date")]
                    pending_count = sum(1 for t in txns if t.get("pending"))
                    logger.info(f"Account '{account.get('name')}': {len(txns)} transactions, "
                               f"{pending_count} pending, dates: {min(dates) if dates else 'N/A'} to {max(dates) if dates else 'N/A'}")

            # Sync the data
            sync_result = self.sync_from_simplefin(institution_id, data)
            results.update(sync_result)

            # Update institution status
            institution.last_sync = datetime.utcnow()
            institution.sync_status = "success"
            institution.error_message = None

        except Exception as e:
            logger.error(f"Sync error for {institution.name}: {e}")
            institution.sync_status = "error"
            institution.error_message = str(e)
            results["errors"].append(str(e))

        self.db.commit()
        return results

    def sync_from_simplefin(self, institution_id: int, data: dict) -> dict:
        """
        Sync accounts and transactions from SimpleFIN response data.
        Uses batch operations for better performance.

        Args:
            institution_id: The institution to attach accounts to
            data: Parsed SimpleFIN response from simplefin_client.get_accounts()

        Returns:
            Summary of what was synced
        """
        results = {
            "accounts_synced": 0,
            "transactions_added": 0,
            "transactions_updated": 0,
            "errors": data.get("errors", [])
        }

        # Get excluded account IDs
        excluded_ids = {e.simplefin_account_id for e in self.db.query(ExcludedAccount).all()}

        for account_data in data.get("accounts", []):
            try:
                account_id = account_data.get("id")

                # Skip excluded accounts
                if account_id in excluded_ids:
                    logger.info(f"Skipping excluded account: {account_data.get('name')}")
                    continue

                # Sync account
                account = self._upsert_account(institution_id, account_data)
                results["accounts_synced"] += 1

                # Batch sync transactions
                txn_results = self._batch_upsert_transactions(account.id, account_data.get("transactions", []))
                results["transactions_added"] += txn_results["added"]
                results["transactions_updated"] += txn_results["updated"]

                # Record balance history
                self._record_balance(account)

            except Exception as e:
                logger.error(f"Error syncing account {account_data.get('name')}: {e}")
                results["errors"].append(str(e))

        self.db.commit()

        # Calculate net worth after sync
        self.calculate_net_worth()

        return results

    def _batch_upsert_transactions(self, account_id: int, transactions: list) -> dict:
        """
        Batch insert/update transactions for better performance.

        Returns dict with 'added' and 'updated' counts.
        """
        if not transactions:
            return {"added": 0, "updated": 0}

        # Get all transaction IDs we're about to sync
        txn_ids = [t.get("id") for t in transactions if t.get("id")]

        # Fetch existing transactions in one query
        existing_txns = {
            t.simplefin_transaction_id: t
            for t in self.db.query(Transaction).filter(
                Transaction.simplefin_transaction_id.in_(txn_ids)
            ).all()
        }

        added = 0
        updated = 0
        new_transactions = []

        for txn_data in transactions:
            txn_id = txn_data.get("id")
            if not txn_id:
                continue

            existing = existing_txns.get(txn_id)

            if existing:
                # Update existing transaction
                self._update_transaction(existing, txn_data)
                updated += 1
            else:
                # Prepare new transaction for batch insert
                new_txn = self._create_transaction(account_id, txn_data)
                new_transactions.append(new_txn)
                added += 1

        # Batch insert new transactions
        if new_transactions:
            self.db.bulk_save_objects(new_transactions)

        return {"added": added, "updated": updated}

    def _create_transaction(self, account_id: int, txn_data: dict) -> Transaction:
        """Create a new Transaction object (without adding to session)"""
        txn = Transaction(
            account_id=account_id,
            simplefin_transaction_id=txn_data.get("id"),
            date=txn_data.get("date"),
            name=txn_data.get("description", "Unknown"),
            merchant_name=txn_data.get("payee"),
            amount=txn_data.get("amount", 0),
            is_pending=txn_data.get("pending", False),
            original_category=txn_data.get("memo")
        )

        # Auto-categorize
        txn.category = categorize_transaction(
            name=txn.name,
            merchant_name=txn.merchant_name,
            original_category=None,
            original_category_id=None,
            amount=txn.amount
        )

        return txn

    def _update_transaction(self, txn: Transaction, txn_data: dict):
        """Update an existing transaction with new data"""
        txn.date = txn_data.get("date")
        txn.name = txn_data.get("description", "Unknown")
        txn.merchant_name = txn_data.get("payee")
        txn.amount = txn_data.get("amount", 0)
        txn.is_pending = txn_data.get("pending", False)

        if txn_data.get("memo"):
            txn.original_category = txn_data.get("memo")

        # Re-categorize if no user override
        if not txn.user_category:
            txn.category = categorize_transaction(
                name=txn.name,
                merchant_name=txn.merchant_name,
                original_category=None,
                original_category_id=None,
                amount=txn.amount
            )

    def _upsert_account(self, institution_id: int, account_data: dict) -> Account:
        """Insert or update an account from SimpleFIN data"""
        account_id = account_data.get("id")

        # Find existing account
        account = self.db.query(Account).filter(
            Account.simplefin_account_id == account_id
        ).first()

        is_new = account is None
        if is_new:
            account = Account(
                institution_id=institution_id,
                simplefin_account_id=account_id
            )
            self.db.add(account)

        # Update account info
        account.name = account_data.get("name", "Unknown Account")
        account.currency = account_data.get("currency", "USD")
        account.current_balance = account_data.get("balance", 0)
        account.available_balance = account_data.get("available_balance")

        # Only guess account type on first sync, preserve user changes after that
        if is_new:
            account.account_type = guess_account_type(
                account.name,
                account.current_balance
            )

        # Store institution name in official_name for reference
        inst_info = account_data.get("institution", {})
        account.official_name = inst_info.get("name")

        self.db.flush()
        return account

    def _record_balance(self, account: Account):
        """Record or update today's balance snapshot"""
        today = date.today()

        existing = self.db.query(BalanceHistory).filter(
            BalanceHistory.account_id == account.id,
            BalanceHistory.date == today
        ).first()

        if existing:
            # Update existing record if balance changed
            existing.balance = account.current_balance
            existing.available = account.available_balance
        else:
            history = BalanceHistory(
                account_id=account.id,
                date=today,
                balance=account.current_balance,
                available=account.available_balance
            )
            self.db.add(history)

    def calculate_net_worth(self) -> NetWorthSnapshot:
        """Calculate and store today's net worth snapshot"""
        today = date.today()

        # Check if already calculated today
        snapshot = self.db.query(NetWorthSnapshot).filter(
            NetWorthSnapshot.date == today
        ).first()

        if not snapshot:
            snapshot = NetWorthSnapshot(date=today)
            self.db.add(snapshot)

        # Get all active, visible accounts
        accounts = self.db.query(Account).filter(
            Account.is_active == True,
            Account.is_hidden == False
        ).all()

        # Calculate totals
        total_assets = 0
        total_liabilities = 0
        cash = 0
        investments = 0
        retirement = 0
        credit_debt = 0
        loan_debt = 0

        for account in accounts:
            balance = account.current_balance or 0

            if account.account_type in [AccountType.CHECKING, AccountType.SAVINGS]:
                cash += balance
                total_assets += balance

            elif account.account_type in [AccountType.INVESTMENT, AccountType.BROKERAGE]:
                investments += balance
                total_assets += balance

            elif account.account_type == AccountType.RETIREMENT:
                retirement += balance
                total_assets += balance

            elif account.account_type == AccountType.CREDIT:
                # Credit balances are typically negative (money owed)
                credit_debt += abs(balance)
                total_liabilities += abs(balance)

            elif account.account_type in [AccountType.LOAN, AccountType.MORTGAGE]:
                loan_debt += abs(balance)
                total_liabilities += abs(balance)

            elif account.account_type == AccountType.OTHER:
                # Positive = asset, Negative = liability
                if balance >= 0:
                    total_assets += balance
                else:
                    total_liabilities += abs(balance)

        snapshot.total_assets = total_assets
        snapshot.total_liabilities = total_liabilities
        snapshot.net_worth = total_assets - total_liabilities
        snapshot.cash = cash
        snapshot.investments = investments
        snapshot.retirement = retirement
        snapshot.credit_debt = credit_debt
        snapshot.loan_debt = loan_debt

        self.db.commit()

        logger.info(f"Net worth snapshot: ${snapshot.net_worth:,.2f}")
        return snapshot


def sync_all_institutions(db: Session, full_sync: bool = False) -> list:
    """
    Sync all active SimpleFIN institutions.

    Args:
        db: Database session
        full_sync: If True, fetch full 90-day history. If False, use incremental sync.
    """
    institutions = db.query(Institution).filter(
        Institution.is_active == True,
        Institution.provider == "simplefin"
    ).all()

    results = []
    sync_service = SimpleFINSyncService(db)

    for institution in institutions:
        try:
            result = sync_service.sync_institution(institution.id, full_sync=full_sync)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to sync {institution.name}: {e}")
            results.append({
                "institution": institution.name,
                "error": str(e)
            })

    return results


def quick_sync_all_institutions(db: Session) -> list:
    """
    Quick sync all institutions - balances only, no transactions.
    Much faster than full sync.
    """
    institutions = db.query(Institution).filter(
        Institution.is_active == True,
        Institution.provider == "simplefin"
    ).all()

    results = []
    sync_service = SimpleFINSyncService(db)

    for institution in institutions:
        try:
            result = sync_service.sync_institution_quick(institution.id)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to quick sync {institution.name}: {e}")
            results.append({
                "institution": institution.name,
                "error": str(e)
            })

    return results


if __name__ == "__main__":
    from database import init_db, SessionLocal

    init_db()
    db = SessionLocal()

    print("SimpleFIN Sync Service ready")
    print("Run sync_all_institutions(db) to sync all connected accounts")
