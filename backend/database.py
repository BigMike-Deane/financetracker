"""
Database configuration and models for Finance Tracker
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "finance.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AccountType(enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"
    INVESTMENT = "investment"
    BROKERAGE = "brokerage"
    RETIREMENT = "retirement"  # 401k, IRA
    LOAN = "loan"
    MORTGAGE = "mortgage"
    OTHER = "other"


class TransactionCategory(enum.Enum):
    # Income
    INCOME_SALARY = "income_salary"
    INCOME_INVESTMENT = "income_investment"
    INCOME_TRANSFER = "income_transfer"
    INCOME_OTHER = "income_other"

    # Housing
    HOUSING_RENT = "housing_rent"
    HOUSING_MORTGAGE = "housing_mortgage"
    HOUSING_UTILITIES = "housing_utilities"
    HOUSING_MAINTENANCE = "housing_maintenance"

    # Transportation
    TRANSPORT_GAS = "transport_gas"
    TRANSPORT_PARKING = "transport_parking"
    TRANSPORT_PUBLIC = "transport_public"
    TRANSPORT_RIDESHARE = "transport_rideshare"
    TRANSPORT_MAINTENANCE = "transport_maintenance"

    # Food & Dining
    FOOD_GROCERIES = "food_groceries"
    FOOD_RESTAURANTS = "food_restaurants"
    FOOD_COFFEE = "food_coffee"
    FOOD_DELIVERY = "food_delivery"

    # Shopping
    SHOPPING_CLOTHING = "shopping_clothing"
    SHOPPING_ELECTRONICS = "shopping_electronics"
    SHOPPING_HOUSEHOLD = "shopping_household"
    SHOPPING_GENERAL = "shopping_general"

    # Entertainment
    ENTERTAINMENT_STREAMING = "entertainment_streaming"
    ENTERTAINMENT_GAMES = "entertainment_games"
    ENTERTAINMENT_EVENTS = "entertainment_events"
    ENTERTAINMENT_OTHER = "entertainment_other"

    # Health
    HEALTH_MEDICAL = "health_medical"
    HEALTH_PHARMACY = "health_pharmacy"
    HEALTH_FITNESS = "health_fitness"
    HEALTH_INSURANCE = "health_insurance"

    # Financial
    FINANCIAL_FEES = "financial_fees"
    FINANCIAL_INTEREST = "financial_interest"
    FINANCIAL_INVESTMENT = "financial_investment"
    FINANCIAL_TRANSFER = "financial_transfer"

    # Subscriptions
    SUBSCRIPTION_SOFTWARE = "subscription_software"
    SUBSCRIPTION_MEMBERSHIP = "subscription_membership"
    SUBSCRIPTION_OTHER = "subscription_other"

    # Other
    TRAVEL = "travel"
    EDUCATION = "education"
    GIFTS = "gifts"
    CHARITY = "charity"
    TAXES = "taxes"
    INSURANCE = "insurance"
    PET = "pet"
    UNCATEGORIZED = "uncategorized"


class Institution(Base):
    """Financial institution connected via SimpleFIN or manual entry"""
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    simplefin_id = Column(String, unique=True, index=True)  # SimpleFIN org domain/id
    simplefin_access_url = Column(String)  # SimpleFIN Access URL
    simplefin_org_id = Column(String)  # SimpleFIN org sfin-url or domain
    name = Column(String)  # e.g., "Chase", "Fidelity"
    logo_url = Column(String, nullable=True)
    primary_color = Column(String, nullable=True)
    provider = Column(String, default="simplefin")  # simplefin, manual

    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime, nullable=True)
    sync_status = Column(String, default="pending")  # pending, success, error
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="institution", cascade="all, delete-orphan")


class Account(Base):
    """Individual account within an institution"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    simplefin_account_id = Column(String, unique=True, index=True)

    name = Column(String)  # e.g., "Checking ...1234"
    official_name = Column(String, nullable=True)  # Full name from bank
    mask = Column(String, nullable=True)  # Last 4 digits

    account_type = Column(SQLEnum(AccountType), default=AccountType.OTHER)
    subtype = Column(String, nullable=True)  # Account subtype

    current_balance = Column(Float, default=0.0)
    available_balance = Column(Float, nullable=True)
    credit_limit = Column(Float, nullable=True)  # For credit cards

    currency = Column(String, default="USD")
    is_active = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)  # User can hide accounts

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    institution = relationship("Institution", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    balances = relationship("BalanceHistory", back_populates="account", cascade="all, delete-orphan")
    holdings = relationship("Holding", back_populates="account", cascade="all, delete-orphan")


class Transaction(Base):
    """Individual transaction"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    simplefin_transaction_id = Column(String, unique=True, index=True)

    date = Column(Date, index=True)
    authorized_date = Column(Date, nullable=True)

    name = Column(String)  # Merchant name
    merchant_name = Column(String, nullable=True)  # Clean merchant name

    amount = Column(Float)  # Negative = expense (money out), Positive = income (money in)
    currency = Column(String, default="USD")

    category = Column(SQLEnum(TransactionCategory), default=TransactionCategory.UNCATEGORIZED)
    original_category = Column(String, nullable=True)  # Original category from provider
    original_category_id = Column(String, nullable=True)

    is_pending = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    is_manual = Column(Boolean, default=False)  # User-created transaction

    # User overrides
    user_category = Column(SQLEnum(TransactionCategory), nullable=True)
    user_notes = Column(Text, nullable=True)
    is_excluded = Column(Boolean, default=False)  # Exclude from budgets

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="transactions")

    @property
    def effective_category(self):
        """Return user override if set, otherwise auto category"""
        return self.user_category if self.user_category else self.category


class BalanceHistory(Base):
    """Daily balance snapshots for net worth tracking"""
    __tablename__ = "balance_history"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    date = Column(Date, index=True)

    balance = Column(Float)
    available = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="balances")


class Holding(Base):
    """Investment holdings for brokerage/retirement accounts"""
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    simplefin_holding_id = Column(String, nullable=True)

    security_name = Column(String)
    ticker = Column(String, nullable=True, index=True)

    quantity = Column(Float)
    cost_basis = Column(Float, nullable=True)
    current_price = Column(Float)
    current_value = Column(Float)

    security_type = Column(String, nullable=True)  # stock, etf, mutual fund, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="holdings")


class NetWorthSnapshot(Base):
    """Daily net worth snapshots"""
    __tablename__ = "net_worth_history"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True)

    total_assets = Column(Float)
    total_liabilities = Column(Float)
    net_worth = Column(Float)

    # Breakdown by account type
    cash = Column(Float, default=0.0)  # Checking + Savings
    investments = Column(Float, default=0.0)  # Investment + Brokerage
    retirement = Column(Float, default=0.0)  # Retirement accounts (401k, IRA)
    credit_debt = Column(Float, default=0.0)
    loan_debt = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)


class Budget(Base):
    """Monthly budget by category"""
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(SQLEnum(TransactionCategory))

    monthly_limit = Column(Float)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExcludedAccount(Base):
    """Accounts excluded from sync (user deleted them)"""
    __tablename__ = "excluded_accounts"

    id = Column(Integer, primary_key=True, index=True)
    simplefin_account_id = Column(String, unique=True, index=True)  # The SimpleFIN account ID
    account_name = Column(String)  # For reference
    excluded_at = Column(DateTime, default=datetime.utcnow)


class TransactionRule(Base):
    """User-defined rules for automatic transaction categorization"""
    __tablename__ = "transaction_rules"

    id = Column(Integer, primary_key=True, index=True)

    # Rule name for user reference
    name = Column(String)

    # Match conditions (all non-null conditions must match)
    match_field = Column(String)  # 'name', 'merchant_name', or 'any'
    match_type = Column(String)  # 'contains', 'starts_with', 'ends_with', 'exact', 'regex'
    match_value = Column(String)  # The pattern to match
    case_sensitive = Column(Boolean, default=False)

    # Optional: only apply to specific account types
    account_type = Column(String, nullable=True)  # 'spending', 'investment', or null for all

    # Action: assign this category
    assign_category = Column(SQLEnum(TransactionCategory))

    # Rule priority (higher = checked first)
    priority = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(Base):
    """Recurring subscriptions tracked separately"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    # Subscription details
    name = Column(String)  # Display name (e.g., "Netflix")
    merchant_pattern = Column(String)  # Pattern to match transactions (e.g., "netflix")

    # Billing info
    expected_amount = Column(Float)  # Expected charge amount
    billing_cycle = Column(String, default="monthly")  # monthly, annual, weekly
    category = Column(SQLEnum(TransactionCategory), default=TransactionCategory.SUBSCRIPTION_OTHER)

    # Status tracking
    is_active = Column(Boolean, default=True)
    is_confirmed = Column(Boolean, default=False)  # User confirmed vs auto-detected
    is_dismissed = Column(Boolean, default=False)  # User dismissed this detection

    # Charge tracking
    last_charge_date = Column(Date, nullable=True)
    last_charge_amount = Column(Float, nullable=True)
    next_expected_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """Initialize the database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print(f"Database created at: {DB_PATH}")
