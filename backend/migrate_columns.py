"""
Migration script to rename plaid_* columns to simplefin_* columns.
Run this once to update the existing database.
"""

import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "finance.db")

def migrate():
    print(f"Migrating database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if migration is needed by checking if old column exists
        cursor.execute("PRAGMA table_info(institutions)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'plaid_item_id' not in columns:
            print("Migration already completed or not needed.")
            return

        print("Starting migration...")

        # Rename columns in institutions table
        # SQLite doesn't support RENAME COLUMN in older versions, so we need to recreate

        # 1. Institutions table
        print("Migrating institutions table...")
        cursor.execute("""
            CREATE TABLE institutions_new (
                id INTEGER PRIMARY KEY,
                simplefin_id VARCHAR UNIQUE,
                simplefin_access_url VARCHAR,
                simplefin_org_id VARCHAR,
                name VARCHAR,
                logo_url VARCHAR,
                primary_color VARCHAR,
                provider VARCHAR DEFAULT 'simplefin',
                is_active BOOLEAN DEFAULT 1,
                last_sync DATETIME,
                sync_status VARCHAR DEFAULT 'pending',
                error_message TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)
        cursor.execute("""
            INSERT INTO institutions_new
            SELECT id, plaid_item_id, plaid_access_token, plaid_institution_id,
                   name, logo_url, primary_color, provider, is_active, last_sync,
                   sync_status, error_message, created_at, updated_at
            FROM institutions
        """)
        cursor.execute("DROP TABLE institutions")
        cursor.execute("ALTER TABLE institutions_new RENAME TO institutions")
        cursor.execute("CREATE INDEX ix_institutions_simplefin_id ON institutions(simplefin_id)")

        # 2. Accounts table
        print("Migrating accounts table...")
        cursor.execute("""
            CREATE TABLE accounts_new (
                id INTEGER PRIMARY KEY,
                institution_id INTEGER REFERENCES institutions(id),
                simplefin_account_id VARCHAR UNIQUE,
                name VARCHAR,
                official_name VARCHAR,
                mask VARCHAR,
                account_type VARCHAR DEFAULT 'other',
                subtype VARCHAR,
                current_balance FLOAT DEFAULT 0.0,
                available_balance FLOAT,
                credit_limit FLOAT,
                currency VARCHAR DEFAULT 'USD',
                is_active BOOLEAN DEFAULT 1,
                is_hidden BOOLEAN DEFAULT 0,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)
        cursor.execute("""
            INSERT INTO accounts_new
            SELECT id, institution_id, plaid_account_id, name, official_name, mask,
                   account_type, subtype, current_balance, available_balance, credit_limit,
                   currency, is_active, is_hidden, created_at, updated_at
            FROM accounts
        """)
        cursor.execute("DROP TABLE accounts")
        cursor.execute("ALTER TABLE accounts_new RENAME TO accounts")
        cursor.execute("CREATE INDEX ix_accounts_simplefin_account_id ON accounts(simplefin_account_id)")

        # 3. Transactions table
        print("Migrating transactions table...")
        cursor.execute("""
            CREATE TABLE transactions_new (
                id INTEGER PRIMARY KEY,
                account_id INTEGER REFERENCES accounts(id),
                simplefin_transaction_id VARCHAR UNIQUE,
                date DATE,
                authorized_date DATE,
                name VARCHAR,
                merchant_name VARCHAR,
                amount FLOAT,
                currency VARCHAR DEFAULT 'USD',
                category VARCHAR DEFAULT 'uncategorized',
                original_category VARCHAR,
                original_category_id VARCHAR,
                is_pending BOOLEAN DEFAULT 0,
                is_recurring BOOLEAN DEFAULT 0,
                is_manual BOOLEAN DEFAULT 0,
                user_category VARCHAR,
                user_notes TEXT,
                is_excluded BOOLEAN DEFAULT 0,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)
        cursor.execute("""
            INSERT INTO transactions_new
            SELECT id, account_id, plaid_transaction_id, date, authorized_date,
                   name, merchant_name, amount, currency, category,
                   plaid_category, plaid_category_id,
                   is_pending, is_recurring, is_manual, user_category, user_notes,
                   is_excluded, created_at, updated_at
            FROM transactions
        """)
        cursor.execute("DROP TABLE transactions")
        cursor.execute("ALTER TABLE transactions_new RENAME TO transactions")
        cursor.execute("CREATE INDEX ix_transactions_simplefin_transaction_id ON transactions(simplefin_transaction_id)")
        cursor.execute("CREATE INDEX ix_transactions_date ON transactions(date)")

        # 4. Holdings table (if exists)
        print("Migrating holdings table...")
        cursor.execute("PRAGMA table_info(holdings)")
        holdings_columns = [col[1] for col in cursor.fetchall()]

        if 'plaid_holding_id' in holdings_columns:
            cursor.execute("""
                CREATE TABLE holdings_new (
                    id INTEGER PRIMARY KEY,
                    account_id INTEGER REFERENCES accounts(id),
                    simplefin_holding_id VARCHAR,
                    security_name VARCHAR,
                    ticker VARCHAR,
                    quantity FLOAT,
                    cost_basis FLOAT,
                    current_price FLOAT,
                    current_value FLOAT,
                    security_type VARCHAR,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            cursor.execute("""
                INSERT INTO holdings_new
                SELECT id, account_id, plaid_holding_id, security_name, ticker,
                       quantity, cost_basis, current_price, current_value,
                       security_type, created_at, updated_at
                FROM holdings
            """)
            cursor.execute("DROP TABLE holdings")
            cursor.execute("ALTER TABLE holdings_new RENAME TO holdings")
            cursor.execute("CREATE INDEX ix_holdings_ticker ON holdings(ticker)")

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
