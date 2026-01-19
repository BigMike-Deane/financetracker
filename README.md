# Finance Tracker

A personal finance tracking app with automatic bank sync via Plaid. Track your net worth, spending, and budgets from a mobile-friendly Progressive Web App (PWA).

## Features

- **Bank Sync**: Connect to 12,000+ financial institutions via Plaid
- **Net Worth Tracking**: Daily snapshots with trend visualization
- **Spending Analysis**: Auto-categorized transactions with charts
- **Mobile PWA**: Install on your phone like a native app
- **Daily Auto-Sync**: Automatic data refresh every 4 hours

## Quick Start

### 1. Get Plaid API Keys

1. Sign up at [Plaid Dashboard](https://dashboard.plaid.com/signup)
2. Go to **Developers → Keys**
3. Copy your `client_id` and `sandbox` secret

### 2. Configure Environment

```bash
cd finance_tracker
cp .env.example .env
```

Edit `.env` with your Plaid credentials:
```
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_sandbox_secret
PLAID_ENV=sandbox
```

### 3. Install & Run Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The API will be running at `http://localhost:8000`

### 4. Install & Run Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be running at `http://localhost:3000`

### 5. Connect Your First Account

1. Open `http://localhost:3000` in your browser
2. Go to **Settings**
3. Click **Connect Bank Account**
4. In sandbox mode, use test credentials:
   - Username: `user_good`
   - Password: `pass_good`
5. Select accounts to link

## Project Structure

```
finance_tracker/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── database.py          # SQLAlchemy models
│   ├── plaid_client.py      # Plaid API integration
│   ├── sync_service.py      # Data sync logic
│   ├── categorizer.py       # Transaction auto-categorization
│   ├── scheduler.py         # Background sync jobs
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/           # React page components
│   │   ├── App.jsx          # Main app with routing
│   │   └── api.js           # API client
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   └── finance.db           # SQLite database
│
└── .env                     # Environment configuration
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard` | GET | Dashboard summary data |
| `/api/accounts` | GET | List all accounts |
| `/api/transactions` | GET | List transactions with filters |
| `/api/net-worth/history` | GET | Net worth history for charts |
| `/api/spending/summary` | GET | Spending by category |
| `/api/plaid/link-token` | POST | Create Plaid Link token |
| `/api/sync` | POST | Trigger manual sync |

## Cloud Deployment

### Option A: Railway (Recommended)

1. Create account at [Railway](https://railway.app)
2. Connect your GitHub repo
3. Add environment variables in Railway dashboard
4. Deploy!

### Option B: Render

1. Create account at [Render](https://render.com)
2. Create a new **Web Service**
3. Connect your repo
4. Configure:
   - Build Command: `cd frontend && npm install && npm run build && cd ../backend && pip install -r requirements.txt`
   - Start Command: `cd backend && python main.py`
5. Add environment variables
6. Deploy!

### Option C: Self-hosted (Docker)

```dockerfile
# Dockerfile example coming soon
```

## Going to Production

### 1. Switch Plaid to Development/Production

1. In Plaid Dashboard, request access to Development environment
2. Update `.env`:
   ```
   PLAID_ENV=development
   PLAID_SECRET=your_development_secret
   ```

### 2. Security Considerations

- [ ] Enable HTTPS
- [ ] Set strong `SECRET_KEY`
- [ ] Configure proper CORS origins
- [ ] Consider adding authentication

### 3. Database

For production, consider migrating from SQLite to PostgreSQL:
```
DATABASE_URL=postgresql://user:password@host:5432/finance
```

## Supported Institutions

Plaid supports 12,000+ institutions including:
- **Banks**: Chase, Bank of America, Wells Fargo, Capital One, etc.
- **Brokerages**: Fidelity, Charles Schwab, TD Ameritrade, Robinhood, etc.
- **Credit Cards**: All major issuers
- **Loans**: Student loans, mortgages, auto loans

## Troubleshooting

### "Link token failed"
- Check Plaid credentials in `.env`
- Ensure Plaid environment matches your secret key

### "Sync failed"
- Some institutions require re-authentication periodically
- Check Plaid Dashboard for error details

### "PWA not installing"
- Must be served over HTTPS (except localhost)
- Clear browser cache and try again

## License

Personal use only. Do not distribute.
