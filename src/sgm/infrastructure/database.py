import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    return Path.home() / ".local" / "share" / "sgm" / "sigma.db"


def init_db(db_path: Path | None = None) -> None:
    if db_path is None:
        db_path = get_db_path()
        
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                balance INTEGER NOT NULL,
                credit_limit INTEGER DEFAULT 0
            )
        """)
        
        # Ensure schema consistency for existing databases
        cursor.execute("PRAGMA table_info(accounts)")
        account_cols = [row[1] for row in cursor.fetchall()]
        if account_cols:
            if 'kind' in account_cols and 'type' not in account_cols:
                cursor.execute("ALTER TABLE accounts RENAME COLUMN kind TO type")
            if 'credit_limit' not in account_cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN credit_limit INTEGER DEFAULT 0")
        
        cursor.execute("PRAGMA table_info(movements)")
        movement_cols_info = cursor.fetchall()
        
        # If the table doesn't exist yet, create it fresh
        if not movement_cols_info:
            cursor.execute("""
                CREATE TABLE movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE movement_marks (
                    movement_id INTEGER PRIMARY KEY,
                    marked INTEGER NOT NULL,
                    FOREIGN KEY(movement_id) REFERENCES movements(id)
                )
            """)
        else:
            movement_cols = {row[1]: row[2] for row in movement_cols_info}
            if movement_cols.get('id') == 'TEXT':
                # Deep migration from old local schema
                cursor.execute("ALTER TABLE movements RENAME TO old_movements")
                cursor.execute("DROP TABLE IF EXISTS movement_marks")
                
                cursor.execute("""
                    CREATE TABLE movements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        amount INTEGER NOT NULL,
                        description TEXT NOT NULL,
                        account_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE movement_marks (
                        movement_id INTEGER PRIMARY KEY,
                        marked INTEGER NOT NULL,
                        FOREIGN KEY(movement_id) REFERENCES movements(id)
                    )
                """)
                
                # Copy data over
                cursor.execute("SELECT id, description, amount, type, account_id, marked, created_at FROM old_movements")
                for old_row in cursor.fetchall():
                    old_id, desc, amt, mtype, acc_id, marked, cat = old_row
                    cursor.execute("""
                        INSERT INTO movements (amount, description, account_id, type, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (amt, desc, acc_id, mtype, cat))
                    new_id = cursor.lastrowid
                    cursor.execute("""
                        INSERT INTO movement_marks (movement_id, marked)
                        VALUES (?, ?)
                    """, (new_id, marked))
                
                cursor.execute("DROP TABLE old_movements")
            else:
                if 'created_at' not in movement_cols:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc).isoformat()
                    cursor.execute(f"ALTER TABLE movements ADD COLUMN created_at TEXT NOT NULL DEFAULT '{now}'")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS movement_marks (
                        movement_id INTEGER PRIMARY KEY,
                        marked INTEGER NOT NULL,
                        FOREIGN KEY(movement_id) REFERENCES movements(id)
                    )
                """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_account TEXT NOT NULL,
                to_account TEXT NOT NULL,
                amount INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS render_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                net_amount INTEGER NOT NULL,
                rendered_at TEXT NOT NULL
            )
        """)
        
        conn.commit()


def create_account(id: str, name: str, type: str, balance: int, credit_limit: int = 0, db_path: Path | None = None) -> None:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO accounts (id, name, type, balance, credit_limit)
                VALUES (?, ?, ?, ?, ?)
            """, (id, name, type, balance, credit_limit))
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Account with ID '{id}' already exists.")

def clear_db(db_path: Path | None = None) -> None:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Delete from all tables
        cursor.execute("DELETE FROM movement_marks")
        cursor.execute("DELETE FROM movements")
        cursor.execute("DELETE FROM transfers")
        cursor.execute("DELETE FROM render_history")
        cursor.execute("DELETE FROM accounts")
        conn.commit()


def get_accounts(db_path: Path | None = None) -> list[dict]:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, balance, credit_limit FROM accounts ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]


def get_account(id: str, db_path: Path | None = None) -> dict | None:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, balance, credit_limit FROM accounts WHERE id = ?", (id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_credit_limit(id: str, limit: int, db_path: Path | None = None) -> None:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE accounts 
            SET credit_limit = ?
            WHERE id = ?
        """, (limit, id))
        conn.commit()


def get_marked_total(db_path: Path | None = None) -> int:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN m.type = 'income' THEN m.amount ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN m.type = 'expense' THEN m.amount ELSE 0 END), 0)
            FROM movements m
            JOIN movement_marks mm ON m.id = mm.movement_id
            WHERE mm.marked = 1
        """)
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0


def create_movement(amount: int, description: str, account_id: str, type: str, marked: bool, db_path: Path | None = None) -> int:
    if db_path is None:
        db_path = get_db_path()
        
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT type, balance, credit_limit FROM accounts WHERE id = ?", (account_id,))
        acc_row = cursor.fetchone()
        if not acc_row:
            raise ValueError(f"Account with ID '{account_id}' does not exist.")
            
        acc_type, balance, credit_limit = acc_row
        
        if type == "expense":
            if acc_type == "debit":
                new_balance = balance - amount
                if new_balance < 0:
                    raise ValueError(f"Insufficient funds in account '{account_id}'. Available: {balance}, Required: {amount}")
            elif acc_type == "credit":
                new_balance = balance + amount
                if new_balance > credit_limit:
                    avail = credit_limit - balance
                    raise ValueError(f"Insufficient credit in account '{account_id}'. Available: {avail}, Required: {amount}")
            else:
                raise ValueError(f"Unknown account type '{acc_type}'")
        elif type == "income":
            if acc_type == "debit":
                new_balance = balance + amount
            elif acc_type == "credit":
                new_balance = balance - amount
            else:
                raise ValueError(f"Unknown account type '{acc_type}'")
        else:
            raise ValueError(f"Unknown movement type '{type}'")
            
        cursor.execute("""
            UPDATE accounts SET balance = ? WHERE id = ?
        """, (new_balance, account_id))
            
        cursor.execute("""
            INSERT INTO movements (amount, description, account_id, type, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (amount, description, account_id, type, now))
        
        movement_id = cursor.lastrowid
        if movement_id is None:
            raise RuntimeError("Failed to insert movement")
            
        cursor.execute("""
            INSERT INTO movement_marks (movement_id, marked)
            VALUES (?, ?)
        """, (movement_id, 1 if marked else 0))
        
        conn.commit()
        return movement_id
