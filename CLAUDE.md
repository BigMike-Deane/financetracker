# Finance Tracker - Project Context

## Overview
A personal finance management application that integrates with SimpleFIN to automatically sync bank accounts, track net worth, categorize spending, and analyze financial trends. Mobile-friendly PWA with FastAPI backend and React frontend.

## Architecture
- **Frontend**: React 18 + Vite + TailwindCSS + Recharts
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Deployment**: Docker on VPS at `/opt/finance-tracker` (port 8000)
- **Docker command**: Use `docker-compose` (with hyphen, old version on VPS)
- **PWA**: Installable as native app on mobile devices

## Key Features

### Bank Integration (SimpleFIN)
- Connects to 12,000+ financial institutions
- Auto-syncs accounts and transactions every 4 hours
- Quick sync (balances only) runs hourly at :30
- Alternative to Plaid (more cost-effective)
- Setup via claim token exchange

### Account Types Supported
- Checking & Savings
- Credit Cards
- Investment & Brokerage
- Retirement (401k, IRA)
- Loans & Mortgages

### Transaction Management
- Auto-categorization with 40+ categories
- User-defined transaction rules (pattern matching)
- Supports: contains, starts_with, ends_with, exact, regex
- Manual category overrides
- **Transaction splitting** - split one transaction into multiple categories
- **Duplicate detection** - find and exclude cross-account duplicates

### Analytics & Tracking
- Net worth with daily snapshots and historical charts
- Spending by category and vendor
- Multi-month trend analysis
- Investment holdings with cost basis
- Subscription/recurring charge detection

### Budgets
- Category-based monthly spending limits
- Progress tracking against limits

## Recent Improvements (Jan 2025)

### Sync Performance Optimizations
- **Quick sync mode**: Update balances only (~5 seconds vs minutes)
- **Incremental sync**: Fetch transactions from last_sync date with 3-day buffer
- **Batch database operations**: Uses `bulk_save_objects()` for transactions
- New endpoints: `/api/sync/quick`, `/api/sync/{id}/quick`
- Existing endpoints support `?full=true` for 90-day history

### Database Performance
- Added composite index on transactions `(account_id, date)`
- Added index on transactions `(account_id)`
- Added composite index on balance_history `(account_id, date)`
- Category list precomputed and cached at module load

### Scheduler Improvements
- Full sync every 4 hours (transactions + balances)
- Quick sync every hour at :30 (balances only)
- Much fresher balance data without transaction overhead

### UI Enhancements
- **Quick Sync button** on Settings page (primary blue)
- **Full Sync button** on Settings page (gray)
- **Sync progress modal** - shows progress bar when syncing multiple institutions
- **Last synced timestamp** on Dashboard header (relative time like "5m ago")
- **Duplicates tab** on Transactions page - review and exclude duplicates
- **Split button** on transactions - split into multiple categories

### Duplicate Transaction Detection
- Finds transactions with same absolute amount within 3 days
- Groups by different accounts (cross-account duplicates)
- Common case: credit card payment on both checking and credit card
- One-click exclude/include for handling duplicates

### Transaction Split Feature
- Split one transaction into multiple parts
- Assign different categories to each split
- Original transaction marked as excluded
- New manual transactions created for splits

## Database Models (SQLAlchemy)

| Model | Purpose |
|-------|---------|
| Institution | Linked banks/brokerages with SimpleFIN credentials |
| Account | Individual accounts (checking, savings, credit, etc.) |
| Transaction | Individual transactions with categories |
| BalanceHistory | Daily balance snapshots per account |
| Holding | Investment holdings (stocks, ETFs) |
| NetWorthSnapshot | Daily aggregated net worth |
| Budget | Category spending limits |
| TransactionRule | User-defined auto-categorization rules |
| Subscription | Tracked recurring charges |
| ExcludedAccount | Accounts user deleted from tracking |

## API Endpoints

### Institutions & Accounts
- `POST /api/setup-simplefin` - Claim SimpleFIN setup token
- `GET /api/institutions` - List linked institutions
- `GET /api/accounts` - List accounts with balances
- `DELETE /api/accounts/{id}` - Remove account

### Sync
- `POST /api/sync` - Sync all (incremental by default, `?full=true` for 90 days)
- `POST /api/sync/quick` - Quick sync all (balances only, ~5 seconds)
- `POST /api/sync/{id}` - Sync specific institution
- `POST /api/sync/{id}/quick` - Quick sync specific institution

