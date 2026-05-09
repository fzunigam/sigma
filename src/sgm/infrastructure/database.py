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
        
        cursor.execute("PRAGMA table_info(transfers)")
        transfer_cols_info = cursor.fetchall()
        
        if not transfer_cols_info:
            cursor.execute("""
                CREATE TABLE transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_account TEXT NOT NULL,
                    to_account TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
        else:
            transfer_cols = {row[1]: row[2] for row in transfer_cols_info}
            if transfer_cols.get('id') == 'TEXT' or 'source_account_id' in transfer_cols:
                # Deep migration from old local schema
                cursor.execute("ALTER TABLE transfers RENAME TO old_transfers")
                cursor.execute("""
                    CREATE TABLE transfers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_account TEXT NOT NULL,
                        to_account TEXT NOT NULL,
                        amount INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)
                cursor.execute("SELECT source_account_id, target_account_id, amount, created_at FROM old_transfers")
                for old_row in cursor.fetchall():
                    src_id, tgt_id, amt, cat = old_row
                    cursor.execute("""
                        INSERT INTO transfers (from_account, to_account, amount, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (src_id, tgt_id, amt, cat))
                cursor.execute("DROP TABLE old_transfers")
        
        cursor.execute("PRAGMA table_info(render_history)")
        render_cols_info = cursor.fetchall()
        
        if not render_cols_info:
            cursor.execute("""
                CREATE TABLE render_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    net_amount INTEGER NOT NULL,
                    rendered_at TEXT NOT NULL
                )
            """)
        else:
            render_cols = {row[1]: row[2] for row in render_cols_info}
            if 'id' not in render_cols or render_cols.get('id') == 'TEXT' or 'income_total' in render_cols:
                # Deep migration for old local schema
                cursor.execute("ALTER TABLE render_history RENAME TO old_render_history")
                cursor.execute("""
                    CREATE TABLE render_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        net_amount INTEGER NOT NULL,
                        rendered_at TEXT NOT NULL
                    )
                """)
                if 'net' in render_cols:
                    cursor.execute("SELECT net, rendered_at FROM old_render_history")
                    for old_row in cursor.fetchall():
                        cursor.execute("""
                            INSERT INTO render_history (net_amount, rendered_at)
                            VALUES (?, ?)
                        """, (old_row[0], old_row[1]))
                elif 'rendered_at' in render_cols:
                    cursor.execute("SELECT rendered_at FROM old_render_history")
                    for old_row in cursor.fetchall():
                        cursor.execute("""
                            INSERT INTO render_history (net_amount, rendered_at)
                            VALUES (?, ?)
                        """, (0, old_row[0]))
                cursor.execute("DROP TABLE old_render_history")
            elif 'net_amount' not in render_cols:
                cursor.execute("ALTER TABLE render_history ADD COLUMN net_amount INTEGER NOT NULL DEFAULT 0")

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


def rename_account(old_id: str, new_id: str, db_path: Path | None = None) -> None:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check if old_id exists
        cursor.execute("SELECT id FROM accounts WHERE id = ?", (old_id,))
        if not cursor.fetchone():
            raise ValueError(f"Account with ID '{old_id}' does not exist.")
            
        # Check if new_id exists
        cursor.execute("SELECT id FROM accounts WHERE id = ?", (new_id,))
        if cursor.fetchone():
            raise ValueError(f"Account with ID '{new_id}' already exists.")
            
        # Update accounts
        cursor.execute("UPDATE accounts SET id = ? WHERE id = ?", (new_id, old_id))
        
        # Update movements
        cursor.execute("UPDATE movements SET account_id = ? WHERE account_id = ?", (new_id, old_id))
        
        # Update transfers
        cursor.execute("UPDATE transfers SET from_account = ? WHERE from_account = ?", (new_id, old_id))
        cursor.execute("UPDATE transfers SET to_account = ? WHERE to_account = ?", (new_id, old_id))
        
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


def execute_render(db_path: Path | None = None) -> tuple[int, int]:
    """
    Sums marked movements, inserts into render_history, and unmarks them.
    Returns (net_amount, count_of_movements_rendered).
    """
    if db_path is None:
        db_path = get_db_path()
        
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Calculate the net amount and count marked movements
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN m.type = 'income' THEN m.amount ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN m.type = 'expense' THEN m.amount ELSE 0 END), 0),
                COUNT(m.id)
            FROM movements m
            JOIN movement_marks mm ON m.id = mm.movement_id
            WHERE mm.marked = 1
        """)
        row = cursor.fetchone()
        net_amount = row[0] if row and row[0] is not None else 0
        count = row[1] if row and row[1] is not None else 0
        
        if count == 0:
            return 0, 0
            
        # 2. Insert snapshot into render_history
        cursor.execute("""
            INSERT INTO render_history (net_amount, rendered_at)
            VALUES (?, ?)
        """, (net_amount, now))
        
        # 3. Unmark processed movements
        cursor.execute("""
            UPDATE movement_marks
            SET marked = 0
            WHERE marked = 1
        """)
        
        conn.commit()
        return net_amount, count


