"""
Finance Tracker API

FastAPI backend for personal finance tracking with SimpleFIN integration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from datetime import datetime, date, timedelta
from typing import Optional, List
from pathlib import Path
from pydantic import BaseModel
import logging

from database import (
    init_db, get_db, Institution, Account, Transaction,
    BalanceHistory, Holding, NetWorthSnapshot, Budget,
    AccountType, TransactionCategory, ExcludedAccount, TransactionRule,
    Subscription
)
from simplefin_client import simplefin_client
from sync_service import SimpleFINSyncService, sync_all_institutions
from categorizer import (
    categorize_transaction, get_category_display_name, get_category_emoji, get_parent_category
)
from config import settings
from scheduler import start_scheduler
from auth import require_auth


# Pydantic models for requests
class SimpleFINSetupRequest(BaseModel):
    setup_token: str


class TransactionRuleCreate(BaseModel):
    name: str
    match_field: str  # 'name', 'merchant_name', or 'any'
    match_type: str  # 'contains', 'starts_with', 'ends_with', 'exact'
    match_value: str
    case_sensitive: bool = False
    account_type: Optional[str] = None  # 'spending', 'investment', or null
    assign_category: str
    priority: int = 0


class TransactionRuleUpdate(BaseModel):
    name: Optional[str] = None
    match_field: Optional[str] = None
    match_type: Optional[str] = None
    match_value: Optional[str] = None
    case_sensitive: Optional[bool] = None
    account_type: Optional[str] = None
    assign_category: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class SubscriptionCreate(BaseModel):
    name: str
    merchant_pattern: str
    expected_amount: float
    billing_cycle: str = "monthly"  # monthly, annual, weekly
    category: Optional[str] = "subscription_other"


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    merchant_pattern: Optional[str] = None
    expected_amount: Optional[float] = None
    billing_cycle: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    is_confirmed: Optional[bool] = None


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - startup and shutdown"""
    # Startup
    logger.info("Starting Finance Tracker API...")
    if settings.AUTH_ENABLED:
        logger.info("Authentication is ENABLED")
    else:
        logger.warning("Authentication is DISABLED - set AUTH_USERNAME and AUTH_PASSWORD in .env for production")
    logger.info("Starting background scheduler...")
    start_scheduler()
    logger.info("Background scheduler started")

    yield  # App runs here

    # Shutdown
    logger.info("Shutting down Finance Tracker API...")


# Create FastAPI app
app = FastAPI(
    title="Finance Tracker API",
    description="Personal finance tracking with SimpleFIN integration",
    version="2.1.0",
    lifespan=lifespan
)

# CORS middleware for PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")


# ============== Health Check Endpoint ==============

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Get basic stats
    institution_count = db.query(Institution).filter(Institution.is_active == True).count()
    account_count = db.query(Account).filter(Account.is_active == True).count()

    # Check for recent sync issues
    recent_errors = db.query(Institution).filter(
        Institution.sync_status == "error",
        Institution.is_active == True
    ).count()

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "institutions": institution_count,
        "accounts": account_count,
        "sync_errors": recent_errors,
        "version": "1.0.0"
    }


# ============== Standardized Error Helpers ==============

class APIError(Exception):
    """Custom API error with code and user-friendly message"""
    def __init__(self, code: str, message: str, details: str = None, status_code: int = 400):
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(message)


@app.exception_handler(APIError)
async def api_error_handler(request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": exc.code,
            "message": exc.message,
            "details": exc.details
        }
    )


# ============== SimpleFIN Setup Endpoints ==============

