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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER NOT NULL,
                description TEXT NOT NULL,
                account_id TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
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