def create_transfer(from_account: str, to_account: str, amount: int, db_path: Path | None = None) -> int:
    if db_path is None:
        db_path = get_db_path()
        
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Get from_account
        cursor.execute("SELECT type, balance, credit_limit FROM accounts WHERE id = ?", (from_account,))
        from_row = cursor.fetchone()
        if not from_row:
            raise ValueError(f"Account with ID '{from_account}' does not exist.")
        from_type, from_balance, from_limit = from_row
        
        # Get to_account
        cursor.execute("SELECT type, balance, credit_limit FROM accounts WHERE id = ?", (to_account,))
        to_row = cursor.fetchone()
        if not to_row:
            raise ValueError(f"Account with ID '{to_account}' does not exist.")
        to_type, to_balance, to_limit = to_row
        
        # Withdraw from from_account
        if from_type == "debit":
            new_from_balance = from_balance - amount
            if new_from_balance < 0:
                raise ValueError(f"Insufficient funds in account '{from_account}'. Available: {from_balance}, Required: {amount}")
        elif from_type == "credit":
            new_from_balance = from_balance + amount
            if new_from_balance > from_limit:
                avail = from_limit - from_balance
                raise ValueError(f"Insufficient credit in account '{from_account}'. Available: {avail}, Required: {amount}")
        else:
            raise ValueError(f"Unknown account type '{from_type}'")
            
        # Deposit into to_account
        if to_type == "debit":
            new_to_balance = to_balance + amount
        elif to_type == "credit":
            new_to_balance = to_balance - amount
        else:
            raise ValueError(f"Unknown account type '{to_type}'")
            
        # Update balances
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_from_balance, from_account))
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_to_balance, to_account))
        
        # Insert transfer record
        cursor.execute("""
            INSERT INTO transfers (from_account, to_account, amount, created_at)
            VALUES (?, ?, ?, ?)
        """, (from_account, to_account, amount, now))
        
        transfer_id = cursor.lastrowid
        if transfer_id is None:
            raise RuntimeError("Failed to insert transfer")
            
        conn.commit()
        return transfer_id


def get_recent_logs(limit: int = 15, db_path: Path | None = None) -> list[dict]:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                'm-' || id AS unique_id,
                type,
                amount,
                description,
                account_id,
                created_at
            FROM movements
            
            UNION ALL
            
            SELECT 
                't-' || id AS unique_id,
                'transfer' AS type,
                amount,
                from_account || ' -> ' || to_account AS description,
                '' AS account_id,
                created_at
            FROM transfers
            
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]


def get_render_history(limit: int = 15, db_path: Path | None = None) -> list[dict]:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, net_amount, rendered_at
            FROM render_history
            ORDER BY rendered_at DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]


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
