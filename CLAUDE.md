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

### Analytics & Tracking
- Net worth with daily snapshots and historical charts
- Spending by category and vendor
- Multi-month trend analysis
- Investment holdings with cost basis
- Subscription/recurring charge detection

### Budgets
- Category-based monthly spending limits
- Progress tracking against limits

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

### Transactions
- `GET /api/transactions` - List with filters (date, account, category)
- `PATCH /api/transactions/{id}` - Update category/notes
- `POST /api/recategorize-transactions` - Bulk recategorization

### Dashboard & Analytics
- `GET /api/dashboard` - Summary (net worth, spending, accounts)
- `GET /api/net-worth/history` - Historical net worth for charts
- `GET /api/spending/summary` - Spending by category
- `GET /api/spending/by-vendor` - Vendor breakdown
- `GET /api/spending/trends` - Multi-month trends

### Investments
- `GET /api/holdings` - All holdings with values
- `GET /api/investment-summary` - Aggregated performance
- `GET /api/investment-history` - Historical tracking

### Configuration
- `POST /api/sync` - Manual sync trigger
- `GET /api/categories` - Category definitions with emojis
- `GET/POST/PATCH/DELETE /api/rules` - Transaction rules CRUD
- `GET/POST/PATCH /api/subscriptions` - Subscription management

## File Structure
```
finance_tracker/
├── backend/
│   ├── main.py              # FastAPI app, 50+ endpoints
│   ├── database.py          # SQLAlchemy models
│   ├── sync_service.py      # SimpleFIN data sync
│   ├── simplefin_client.py  # SimpleFIN API client
│   ├── categorizer.py       # Transaction auto-categorization
│   ├── config.py            # Settings/environment
│   ├── auth.py              # Basic auth
│   ├── scheduler.py         # Background jobs (APScheduler)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app, routing
│   │   ├── api.js           # API client
│   │   └── pages/           # Dashboard, Accounts, Transactions, etc.
│   ├── vite.config.js
│   └── tailwind.config.js
├── Dockerfile
├── docker-compose.yml
└── data/finance.db          # SQLite database
```

## Background Jobs
- **APScheduler** runs auto-sync every 4 hours
- Configured in `scheduler.py`
- Timezone-aware scheduling

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
docker-compose up -d --build
```

### View Logs
```bash
docker logs -f finance-tracker
```

### Manual Sync
```bash
curl -X POST http://localhost:8000/api/sync
```

### Restart Without Affecting CANSLIM
```bash
cd /opt/finance-tracker
docker-compose down && docker-compose up -d --build
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

## Related Project
- **CANSLIM Analyzer** runs on port 8001 (same VPS)
- Both share similar architecture (FastAPI + React + Docker)
- Be careful with `docker rm -f $(docker ps -aq)` - it removes BOTH containers

## Security
- Basic auth enabled for production
- HTTPS recommended for PWA features
- CORS configured for frontend origin
- Passwords hashed with bcrypt