@app.post("/api/simplefin/setup")
async def setup_simplefin(
    request: SimpleFINSetupRequest,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """
    Setup SimpleFIN connection using a setup token.

    The user gets this token from https://beta-bridge.simplefin.org
    after connecting their banks there.
    """
    try:
        # Claim the setup token to get an access URL
        access_url = simplefin_client.claim_setup_token(request.setup_token)

        # Fetch accounts to verify connection and get institution info
        data = simplefin_client.get_accounts(access_url)

        if not data.get("accounts"):
            raise HTTPException(status_code=400, detail="No accounts found. Please connect banks in SimpleFIN Bridge first.")

        # Group accounts by institution
        institutions_map = {}
        for account in data["accounts"]:
            inst_info = account.get("institution", {})
            inst_id = inst_info.get("id", "unknown")

            if inst_id not in institutions_map:
                institutions_map[inst_id] = {
                    "name": inst_info.get("name", "Unknown Institution"),
                    "domain": inst_info.get("domain"),
                    "accounts": []
                }
            institutions_map[inst_id]["accounts"].append(account)

        # Create a single institution record for SimpleFIN connection
        # (SimpleFIN provides all accounts through one access URL)
        institution = Institution(
            simplefin_id=f"simplefin_{datetime.utcnow().timestamp()}",
            simplefin_access_url=access_url,
            simplefin_org_id="simplefin",
            name="SimpleFIN Bridge",
            provider="simplefin"
        )
        db.add(institution)
        db.commit()
        db.refresh(institution)

        # Sync all accounts and transactions
        sync_service = SimpleFINSyncService(db)
        sync_result = sync_service.sync_from_simplefin(institution.id, data)

        return {
            "institution_id": institution.id,
            "name": institution.name,
            "accounts_synced": sync_result.get("accounts_synced", 0),
            "transactions_synced": sync_result.get("transactions_synced", 0),
            "institutions_found": list(institutions_map.keys())
        }

    except Exception as e:
        logger.error(f"SimpleFIN setup error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============== Institution Endpoints ==============

@app.get("/api/institutions")
async def get_institutions(db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    """Get all connected institutions"""
    institutions = db.query(Institution).filter(Institution.is_active == True).all()

    now = datetime.utcnow()
    return [{
        "id": inst.id,
        "name": inst.name,
        "logo_url": inst.logo_url,
        "primary_color": inst.primary_color,
        "last_sync": inst.last_sync.isoformat() if inst.last_sync else None,
        "hours_since_sync": round((now - inst.last_sync).total_seconds() / 3600, 1) if inst.last_sync else None,
        "sync_status": inst.sync_status,
        "error_message": inst.error_message,
        "accounts_count": len(inst.accounts)
    } for inst in institutions]


@app.delete("/api/institutions/{institution_id}")
async def remove_institution(institution_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    """Remove an institution and all its data"""
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    db.delete(institution)
    db.commit()
    return {"message": "Institution removed"}


@app.post("/api/sync")
async def sync_all(db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    """Sync all connected SimpleFIN institutions"""
    results = sync_all_institutions(db)
    return {"results": results}


@app.post("/api/sync/{institution_id}")
async def sync_institution(institution_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    """Sync a specific institution"""
    sync_service = SimpleFINSyncService(db)
    try:
        result = sync_service.sync_institution(institution_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/recategorize")
async def recategorize_transactions(db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    """Re-categorize all transactions using updated rules"""
    transactions = db.query(Transaction).filter(
        Transaction.user_category == None  # Only re-categorize auto-categorized transactions
    ).all()

    updated = 0
    for txn in transactions:
        new_category = categorize_transaction(
            name=txn.name,
            merchant_name=txn.merchant_name,
            original_category=None,
            original_category_id=None,
            amount=txn.amount
        )
        if new_category != txn.category:
            txn.category = new_category
            updated += 1

    db.commit()
    return {"message": f"Re-categorized {updated} transactions out of {len(transactions)}"}


# ============== Account Endpoints ==============

@app.get("/api/accounts")
async def get_accounts(
    include_hidden: bool = False,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get all accounts with current balances"""
    query = db.query(Account).filter(Account.is_active == True)
    if not include_hidden:
        query = query.filter(Account.is_hidden == False)

    accounts = query.all()

    return [{
        "id": acc.id,
        "institution_id": acc.institution_id,
        "institution_name": acc.institution.name if acc.institution else None,
        "name": acc.name,
        "official_name": acc.official_name,
        "mask": acc.mask,
        "type": acc.account_type.value,
        "subtype": acc.subtype,
        "current_balance": acc.current_balance,
        "available_balance": acc.available_balance,
        "credit_limit": acc.credit_limit,
        "is_hidden": acc.is_hidden
    } for acc in accounts]


@app.patch("/api/accounts/{account_id}")
async def update_account(
    account_id: int,
    is_hidden: Optional[bool] = None,
    account_type: Optional[str] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Update account settings (type, name, visibility)"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if is_hidden is not None:
        account.is_hidden = is_hidden

    if account_type is not None:
        try:
            account.account_type = AccountType(account_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid account type: {account_type}")

    if name is not None:
        account.name = name

    db.commit()
    return {"message": "Account updated", "account_type": account.account_type.value}


@app.delete("/api/accounts/{account_id}")
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Delete an account and all its transactions, exclude from future syncs"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account_name = account.name
    simplefin_id = account.simplefin_account_id

    # Add to exclusion list so it doesn't come back on sync
    if simplefin_id:
        existing = db.query(ExcludedAccount).filter(
            ExcludedAccount.simplefin_account_id == simplefin_id
        ).first()
        if not existing:
            excluded = ExcludedAccount(
                simplefin_account_id=simplefin_id,
                account_name=account_name
            )
            db.add(excluded)

    db.delete(account)
    db.commit()
    return {"message": f"Account '{account_name}' deleted"}


# ============== Transaction Endpoints ==============

# Account types for filtering
SPENDING_ACCOUNT_TYPES = [AccountType.CHECKING, AccountType.SAVINGS, AccountType.CREDIT]
INVESTMENT_ACCOUNT_TYPES = [AccountType.INVESTMENT, AccountType.BROKERAGE, AccountType.RETIREMENT]


@app.get("/api/transactions")
async def get_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    account_id: Optional[int] = None,
    account_type: Optional[str] = None,  # "spending" or "investment"
    category: Optional[str] = None,
    search: Optional[str] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    exclude_transfers: bool = False,  # Exclude transfer/payment transactions
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get transactions with filtering options"""
    query = db.query(Transaction).join(Account).filter(Transaction.is_pending == False)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)

    # Filter by amount range (for income/expense filtering)
    if amount_min is not None:
        query = query.filter(Transaction.amount >= amount_min)
    if amount_max is not None:
        query = query.filter(Transaction.amount <= amount_max)

    # Exclude transfer transactions (credit card payments, venmo, etc.)
    transfer_categories = [
        TransactionCategory.FINANCIAL_TRANSFER,
        TransactionCategory.FINANCIAL_INVESTMENT,
        TransactionCategory.INCOME_TRANSFER
    ]

    # Auto-exclude transfers for spending queries (negative amounts from spending accounts)
    if exclude_transfers or (account_type == "spending" and amount_max is not None and amount_max < 0):
        query = query.filter(~Transaction.category.in_(transfer_categories))

    # Filter by account type category (spending vs investment)
    if account_type == "spending":
        query = query.filter(Account.account_type.in_(SPENDING_ACCOUNT_TYPES))
    elif account_type == "investment":
        query = query.filter(Account.account_type.in_(INVESTMENT_ACCOUNT_TYPES))

    if category:
        try:
            cat_enum = TransactionCategory(category)
            query = query.filter(
                (Transaction.user_category == cat_enum) |
                ((Transaction.user_category == None) & (Transaction.category == cat_enum))
            )
        except ValueError:
            pass
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Transaction.name.ilike(search_pattern)) |
            (Transaction.merchant_name.ilike(search_pattern))
        )

    total = query.count()

    transactions = query.order_by(desc(Transaction.date)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "transactions": [{
            "id": txn.id,
            "date": txn.date.isoformat() if txn.date else None,
            "name": txn.name,
            "merchant_name": txn.merchant_name,
            "amount": txn.amount,
            "category": txn.effective_category.value,
            "category_display": get_category_display_name(txn.effective_category),
            "category_emoji": get_category_emoji(txn.effective_category),
            "parent_category": get_parent_category(txn.effective_category),
            "account_id": txn.account_id,
            "account_name": txn.account.name if txn.account else None,
            "account_type": txn.account.account_type.value if txn.account else None,
            "is_excluded": txn.is_excluded,
            "notes": txn.user_notes
        } for txn in transactions]
    }


@app.patch("/api/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    category: Optional[str] = None,
    notes: Optional[str] = None,
    is_excluded: Optional[bool] = None,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Update a transaction (category, notes, etc.)"""
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if category:
        try:
            txn.user_category = TransactionCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")

    if notes is not None:
        txn.user_notes = notes

    if is_excluded is not None:
        txn.is_excluded = is_excluded

    db.commit()
    return {"message": "Transaction updated"}


# ============== Net Worth & Dashboard Endpoints ==============

@app.get("/api/dashboard")
async def get_dashboard(db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    """Get dashboard summary data"""
    # Get latest net worth
    latest_nw = db.query(NetWorthSnapshot).order_by(
        desc(NetWorthSnapshot.date)
    ).first()

    # Get previous day for comparison
    yesterday = date.today() - timedelta(days=1)
    prev_nw = db.query(NetWorthSnapshot).filter(
        NetWorthSnapshot.date <= yesterday
    ).order_by(desc(NetWorthSnapshot.date)).first()

    # Calculate change
    nw_change = 0
    nw_change_pct = 0
    if latest_nw and prev_nw:
        nw_change = latest_nw.net_worth - prev_nw.net_worth
        if prev_nw.net_worth != 0:
            nw_change_pct = (nw_change / abs(prev_nw.net_worth)) * 100

    # Get accounts by type
    accounts = db.query(Account).filter(
        Account.is_active == True,
        Account.is_hidden == False
    ).all()

    accounts_by_type = {}
    for acc in accounts:
        type_name = acc.account_type.value
        if type_name not in accounts_by_type:
            accounts_by_type[type_name] = []
        accounts_by_type[type_name].append({
            "id": acc.id,
            "name": acc.name,
            "institution": acc.institution.name if acc.institution else None,
            "balance": acc.current_balance
        })

    # Get this month's spending (negative amounts = expenses)
    # Only from spending accounts (checking, savings, credit) - exclude investment accounts
    # ALSO exclude transfer categories (credit card payments, internal transfers)
    first_of_month = date.today().replace(day=1)

    transfer_categories = [
        TransactionCategory.FINANCIAL_TRANSFER,
        TransactionCategory.FINANCIAL_INVESTMENT,
        TransactionCategory.INCOME_TRANSFER,
    ]

    spending_query = db.query(
        func.sum(Transaction.amount)
    ).join(Account).filter(
        Transaction.date >= first_of_month,
        Transaction.amount < 0,  # Negative = expense
        Transaction.is_excluded == False,
        Account.account_type.in_(SPENDING_ACCOUNT_TYPES),  # Exclude investment accounts
        ~Transaction.category.in_(transfer_categories)  # Exclude transfers
    ).scalar() or 0
    spending_query = abs(spending_query)  # Convert to positive for display

    # Calculate dynamic budget: 75% of average gross income over past 3 months
    three_months_ago = date.today() - timedelta(days=90)
    total_income = db.query(
        func.sum(Transaction.amount)
    ).join(Account).filter(
        Transaction.date >= three_months_ago,
        Transaction.amount > 0,  # Positive = income
        Transaction.is_excluded == False,
        Account.account_type.in_(SPENDING_ACCOUNT_TYPES),  # From spending accounts
        Transaction.category.in_([
            TransactionCategory.INCOME_SALARY,
            TransactionCategory.INCOME_OTHER,
            TransactionCategory.INCOME_INVESTMENT,
        ])
    ).scalar() or 0

    # Calculate monthly average and take 75%
    avg_monthly_income = total_income / 3
    dynamic_budget = avg_monthly_income * 0.75

    # Get spending by category this month (excluding investment accounts and transfers)
    category_spending = db.query(
        Transaction.category,
        func.sum(Transaction.amount)
    ).join(Account).filter(
        Transaction.date >= first_of_month,
        Transaction.amount < 0,  # Negative = expense
        Transaction.is_excluded == False,
        Account.account_type.in_(SPENDING_ACCOUNT_TYPES),  # Exclude investment accounts
        ~Transaction.category.in_(transfer_categories)  # Exclude transfers
    ).group_by(Transaction.category).all()

    spending_by_category = [{
        "category": cat.value,
        "display": get_category_display_name(cat),
        "emoji": get_category_emoji(cat),
        "parent": get_parent_category(cat),
        "amount": abs(amount)  # Convert to positive for display
    } for cat, amount in category_spending if amount < 0]

    spending_by_category.sort(key=lambda x: x["amount"], reverse=True)

    return {
        "net_worth": {
            "current": latest_nw.net_worth if latest_nw else 0,
            "change": nw_change,
            "change_pct": nw_change_pct,
            "as_of": latest_nw.date.isoformat() if latest_nw else None,
            "breakdown": {
                "cash": latest_nw.cash if latest_nw else 0,
                "investments": latest_nw.investments if latest_nw else 0,
                "retirement": getattr(latest_nw, 'retirement', 0) if latest_nw else 0,
                "credit_debt": latest_nw.credit_debt if latest_nw else 0,
                "loan_debt": latest_nw.loan_debt if latest_nw else 0
            }
        },
        "accounts": accounts_by_type,
        "spending": {
            "month_total": spending_query,
            "budget": dynamic_budget,
            "avg_monthly_income": avg_monthly_income,
            "by_category": spending_by_category[:10]  # Top 10 categories
        }
    }


@app.get("/api/net-worth/history")
async def get_net_worth_history(
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get net worth history for charting"""
    start_date = date.today() - timedelta(days=days)

    history = db.query(NetWorthSnapshot).filter(
        NetWorthSnapshot.date >= start_date
    ).order_by(NetWorthSnapshot.date).all()

    return [{
        "date": snap.date.isoformat(),
        "net_worth": snap.net_worth,
        "assets": snap.total_assets,
        "liabilities": snap.total_liabilities,
        "cash": snap.cash,
        "investments": snap.investments,
        "retirement": getattr(snap, 'retirement', 0) or 0
    } for snap in history]


# ============== Spending & Budget Endpoints ==============

@app.get("/api/spending/summary")
async def get_spending_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get spending summary by category (excludes transfers)"""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    # Get all spending transactions (negative amounts = expenses)
    # Exclude investment accounts
    transactions = db.query(Transaction).join(Account).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.amount < 0,  # Negative = expense
        Transaction.is_excluded == False,
        Account.account_type.in_(SPENDING_ACCOUNT_TYPES)  # Exclude investment accounts
    ).all()

    # Calculate spending by category, excluding transfers (but include peer payments)
    category_totals = {}
    for txn in transactions:
        # Always include peer-to-peer payments (Venmo, Zelle, etc.) as real spending
        is_peer = is_peer_payment(txn.name)
        if not is_peer:
            # Skip transfer transactions (internal money movements)
            if is_transfer_transaction(txn.name) or is_transfer_transaction(txn.merchant_name):
                continue
            # Skip transfer and investment categories (not real spending)
            if txn.category in (TransactionCategory.FINANCIAL_TRANSFER, TransactionCategory.FINANCIAL_INVESTMENT):
                continue

        cat = txn.category
        if cat not in category_totals:
            category_totals[cat] = {"total": 0, "count": 0}
        category_totals[cat]["total"] += txn.amount
        category_totals[cat]["count"] += 1

    total_spending = abs(sum(c["total"] for c in category_totals.values()))

    categories = [{
        "category": cat.value,
        "display": get_category_display_name(cat),
        "emoji": get_category_emoji(cat),
        "parent": get_parent_category(cat),
        "amount": abs(data["total"]),  # Convert to positive for display
        "count": data["count"],
        "percentage": (abs(data["total"]) / total_spending * 100) if total_spending > 0 else 0
    } for cat, data in category_totals.items()]

    categories.sort(key=lambda x: x["amount"], reverse=True)

    # Group by parent category
    by_parent = {}
    for cat in categories:
        parent = cat["parent"]
        if parent not in by_parent:
            by_parent[parent] = {"amount": 0, "categories": []}
        by_parent[parent]["amount"] += cat["amount"]
        by_parent[parent]["categories"].append(cat)

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "total": total_spending,
        "by_category": categories,
        "by_parent": by_parent
    }


@app.get("/api/spending/by-vendor")
async def get_spending_by_vendor(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(15, le=50),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get spending aggregated by vendor/merchant"""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    # Get all spending transactions (negative amounts = expenses)
    transactions = db.query(Transaction).join(Account).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.amount < 0,
        Transaction.is_excluded == False,
        Account.account_type.in_(SPENDING_ACCOUNT_TYPES)
    ).all()

    # Aggregate by merchant name
    vendor_totals = {}
    for txn in transactions:
        # Always include peer-to-peer payments (Venmo, Zelle, etc.) as real spending
        is_peer = is_peer_payment(txn.name)
        if not is_peer:
            # Skip transfers
            if txn.category in (TransactionCategory.FINANCIAL_TRANSFER, TransactionCategory.FINANCIAL_INVESTMENT):
                continue
            if is_transfer_transaction(txn.name) or is_transfer_transaction(txn.merchant_name):
                continue

        # Use merchant_name if available, otherwise extract from transaction name
        vendor = txn.merchant_name or txn.name.split()[0] if txn.name else "Unknown"

        # Normalize common vendor names
        vendor_lower = vendor.lower()
        if 'amazon' in vendor_lower:
            vendor = 'Amazon'
        elif 'doordash' in vendor_lower or vendor_lower.startswith('dd '):
            vendor = 'DoorDash'
        elif 'uber' in vendor_lower and 'eats' in vendor_lower:
            vendor = 'Uber Eats'
        elif 'shipt' in vendor_lower:
            vendor = 'Shipt'
        elif 'walmart' in vendor_lower:
            vendor = 'Walmart'
        elif 'target' in vendor_lower:
            vendor = 'Target'
        elif 'costco' in vendor_lower:
            vendor = 'Costco'
        elif 'starbucks' in vendor_lower:
            vendor = 'Starbucks'
        elif 'chick-fil-a' in vendor_lower or 'chickfila' in vendor_lower:
            vendor = 'Chick-fil-A'
        elif 'netflix' in vendor_lower:
            vendor = 'Netflix'
        elif 'spotify' in vendor_lower:
            vendor = 'Spotify'
        elif 'chevron' in vendor_lower:
            vendor = 'Chevron'
        elif 'shell' in vendor_lower:
            vendor = 'Shell'
        elif 'exxon' in vendor_lower:
            vendor = 'Exxon'

        if vendor not in vendor_totals:
            vendor_totals[vendor] = {"total": 0, "count": 0}
        vendor_totals[vendor]["total"] += txn.amount
        vendor_totals[vendor]["count"] += 1

    # Convert to list and sort by amount
    vendors = [{
        "vendor": vendor,
        "amount": abs(data["total"]),
        "count": data["count"]
    } for vendor, data in vendor_totals.items()]

    vendors.sort(key=lambda x: x["amount"], reverse=True)

    total_spending = sum(v["amount"] for v in vendors)

    # Add percentage and limit results
    for v in vendors:
        v["percentage"] = (v["amount"] / total_spending * 100) if total_spending > 0 else 0

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "total": total_spending,
        "vendors": vendors[:limit]
    }


# Patterns to exclude from spending/income (transfers, credit card payments)
TRANSFER_PATTERNS = [
    '%transfer%',
    '%payment thank you%',
    '%credit crd%epay%',
    '%mobile pmt%',
    '%mobile pymt%',
    '%autopay%',
    '%payment to%card%',
    '%payment from%',
    '%online banking transfer%',
]


def is_peer_payment(name: str) -> bool:
    """Check if transaction is a peer-to-peer payment (Venmo, Zelle, PayPal, CashApp)

    These should count as real spending since they're payments to other people,
    not transfers between your own accounts.
    """
    name_lower = name.lower() if name else ""
    peer_services = ['venmo', 'zelle', 'paypal', 'cash app', 'cashapp']
    return any(svc in name_lower for svc in peer_services)


def is_transfer_transaction(name: str) -> bool:
    """Check if transaction name matches transfer patterns"""
    name_lower = name.lower() if name else ""
    transfer_keywords = [
        'transfer', 'payment thank you', 'credit crd', 'epay',
        'mobile pmt', 'mobile pymt', 'autopay', 'payment to', 'payment from',
        'online banking', 'xfer', 'ach credit', 'ach debit',
        # Credit card payment patterns
        'syf paymnt', 'syf payment',  # Synchrony Financial (store cards like Amazon, Lowe's)
        'onetimepayment', 'one time payment',  # Common store card payment
        'des:payment', 'des:paymnt',  # ACH payment description
        'online pymt', 'pymt-thank you',  # Generic credit card payments
        'capital one mobile pymt',  # Capital One payments
    ]
    return any(kw in name_lower for kw in transfer_keywords)


@app.get("/api/spending/trends")
async def get_spending_trends(
    months: Optional[int] = Query(None, le=24),
    days: Optional[int] = Query(None, le=365),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get monthly spending trends. Can specify either months or days."""
    trends = []

    # Account types for income: only checking/savings where real payroll/deposits come in
    INCOME_ACCOUNT_TYPES = [AccountType.CHECKING, AccountType.SAVINGS]

    # Calculate the actual date range
    end_date = date.today()
    if days is not None:
        start_date = end_date - timedelta(days=days)
    elif months is not None:
        # For months parameter, calculate based on days for partial month support
        # months=1 means ~30 days, months=3 means ~90 days, etc.
        approx_days = months * 30
        start_date = end_date - timedelta(days=approx_days)
    else:
        start_date = end_date - timedelta(days=180)  # Default 6 months

    # Build list of months with partial date ranges
    month_ranges = []
    current = start_date
    while current <= end_date:
        # Month start is either the 1st or the start_date if it's the first month
        if current.year == start_date.year and current.month == start_date.month:
            range_start = start_date
        else:
            range_start = current.replace(day=1)

        # Month end is either the last day of month or end_date if it's the last month
        if current.month == 12:
            last_day = current.replace(year=current.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = current.replace(month=current.month + 1, day=1) - timedelta(days=1)

        if current.year == end_date.year and current.month == end_date.month:
            range_end = end_date
        else:
            range_end = last_day

        month_ranges.append({
            "year": current.year,
            "month": current.month,
            "range_start": range_start,
            "range_end": range_end,
            "is_partial": range_start.day > 1 or range_end < last_day
        })

        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1, day=1)
        else:
            current = current.replace(month=current.month + 1, day=1)

    # Calculate spending/income for each month range
    for mr in month_ranges:
        range_start = mr["range_start"]
        range_end = mr["range_end"]

        # Get spending transactions (negative amounts from all spending accounts)
        spending_txns = db.query(Transaction).join(Account).filter(
            Transaction.date >= range_start,
            Transaction.date <= range_end,
            Transaction.is_excluded == False,
            Transaction.amount < 0,
            Account.account_type.in_(SPENDING_ACCOUNT_TYPES)
        ).all()

        # Get income transactions (positive amounts from checking/savings only, not credit)
        income_txns = db.query(Transaction).join(Account).filter(
            Transaction.date >= range_start,
            Transaction.date <= range_end,
            Transaction.is_excluded == False,
            Transaction.amount > 0,
            Account.account_type.in_(INCOME_ACCOUNT_TYPES)
        ).all()

        # Calculate spending, excluding transfers (but include peer payments like Venmo)
        spending = 0
        for txn in spending_txns:
            # Always include peer-to-peer payments (Venmo, Zelle, etc.) as real spending
            if is_peer_payment(txn.name):
                spending += abs(txn.amount)
                continue
            # Skip internal transfers and credit card payments
            if is_transfer_transaction(txn.name) or is_transfer_transaction(txn.merchant_name):
                continue
            if txn.category in (TransactionCategory.FINANCIAL_TRANSFER, TransactionCategory.FINANCIAL_INVESTMENT):
                continue
            spending += abs(txn.amount)

        # Calculate income, excluding transfers and investment-related
        # But include Zelle payments from others (that's real income)
        income = 0
        for txn in income_txns:
            # Zelle payments FROM others are real income, not transfers
            name_lower = (txn.name or "").lower()
            if "zelle" in name_lower and "payment from" in name_lower:
                income += txn.amount
                continue
            if is_transfer_transaction(txn.name) or is_transfer_transaction(txn.merchant_name):
                continue
            if txn.category == TransactionCategory.FINANCIAL_INVESTMENT:
                continue
            income += txn.amount

        # Format month name with partial indicator
        month_name = date(mr["year"], mr["month"], 1).strftime("%B %Y")
        if mr["is_partial"]:
            month_name = f"{month_name} (partial)"

        trends.append({
            "month": f"{mr['year']}-{mr['month']:02d}",
            "month_name": month_name,
            "month_start": range_start.isoformat(),
            "month_end": range_end.isoformat(),
            "spending": spending,
            "income": income,
            "net": income - spending
        })

    return trends


# ============== Categories Endpoint ==============

@app.get("/api/categories")
async def get_categories(_auth: bool = Depends(require_auth)):
    """Get all available transaction categories for dropdowns"""
    # Skip duplicate subscription categories - only show one "Subscriptions" option
    skip_categories = {"subscription_software", "subscription_other"}

    categories = []
    for cat in TransactionCategory:
        if cat.value in skip_categories:
            continue
        categories.append({
            "value": cat.value,
            "display": get_category_display_name(cat),
            "emoji": get_category_emoji(cat),
            "parent": get_parent_category(cat)
        })
    # Sort by parent category, then display name
    categories.sort(key=lambda c: (c["parent"], c["display"]))
    return categories


# ============== Holdings/Investments Endpoints ==============

@app.get("/api/holdings")
async def get_holdings(db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    """Get all investment holdings"""
    holdings = db.query(Holding).all()

    total_value = sum(h.current_value or 0 for h in holdings)

    return {
        "total_value": total_value,
        "holdings": [{
            "id": h.id,
            "account_id": h.account_id,
            "account_name": h.account.name if h.account else None,
            "security_name": h.security_name,
            "ticker": h.ticker,
            "type": h.security_type,
            "quantity": h.quantity,
            "cost_basis": h.cost_basis,
            "current_price": h.current_price,
            "current_value": h.current_value,
            "gain_loss": (h.current_value - h.cost_basis) if h.cost_basis else None,
            "gain_loss_pct": ((h.current_value - h.cost_basis) / h.cost_basis * 100) if h.cost_basis and h.cost_basis > 0 else None
        } for h in holdings]
    }


@app.get("/api/investments/summary")
async def get_investment_summary(
    days: int = Query(90, le=365),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get comprehensive investment portfolio summary"""
    # Get all investment accounts
    investment_accounts = db.query(Account).filter(
        Account.account_type.in_(INVESTMENT_ACCOUNT_TYPES),
        Account.is_active == True
    ).all()

    # Get all holdings (may be empty if SimpleFIN doesn't provide them)
    holdings = db.query(Holding).join(Account).filter(
        Account.account_type.in_(INVESTMENT_ACCOUNT_TYPES)
    ).all()

    # If we have holdings, use them for detailed breakdown
    # Otherwise, fall back to account balances
    has_holdings = len(holdings) > 0

    if has_holdings:
        # Calculate totals from holdings
        total_value = sum(h.current_value or 0 for h in holdings)
        total_cost_basis = sum(h.cost_basis or 0 for h in holdings if h.cost_basis)

        # Group by account from holdings
        by_account = {}
        for h in holdings:
            account_name = h.account.name if h.account else "Unknown"
            account_type = h.account.account_type.value if h.account else "other"
            key = f"{h.account_id}"
            if key not in by_account:
                by_account[key] = {
                    "account_id": h.account_id,
                    "account_name": account_name,
                    "account_type": account_type,
                    "institution": h.account.institution.name if h.account and h.account.institution else None,
                    "value": 0,
                    "cost_basis": 0,
                    "holdings_count": 0
                }
            by_account[key]["value"] += h.current_value or 0
            by_account[key]["cost_basis"] += h.cost_basis or 0
            by_account[key]["holdings_count"] += 1

        # Group by security type
        by_type = {}
        for h in holdings:
            sec_type = h.security_type or "Other"
            if sec_type not in by_type:
                by_type[sec_type] = {"type": sec_type, "value": 0, "count": 0}
            by_type[sec_type]["value"] += h.current_value or 0
            by_type[sec_type]["count"] += 1

        types_list = sorted(by_type.values(), key=lambda x: x["value"], reverse=True)

        # Top holdings
        top_holdings = sorted(holdings, key=lambda h: h.current_value or 0, reverse=True)[:10]
        top_holdings_list = [{
            "security_name": h.security_name,
            "ticker": h.ticker,
            "value": h.current_value,
            "cost_basis": h.cost_basis,
            "gain_loss": (h.current_value - h.cost_basis) if h.cost_basis else None,
            "gain_loss_pct": ((h.current_value - h.cost_basis) / h.cost_basis * 100) if h.cost_basis and h.cost_basis > 0 else None,
            "allocation_pct": (h.current_value / total_value * 100) if total_value > 0 else 0
        } for h in top_holdings]
    else:
        # No holdings - use account balances instead
        total_value = sum(acc.current_balance or 0 for acc in investment_accounts)
        total_cost_basis = None  # Can't calculate without holdings

        # Build account list from accounts directly
        by_account = {}
        for acc in investment_accounts:
            by_account[str(acc.id)] = {
                "account_id": acc.id,
                "account_name": acc.name,
                "account_type": acc.account_type.value,
                "institution": acc.institution.name if acc.institution else None,
                "value": acc.current_balance or 0,
                "cost_basis": None,
                "holdings_count": 0
            }

        types_list = []  # No breakdown without holdings
        top_holdings_list = []  # No individual holdings

    # Get historical balances for period change calculation
    period_start = date.today() - timedelta(days=days)

    # Get the earliest balance for each account within the period
    from sqlalchemy import and_
    start_balances = {}
    for acc_id in by_account.keys():
        earliest_balance = db.query(BalanceHistory).filter(
            BalanceHistory.account_id == int(acc_id),
            BalanceHistory.date >= period_start
        ).order_by(BalanceHistory.date.asc()).first()

        if earliest_balance:
            start_balances[acc_id] = earliest_balance.balance

    # Calculate period change for each account
    accounts_list = []
    total_period_change = 0
    total_period_start_value = 0

    for acc in by_account.values():
        acc_id = str(acc["account_id"])
        current_value = acc["value"]

        if acc_id in start_balances:
            start_value = start_balances[acc_id]
            period_change = current_value - start_value
            period_change_pct = (period_change / start_value * 100) if start_value != 0 else None
            acc["period_change"] = round(period_change, 2)
            acc["period_change_pct"] = round(period_change_pct, 2) if period_change_pct is not None else None
            total_period_change += period_change
            total_period_start_value += start_value
        else:
            acc["period_change"] = None
            acc["period_change_pct"] = None

        accounts_list.append(acc)

    # Sort by value descending
    accounts_list.sort(key=lambda x: x["value"], reverse=True)

    # Calculate overall period change
    total_period_change_pct = (total_period_change / total_period_start_value * 100) if total_period_start_value > 0 else None

    return {
        "total_value": total_value,
        "total_period_change": round(total_period_change, 2) if total_period_start_value > 0 else None,
        "total_period_change_pct": round(total_period_change_pct, 2) if total_period_change_pct is not None else None,
        "accounts_count": len(investment_accounts),
        "holdings_count": len(holdings),
        "has_holdings": has_holdings,
        "by_account": accounts_list,
        "by_type": types_list,
        "top_holdings": top_holdings_list
    }


@app.get("/api/investments/history")
async def get_investment_history(
    days: int = Query(90, le=365),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get historical investment portfolio value for charting"""
    start_date = date.today() - timedelta(days=days)

    # Get balance history for investment accounts
    history = db.query(
        BalanceHistory.date,
        func.sum(BalanceHistory.balance).label('total_value')
    ).join(Account).filter(
        Account.account_type.in_(INVESTMENT_ACCOUNT_TYPES),
        BalanceHistory.date >= start_date
    ).group_by(BalanceHistory.date).order_by(BalanceHistory.date).all()

    if not history:
        return {"history": [], "change": None, "change_pct": None}

    history_list = [{"date": h.date.isoformat(), "value": h.total_value} for h in history]

    # Calculate change over period
    if len(history_list) >= 2:
        start_value = history_list[0]["value"]
        end_value = history_list[-1]["value"]
        change = end_value - start_value
        change_pct = (change / start_value * 100) if start_value > 0 else None
    else:
        change = None
        change_pct = None

    return {
        "history": history_list,
        "change": change,
        "change_pct": change_pct
    }


# ============== Transaction Rules Endpoints ==============

@app.get("/api/rules")
async def get_rules(db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    """Get all transaction categorization rules"""
    rules = db.query(TransactionRule).order_by(
        TransactionRule.priority.desc(),
        TransactionRule.name
    ).all()

    return [{
        "id": r.id,
        "name": r.name,
        "match_field": r.match_field,
        "match_type": r.match_type,
        "match_value": r.match_value,
        "case_sensitive": r.case_sensitive,
        "account_type": r.account_type,
        "assign_category": r.assign_category.value,
        "assign_category_display": get_category_display_name(r.assign_category),
        "priority": r.priority,
        "is_active": r.is_active,
        "created_at": r.created_at.isoformat() if r.created_at else None
    } for r in rules]


@app.post("/api/rules")
async def create_rule(
    rule: TransactionRuleCreate,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Create a new transaction categorization rule"""
    try:
        category = TransactionCategory(rule.assign_category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {rule.assign_category}")

    if rule.match_field not in ['name', 'merchant_name', 'any']:
        raise HTTPException(status_code=400, detail="match_field must be 'name', 'merchant_name', or 'any'")

    if rule.match_type not in ['contains', 'starts_with', 'ends_with', 'exact']:
        raise HTTPException(status_code=400, detail="match_type must be 'contains', 'starts_with', 'ends_with', or 'exact'")

    new_rule = TransactionRule(
        name=rule.name,
        match_field=rule.match_field,
        match_type=rule.match_type,
        match_value=rule.match_value,
        case_sensitive=rule.case_sensitive,
        account_type=rule.account_type,
        assign_category=category,
        priority=rule.priority
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)

    return {
        "id": new_rule.id,
        "name": new_rule.name,
        "match_field": new_rule.match_field,
        "match_type": new_rule.match_type,
        "match_value": new_rule.match_value,
        "assign_category": new_rule.assign_category.value,
        "message": "Rule created successfully"
    }


@app.patch("/api/rules/{rule_id}")
async def update_rule(
    rule_id: int,
    updates: TransactionRuleUpdate,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Update a transaction rule"""
    rule = db.query(TransactionRule).filter(TransactionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if updates.name is not None:
        rule.name = updates.name
    if updates.match_field is not None:
        rule.match_field = updates.match_field
    if updates.match_type is not None:
        rule.match_type = updates.match_type
    if updates.match_value is not None:
        rule.match_value = updates.match_value
    if updates.case_sensitive is not None:
        rule.case_sensitive = updates.case_sensitive
    if updates.account_type is not None:
        rule.account_type = updates.account_type if updates.account_type != '' else None
    if updates.assign_category is not None:
        try:
            rule.assign_category = TransactionCategory(updates.assign_category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {updates.assign_category}")
    if updates.priority is not None:
        rule.priority = updates.priority
    if updates.is_active is not None:
        rule.is_active = updates.is_active

    db.commit()
    return {"message": "Rule updated successfully"}


@app.delete("/api/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Delete a transaction rule"""
    rule = db.query(TransactionRule).filter(TransactionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()
    return {"message": "Rule deleted successfully"}


@app.post("/api/rules/{rule_id}/apply")
async def apply_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Apply a rule to all existing transactions that match"""
    from categorizer import apply_single_rule

    rule = db.query(TransactionRule).filter(TransactionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Get transactions that don't have user overrides
    query = db.query(Transaction).join(Account).filter(
        Transaction.user_category == None
    )

    # Filter by account type if specified
    if rule.account_type == 'spending':
        query = query.filter(Account.account_type.in_(SPENDING_ACCOUNT_TYPES))
    elif rule.account_type == 'investment':
        query = query.filter(Account.account_type.in_(INVESTMENT_ACCOUNT_TYPES))

    transactions = query.all()
    updated_count = 0

    for txn in transactions:
        if apply_single_rule(rule, txn.name, txn.merchant_name):
            txn.category = rule.assign_category
            updated_count += 1

    db.commit()

    return {
        "message": f"Rule applied to {updated_count} transactions",
        "updated_count": updated_count
    }


@app.get("/api/rules/test")
async def test_rule(
    match_field: str,
    match_type: str,
    match_value: str,
    case_sensitive: bool = False,
    limit: int = 10,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Test a rule pattern against existing transactions"""
    from categorizer import apply_single_rule_params

    transactions = db.query(Transaction).order_by(desc(Transaction.date)).limit(500).all()
    matches = []

    for txn in transactions:
        if apply_single_rule_params(match_field, match_type, match_value, case_sensitive, txn.name, txn.merchant_name):
            matches.append({
                "id": txn.id,
                "date": txn.date.isoformat() if txn.date else None,
                "name": txn.name,
                "merchant_name": txn.merchant_name,
                "current_category": txn.category.value if txn.category else None
            })
            if len(matches) >= limit:
                break

    return {
        "matches": matches,
        "match_count": len(matches)
    }


# ============== Subscriptions Endpoints ==============

def normalize_merchant_name(name: str) -> str:
    """Normalize merchant name for grouping"""
    if not name:
        return ""
    name_lower = name.lower().strip()

    # Common normalizations
    normalizations = {
        'netflix': ['netflix'],
        'spotify': ['spotify'],
        'amazon prime': ['amazon prime', 'prime video', 'amzn prime'],
        'amazon': ['amazon', 'amzn'],
        'hulu': ['hulu'],
        'disney+': ['disney+', 'disney plus', 'disneyplus'],
        'apple': ['apple.com', 'apple music', 'icloud'],
        'google': ['google', 'youtube premium', 'youtube music'],
        'microsoft': ['microsoft', 'xbox', 'office 365'],
        'adobe': ['adobe'],
        'dropbox': ['dropbox'],
        'github': ['github'],
        'aws': ['aws', 'amazon web services'],
        'doordash': ['doordash', 'dashpass'],
        'instacart': ['instacart'],
        'costco': ['costco'],
        'sam\'s club': ['sam\'s club', 'sams club'],
        'planet fitness': ['planet fitness'],
        'anytime fitness': ['anytime fitness'],
    }

    for normalized, patterns in normalizations.items():
        for pattern in patterns:
            if pattern in name_lower:
                return normalized

    # Default: return first word or cleaned name
    return name_lower.split()[0] if name_lower else name_lower


def detect_billing_cycle(intervals: List[int]) -> Optional[str]:
    """Detect billing cycle from list of day intervals between charges"""
    if not intervals:
        return None

    avg_interval = sum(intervals) / len(intervals)

    # Check for weekly (5-9 days)
    if 5 <= avg_interval <= 9:
        return "weekly"
    # Check for bi-weekly (12-16 days)
    elif 12 <= avg_interval <= 16:
        return "biweekly"
    # Check for monthly (25-35 days)
    elif 25 <= avg_interval <= 35:
        return "monthly"
    # Check for quarterly (80-100 days)
    elif 80 <= avg_interval <= 100:
        return "quarterly"
    # Check for semi-annual (170-200 days)
    elif 170 <= avg_interval <= 200:
        return "semiannual"
    # Check for annual (340-390 days) - widened range
    elif 340 <= avg_interval <= 390:
        return "annual"

    return None


def calculate_next_charge_date(last_date: date, billing_cycle: str) -> date:
    """Calculate the next expected charge date based on billing cycle"""
    if not last_date:
        return None

    cycle_days = {
        "weekly": 7,
        "biweekly": 14,
        "monthly": 30,
        "quarterly": 91,
        "semiannual": 182,
        "annual": 365
    }

    days = cycle_days.get(billing_cycle, 30)
    next_date = last_date + timedelta(days=days)

    # If next date is in the past, advance to next occurrence
    today = date.today()
    while next_date < today:
        next_date += timedelta(days=days)

    return next_date


def get_monthly_equivalent(amount: float, billing_cycle: str) -> float:
    """Convert any billing cycle amount to monthly equivalent"""
    multipliers = {
        "weekly": 4.33,
        "biweekly": 2.17,
        "monthly": 1,
        "quarterly": 1/3,
        "semiannual": 1/6,
        "annual": 1/12
    }
    return round(amount * multipliers.get(billing_cycle, 1), 2)


def get_annual_equivalent(amount: float, billing_cycle: str) -> float:
    """Convert any billing cycle amount to annual equivalent"""
    multipliers = {
        "weekly": 52,
        "biweekly": 26,
        "monthly": 12,
        "quarterly": 4,
        "semiannual": 2,
        "annual": 1
    }
    return round(amount * multipliers.get(billing_cycle, 12), 2)


@app.get("/api/subscriptions")
async def get_subscriptions(
    include_dismissed: bool = False,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get all subscriptions (confirmed and detected)"""
    query = db.query(Subscription).filter(Subscription.is_active == True)
    if not include_dismissed:
        query = query.filter(Subscription.is_dismissed == False)

    subscriptions = query.order_by(Subscription.is_confirmed.desc(), Subscription.name).all()

    today = date.today()
    result = []

    for sub in subscriptions:
        # Calculate next charge date if not set
        next_date = sub.next_expected_date
        if not next_date and sub.last_charge_date:
            next_date = calculate_next_charge_date(sub.last_charge_date, sub.billing_cycle)

        days_until = (next_date - today).days if next_date else None

        result.append({
            "id": sub.id,
            "name": sub.name,
            "merchant_pattern": sub.merchant_pattern,
            "expected_amount": sub.expected_amount,
            "billing_cycle": sub.billing_cycle,
            "category": sub.category.value if sub.category else "subscription_other",
            "category_display": get_category_display_name(sub.category) if sub.category else "Other Subscription",
            "is_active": sub.is_active,
            "is_confirmed": sub.is_confirmed,
            "last_charge_date": sub.last_charge_date.isoformat() if sub.last_charge_date else None,
            "last_charge_amount": sub.last_charge_amount,
            "next_expected_date": next_date.isoformat() if next_date else None,
            "days_until_charge": days_until,
            "monthly_equivalent": get_monthly_equivalent(sub.expected_amount, sub.billing_cycle),
            "annual_equivalent": get_annual_equivalent(sub.expected_amount, sub.billing_cycle),
            "amount_changed": sub.last_charge_amount and abs(sub.last_charge_amount - sub.expected_amount) > 0.50
        })

    return result


@app.get("/api/subscriptions/summary")
async def get_subscriptions_summary(db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    """Get subscription summary with monthly and annual totals"""
    subscriptions = db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.is_confirmed == True,
        Subscription.is_dismissed == False
    ).all()

    monthly_total = 0
    annual_total = 0

    for sub in subscriptions:
        monthly_total += get_monthly_equivalent(sub.expected_amount, sub.billing_cycle)
        annual_total += get_annual_equivalent(sub.expected_amount, sub.billing_cycle)

    # Calculate upcoming charges (next 7 and 30 days)
    today = date.today()
    next_week = today + timedelta(days=7)
    next_month = today + timedelta(days=30)

    upcoming_week = []
    upcoming_month = []

    for sub in subscriptions:
        # Calculate next charge date if not set
        next_date = sub.next_expected_date
        if not next_date and sub.last_charge_date:
            next_date = calculate_next_charge_date(sub.last_charge_date, sub.billing_cycle)

        if next_date:
            if today <= next_date <= next_week:
                upcoming_week.append({
                    "id": sub.id,
                    "name": sub.name,
                    "amount": sub.expected_amount,
                    "date": next_date.isoformat(),
                    "days_until": (next_date - today).days
                })
            elif today <= next_date <= next_month:
                upcoming_month.append({
                    "id": sub.id,
                    "name": sub.name,
                    "amount": sub.expected_amount,
                    "date": next_date.isoformat(),
                    "days_until": (next_date - today).days
                })

    # Sort by date
    upcoming_week.sort(key=lambda x: x["days_until"])
    upcoming_month.sort(key=lambda x: x["days_until"])

    return {
        "monthly_total": round(monthly_total, 2),
        "annual_total": round(annual_total, 2),
        "subscription_count": len(subscriptions),
        "upcoming_week": upcoming_week,
        "upcoming_week_total": round(sum(u["amount"] for u in upcoming_week), 2),
        "upcoming_month": upcoming_month,
        "upcoming_month_total": round(sum(u["amount"] for u in upcoming_month), 2),
        "subscriptions": [{
            "name": sub.name,
            "amount": sub.expected_amount,
            "cycle": sub.billing_cycle,
            "monthly_equivalent": get_monthly_equivalent(sub.expected_amount, sub.billing_cycle),
            "annual_equivalent": get_annual_equivalent(sub.expected_amount, sub.billing_cycle)
        } for sub in subscriptions]
    }


@app.post("/api/subscriptions/detect")
async def detect_subscriptions(
    days: int = Query(365, le=730),  # Default to 1 year for better annual detection
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Auto-detect recurring subscriptions from transaction history"""
    start_date = date.today() - timedelta(days=days)

    # Get spending transactions
    transactions = db.query(Transaction).join(Account).filter(
        Transaction.date >= start_date,
        Transaction.amount < 0,  # Expenses only
        Account.account_type.in_(SPENDING_ACCOUNT_TYPES)
    ).order_by(Transaction.date).all()

    # Group by normalized merchant name
    by_merchant = {}
    for txn in transactions:
        merchant = normalize_merchant_name(txn.merchant_name or txn.name)
        if not merchant:
            continue
        if merchant not in by_merchant:
            by_merchant[merchant] = []
        by_merchant[merchant].append(txn)

    # Get ALL subscriptions (confirmed AND dismissed) to avoid duplicates
    all_subs = db.query(Subscription).all()
    # Build sets for both confirmed and dismissed patterns
    existing_patterns = {sub.merchant_pattern.lower() for sub in all_subs if not sub.is_dismissed}
    dismissed_patterns = {sub.merchant_pattern.lower() for sub in all_subs if sub.is_dismissed}
    all_excluded_patterns = existing_patterns | dismissed_patterns

    def is_pattern_match(merchant: str, patterns: set) -> bool:
        """Check if merchant matches any pattern (partial matching)"""
        merchant_lower = merchant.lower()
        for pattern in patterns:
            # Exact match
            if merchant_lower == pattern:
                return True
            # Merchant contains pattern or pattern contains merchant
            if pattern in merchant_lower or merchant_lower in pattern:
                return True
            # Word overlap (for cases like "youtube premium" vs "youtube tv")
            merchant_words = set(merchant_lower.split())
            pattern_words = set(pattern.split())
            # If they share significant words (excluding common words)
            common_words = {'the', 'inc', 'llc', 'ltd', 'co', 'corp'}
            shared = (merchant_words & pattern_words) - common_words
            if shared and len(shared) >= 1:
                # Check if the shared word is significant (not just "the", etc.)
                significant_shared = any(len(w) > 3 for w in shared)
                if significant_shared:
                    return True
        return False

    detected = []
    for merchant, txns in by_merchant.items():
        # Skip if already tracked or dismissed
        if is_pattern_match(merchant, all_excluded_patterns):
            continue

        # Need at least 2 transactions for most cycles, but allow 1 for potential annuals
        if len(txns) < 1:
            continue

        # Check amount consistency (within 20% tolerance for flexibility)
        amounts = [abs(t.amount) for t in txns]
        avg_amount = sum(amounts) / len(amounts)

        # Skip very small amounts (under $1)
        if avg_amount < 1:
            continue

        # Calculate intervals between charges
        sorted_txns = sorted(txns, key=lambda t: t.date)

        # For single transactions, check if it looks like an annual subscription
        if len(txns) == 1:
            # Check if transaction is from ~1 year ago (could be annual)
            days_ago = (date.today() - sorted_txns[0].date).days
            # If it's between 11-13 months old and a "subscription-like" amount
            if 330 <= days_ago <= 400 and avg_amount >= 20:
                detected.append({
                    "merchant": merchant.title(),
                    "merchant_pattern": merchant,
                    "amount": round(avg_amount, 2),
                    "billing_cycle": "annual",
                    "transaction_count": len(txns),
                    "last_charge_date": sorted_txns[-1].date.isoformat(),
                    "last_charge_amount": abs(sorted_txns[-1].amount),
                    "next_expected_date": calculate_next_charge_date(sorted_txns[-1].date, "annual").isoformat(),
                    "confidence": 0.5,  # Lower confidence for single transactions
                    "monthly_equivalent": get_monthly_equivalent(avg_amount, "annual"),
                    "annual_equivalent": avg_amount
                })
            continue

        # Skip if amounts vary too much (20% tolerance)
        amount_variance = [abs(a - avg_amount) / avg_amount for a in amounts if avg_amount > 0]
        if amount_variance and max(amount_variance) > 0.20:
            continue

        intervals = []
        for i in range(1, len(sorted_txns)):
            delta = (sorted_txns[i].date - sorted_txns[i-1].date).days
            intervals.append(delta)

        # Detect billing cycle
        cycle = detect_billing_cycle(intervals)
        if not cycle:
            continue

        # Calculate next expected date
        last_date = sorted_txns[-1].date
        next_date = calculate_next_charge_date(last_date, cycle)

        # Calculate confidence based on number of transactions and consistency
        confidence = min(len(txns) / 4, 1.0)
        if len(set(intervals)) == 1:  # Perfect consistency
            confidence = min(confidence + 0.2, 1.0)

        detected.append({
            "merchant": merchant.title(),
            "merchant_pattern": merchant,
            "amount": round(avg_amount, 2),
            "billing_cycle": cycle,
            "transaction_count": len(txns),
            "last_charge_date": sorted_txns[-1].date.isoformat(),
            "last_charge_amount": abs(sorted_txns[-1].amount),
            "next_expected_date": next_date.isoformat() if next_date else None,
            "confidence": round(confidence, 2),
            "monthly_equivalent": get_monthly_equivalent(avg_amount, cycle),
            "annual_equivalent": get_annual_equivalent(avg_amount, cycle)
        })

    # Sort by confidence and amount
    detected.sort(key=lambda x: (-x["confidence"], -x["amount"]))

    return {
        "detected_count": len(detected),
        "subscriptions": detected
    }


@app.post("/api/subscriptions")
async def create_subscription(
    sub: SubscriptionCreate,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Manually create a subscription"""
    try:
        category = TransactionCategory(sub.category) if sub.category else TransactionCategory.SUBSCRIPTION_OTHER
    except ValueError:
        category = TransactionCategory.SUBSCRIPTION_OTHER

    new_sub = Subscription(
        name=sub.name,
        merchant_pattern=sub.merchant_pattern.lower(),
        expected_amount=sub.expected_amount,
        billing_cycle=sub.billing_cycle,
        category=category,
        is_confirmed=True  # Manually created = confirmed
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)

    return {
        "id": new_sub.id,
        "name": new_sub.name,
        "message": "Subscription created successfully"
    }


@app.post("/api/subscriptions/confirm")
async def confirm_detected_subscription(
    name: str,
    merchant_pattern: str,
    expected_amount: float,
    billing_cycle: str = "monthly",
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Confirm a detected subscription (creates it as confirmed)"""
    # Check if already exists
    existing = db.query(Subscription).filter(
        Subscription.merchant_pattern == merchant_pattern.lower()
    ).first()

    if existing:
        existing.is_confirmed = True
        existing.is_dismissed = False
        existing.expected_amount = expected_amount
        existing.billing_cycle = billing_cycle
        db.commit()
        return {"id": existing.id, "message": "Subscription confirmed"}

    new_sub = Subscription(
        name=name,
        merchant_pattern=merchant_pattern.lower(),
        expected_amount=expected_amount,
        billing_cycle=billing_cycle,
        category=TransactionCategory.SUBSCRIPTION_OTHER,
        is_confirmed=True
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)

    return {"id": new_sub.id, "message": "Subscription confirmed"}


@app.patch("/api/subscriptions/{subscription_id}")
async def update_subscription(
    subscription_id: int,
    updates: SubscriptionUpdate,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Update a subscription"""
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if updates.name is not None:
        sub.name = updates.name
    if updates.merchant_pattern is not None:
        sub.merchant_pattern = updates.merchant_pattern.lower()
    if updates.expected_amount is not None:
        sub.expected_amount = updates.expected_amount
    if updates.billing_cycle is not None:
        sub.billing_cycle = updates.billing_cycle
    if updates.category is not None:
        try:
            sub.category = TransactionCategory(updates.category)
        except ValueError:
            pass
    if updates.is_active is not None:
        sub.is_active = updates.is_active
    if updates.is_confirmed is not None:
        sub.is_confirmed = updates.is_confirmed

    db.commit()
    return {"message": "Subscription updated"}


@app.delete("/api/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    dismiss: bool = False,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Delete or dismiss a subscription"""
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if dismiss:
        # Mark as dismissed so it won't be detected again
        sub.is_dismissed = True
        sub.is_active = False
        db.commit()
        return {"message": "Subscription dismissed"}
    else:
        db.delete(sub)
        db.commit()
        return {"message": "Subscription deleted"}


@app.get("/api/subscriptions/{subscription_id}/transactions")
async def get_subscription_transactions(
    subscription_id: int,
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get transaction history for a subscription"""
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Find transactions matching the merchant pattern
    pattern = f"%{sub.merchant_pattern}%"
    transactions = db.query(Transaction).join(Account).filter(
        Transaction.amount < 0,  # Expenses only
        Account.account_type.in_(SPENDING_ACCOUNT_TYPES),
        (Transaction.merchant_name.ilike(pattern)) | (Transaction.name.ilike(pattern))
    ).order_by(desc(Transaction.date)).limit(limit).all()

    return {
        "subscription": {
            "id": sub.id,
            "name": sub.name,
            "expected_amount": sub.expected_amount,
            "billing_cycle": sub.billing_cycle
        },
        "transactions": [{
            "id": txn.id,
            "date": txn.date.isoformat() if txn.date else None,
            "name": txn.name,
            "merchant_name": txn.merchant_name,
            "amount": txn.amount,
            "account_name": txn.account.name if txn.account else None
        } for txn in transactions]
    }


@app.get("/api/subscriptions/pattern/{pattern}/transactions")
async def get_pattern_transactions(
    pattern: str,
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth)
):
    """Get transaction history for a merchant pattern (for detected subscriptions)"""
    search_pattern = f"%{pattern}%"
    transactions = db.query(Transaction).join(Account).filter(
        Transaction.amount < 0,
        Account.account_type.in_(SPENDING_ACCOUNT_TYPES),
        (Transaction.merchant_name.ilike(search_pattern)) | (Transaction.name.ilike(search_pattern))
    ).order_by(desc(Transaction.date)).limit(limit).all()

    return {
        "pattern": pattern,
        "transactions": [{
            "id": txn.id,
            "date": txn.date.isoformat() if txn.date else None,
            "name": txn.name,
            "merchant_name": txn.merchant_name,
            "amount": txn.amount,
            "account_name": txn.account.name if txn.account else None
        } for txn in transactions]
    }


# ============== Serve Frontend ==============

@app.get("/")
async def serve_frontend():
    """Serve the PWA frontend"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Finance Tracker API", "docs": "/docs"}


@app.get("/{path:path}")
async def serve_frontend_routes(path: str):
    """Serve frontend for all other routes (SPA support)"""
    # Check if it's an API route
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    # Try to serve static file
    file_path = frontend_path / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # Otherwise serve index.html for SPA routing
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return {"message": "Finance Tracker API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