### Transactions
- `GET /api/transactions` - List with filters (date, account, category)
- `PATCH /api/transactions/{id}` - Update category/notes
- `POST /api/transactions/{id}/split` - Split into multiple parts
- `POST /api/transactions/{id}/exclude` - Exclude from reports
- `POST /api/transactions/{id}/include` - Re-include in reports
- `GET /api/transactions/duplicates` - Find potential duplicates

### Dashboard & Analytics
- `GET /api/dashboard` - Summary (net worth, spending, accounts, last_sync)
- `GET /api/net-worth/history` - Historical net worth for charts
- `GET /api/spending/summary` - Spending by category
- `GET /api/spending/by-vendor` - Vendor breakdown
- `GET /api/spending/trends` - Multi-month trends

### Investments
- `GET /api/holdings` - All holdings with values
- `GET /api/investment-summary` - Aggregated performance
- `GET /api/investment-history` - Historical tracking

### Configuration
- `GET /api/categories` - Category definitions with emojis (cached)
- `GET/POST/PATCH/DELETE /api/rules` - Transaction rules CRUD
- `GET/POST/PATCH /api/subscriptions` - Subscription management

## File Structure
```
finance_tracker/
├── backend/
│   ├── main.py              # FastAPI app, 50+ endpoints
│   ├── database.py          # SQLAlchemy models + indexes
│   ├── sync_service.py      # SimpleFIN data sync (quick/full/incremental)
│   ├── simplefin_client.py  # SimpleFIN API client
│   ├── categorizer.py       # Transaction auto-categorization
│   ├── config.py            # Settings/environment
│   ├── auth.py              # Basic auth
│   ├── scheduler.py         # Background jobs (full every 4h, quick every 1h)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app, routing
│   │   ├── api.js           # API client
│   │   └── pages/           # Dashboard, Accounts, Transactions, Settings
│   ├── vite.config.js
│   └── tailwind.config.js
├── Dockerfile
├── docker-compose.yml
└── data/finance.db          # SQLite database
```

## Background Jobs
- **APScheduler** configured in `scheduler.py`
- Full sync at 6 AM daily and every 4 hours
- Quick sync (balances only) every hour at :30
- Timezone-aware scheduling via `TZ` environment variable

## Transaction Categorization Logic
Three-tier system in `categorizer.py`:
1. Provider categories (SimpleFIN standard)
2. User-defined rules (priority-based)
3. Merchant name pattern matching

## Net Worth Calculation
- **Assets**: Cash (checking+savings) + Investments + Retirement
- **Liabilities**: Credit debt + Loan debt
- Daily snapshots stored for trend analysis

## Environment Variables
```
SECRET_KEY=your-secret-key
DEBUG=false
AUTH_USERNAME=admin
AUTH_PASSWORD=your-password
API_HOST=0.0.0.0
API_PORT=8000
TZ=America/New_York
DATABASE_URL=sqlite:///./data/finance.db
```

## Common Commands

### Start/Restart
```bash
cd /opt/finance-tracker
docker-compose down && docker-compose up -d --build
```

### View Logs
```bash
docker logs -f finance-tracker
```

### Manual Sync (Quick)
```bash
curl -X POST http://localhost:8000/api/sync/quick
```

### Manual Sync (Full)
```bash
curl -X POST "http://localhost:8000/api/sync?full=true"
```

## Common Issues

### Container stopped
```bash
cd /opt/finance-tracker && docker-compose up -d
```

### SimpleFIN sync not working
- Check institution credentials in Settings
- Try manual sync via API
- Check logs for SimpleFIN API errors

### Frontend changes not appearing
```bash
docker-compose build --no-cache && docker-compose up -d
```

### Sync taking too long
- Use Quick Sync for balance-only updates (~5 seconds)
- Full Sync fetches all transactions (can take minutes)

## Related Project
- **CANSLIM Analyzer** runs on port 8001 (same VPS)
- Both share similar architecture (FastAPI + React + Docker)
- **CRITICAL**: Never use `docker rm -f $(docker ps -aq)` - it removes BOTH containers

## Security
- Basic auth enabled for production
- HTTPS recommended for PWA features
- CORS configured for frontend origin
- Passwords hashed with bcrypt
