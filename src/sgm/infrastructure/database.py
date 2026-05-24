import csv
import uuid
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


def get_db_path() -> Path:
    return Path.home() / ".local" / "share" / "sgm" / "sigma.db"


def get_now_timestamp() -> str:
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


def init_db(db_path: Path | None = None) -> None:
    if db_path is None:
        db_path = get_db_path()
        
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Accounts Table Setup
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                balance INTEGER NOT NULL,
                credit_limit INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                deleted_at TEXT
            )
        """)
        
        # Ensure schema consistency for existing databases (accounts)
        cursor.execute("PRAGMA table_info(accounts)")
        account_cols = {row[1]: row[2] for row in cursor.fetchall()}
        if account_cols:
            if 'kind' in account_cols and 'type' not in account_cols:
                cursor.execute("ALTER TABLE accounts RENAME COLUMN kind TO type")
            if 'credit_limit' not in account_cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN credit_limit INTEGER DEFAULT 0")
            if 'updated_at' not in account_cols:
                now_ts = get_now_timestamp()
                cursor.execute(f"ALTER TABLE accounts ADD COLUMN updated_at TEXT NOT NULL DEFAULT '{now_ts}'")
            if 'deleted_at' not in account_cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN deleted_at TEXT")
        
        # 2. Movements Table Setup
        cursor.execute("PRAGMA table_info(movements)")
        movement_cols_info = cursor.fetchall()
        
        # If the table doesn't exist yet, create it fresh
        if not movement_cols_info:
            cursor.execute("""
                CREATE TABLE movements (
                    id TEXT PRIMARY KEY,
                    amount INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                    deleted_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE movement_marks (
                    movement_id TEXT PRIMARY KEY,
                    marked INTEGER NOT NULL,
                    FOREIGN KEY(movement_id) REFERENCES movements(id)
                )
            """)
        else:
            movement_cols = {row[1]: row[2] for row in movement_cols_info}
            if movement_cols.get('id') != 'TEXT':
                # Deep migration from old local schema (integer IDs) to UUID schema
                cursor.execute("ALTER TABLE movements RENAME TO old_movements")
                
                # Check if old movement_marks exists, rename if yes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movement_marks'")
                has_marks = cursor.fetchone() is not None
                if has_marks:
                    cursor.execute("ALTER TABLE movement_marks RENAME TO old_movement_marks")
                
                cursor.execute("""
                    CREATE TABLE movements (
                        id TEXT PRIMARY KEY,
                        amount INTEGER NOT NULL,
                        description TEXT NOT NULL,
                        account_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                        deleted_at TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE movement_marks (
                        movement_id TEXT PRIMARY KEY,
                        marked INTEGER NOT NULL,
                        FOREIGN KEY(movement_id) REFERENCES movements(id)
                    )
                """)
                
                # Copy data over converting IDs to UUIDs
                if has_marks:
                    cursor.execute("""
                        SELECT m.id, m.description, m.amount, m.type, m.account_id, COALESCE(mm.marked, 0) as marked, m.created_at
                        FROM old_movements m
                        LEFT JOIN old_movement_marks mm ON m.id = mm.movement_id
                    """)
                else:
                    cursor.execute("SELECT id, description, amount, type, account_id, 0 as marked, created_at FROM old_movements")
                    
                for old_row in cursor.fetchall():
                    old_id, desc, amt, mtype, acc_id, marked, cat = old_row
                    # Ensure date-only format
                    cat_date = cat.split('T')[0] if 'T' in cat else cat
                    new_uuid = str(uuid.uuid4())
                    now_ts = get_now_timestamp()
                    cursor.execute("""
                        INSERT INTO movements (id, amount, description, account_id, type, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (new_uuid, amt, desc, acc_id, mtype, cat_date, now_ts))
                    cursor.execute("""
                        INSERT INTO movement_marks (movement_id, marked)
                        VALUES (?, ?)
                    """, (new_uuid, marked))
                
                cursor.execute("DROP TABLE old_movements")
                if has_marks:
                    cursor.execute("DROP TABLE old_movement_marks")
            else:
                if 'updated_at' not in movement_cols:
                    now_ts = get_now_timestamp()
                    cursor.execute(f"ALTER TABLE movements ADD COLUMN updated_at TEXT NOT NULL DEFAULT '{now_ts}'")
                if 'deleted_at' not in movement_cols:
                    cursor.execute("ALTER TABLE movements ADD COLUMN deleted_at TEXT")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS movement_marks (
                        movement_id TEXT PRIMARY KEY,
                        marked INTEGER NOT NULL,
                        FOREIGN KEY(movement_id) REFERENCES movements(id)
                    )
                """)
        
        # 3. Transfers Table Setup
        cursor.execute("PRAGMA table_info(transfers)")
        transfer_cols_info = cursor.fetchall()
        
        if not transfer_cols_info:
            cursor.execute("""
                CREATE TABLE transfers (
                    id TEXT PRIMARY KEY,
                    from_account TEXT NOT NULL,
                    to_account TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                    deleted_at TEXT
                )
            """)
        else:
            transfer_cols = {row[1]: row[2] for row in transfer_cols_info}
            if transfer_cols.get('id') != 'TEXT':
                # Deep migration from old local schema
                cursor.execute("ALTER TABLE transfers RENAME TO old_transfers")
                cursor.execute("""
                    CREATE TABLE transfers (
                        id TEXT PRIMARY KEY,
                        from_account TEXT NOT NULL,
                        to_account TEXT NOT NULL,
                        amount INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                        deleted_at TEXT
                    )
                """)
                cursor.execute("SELECT from_account, to_account, amount, created_at FROM old_transfers")
                for old_row in cursor.fetchall():
                    src_id, tgt_id, amt, cat = old_row
                    cat_date = cat.split('T')[0] if 'T' in cat else cat
                    new_uuid = str(uuid.uuid4())
                    now_ts = get_now_timestamp()
                    cursor.execute("""
                        INSERT INTO transfers (id, from_account, to_account, amount, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (new_uuid, src_id, tgt_id, amt, cat_date, now_ts))
                cursor.execute("DROP TABLE old_transfers")
            else:
                if 'updated_at' not in transfer_cols:
                    now_ts = get_now_timestamp()
                    cursor.execute(f"ALTER TABLE transfers ADD COLUMN updated_at TEXT NOT NULL DEFAULT '{now_ts}'")
                if 'deleted_at' not in transfer_cols:
                    cursor.execute("ALTER TABLE transfers ADD COLUMN deleted_at TEXT")
        
        # 4. Render History Table Setup
        cursor.execute("PRAGMA table_info(render_history)")
        render_cols_info = cursor.fetchall()
        
        if not render_cols_info:
            cursor.execute("""
                CREATE TABLE render_history (
                    id TEXT PRIMARY KEY,
                    net_amount INTEGER NOT NULL,
                    rendered_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                    deleted_at TEXT
                )
            """)
        else:
            render_cols = {row[1]: row[2] for row in render_cols_info}
            if render_cols.get('id') != 'TEXT':
                # Deep migration
                cursor.execute("ALTER TABLE render_history RENAME TO old_render_history")
                cursor.execute("""
                    CREATE TABLE render_history (
                        id TEXT PRIMARY KEY,
                        net_amount INTEGER NOT NULL,
                        rendered_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                        deleted_at TEXT
                    )
                """)
                cursor.execute("SELECT net_amount, rendered_at FROM old_render_history")
                for old_row in cursor.fetchall():
                    net_amt, rat = old_row
                    rat_date = rat.split('T')[0] if 'T' in rat else rat
                    new_uuid = str(uuid.uuid4())
                    now_ts = get_now_timestamp()
                    cursor.execute("""
                        INSERT INTO render_history (id, net_amount, rendered_at, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (new_uuid, net_amt, rat_date, now_ts))
                cursor.execute("DROP TABLE old_render_history")
            else:
                if 'updated_at' not in render_cols:
                    now_ts = get_now_timestamp()
                    cursor.execute(f"ALTER TABLE render_history ADD COLUMN updated_at TEXT NOT NULL DEFAULT '{now_ts}'")
                if 'deleted_at' not in render_cols:
                    cursor.execute("ALTER TABLE render_history ADD COLUMN deleted_at TEXT")
        
        conn.commit()


def create_account(id: str, name: str, type: str, balance: int, credit_limit: int = 0, db_path: Path | None = None) -> None:
    if id == "deleted":
        raise ValueError("Cannot create an account with the reserved ID 'deleted'.")
        
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        try:
            now_ts = get_now_timestamp()
            cursor.execute("SELECT id FROM accounts WHERE id = ? AND deleted_at IS NOT NULL", (id,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE accounts 
                    SET name = ?, type = ?, balance = ?, credit_limit = ?, updated_at = ?, deleted_at = NULL
                    WHERE id = ?
                """, (name, type, balance, credit_limit, now_ts, id))
            else:
                cursor.execute("""
                    INSERT INTO accounts (id, name, type, balance, credit_limit, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id, name, type, balance, credit_limit, now_ts))
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
    if old_id == "deleted" or new_id == "deleted":
        raise ValueError("Cannot rename to or from the reserved ID 'deleted'.")
        
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check if old_id exists
        cursor.execute("SELECT id FROM accounts WHERE id = ? AND deleted_at IS NULL", (old_id,))
        if not cursor.fetchone():
            raise ValueError(f"Account with ID '{old_id}' does not exist.")
            
        # Check if new_id exists
        cursor.execute("SELECT id FROM accounts WHERE id = ?", (new_id,))
        if cursor.fetchone():
            raise ValueError(f"Account with ID '{new_id}' already exists.")
            
        now_ts = get_now_timestamp()
        # Update accounts
        cursor.execute("UPDATE accounts SET id = ?, updated_at = ? WHERE id = ?", (new_id, now_ts, old_id))
        
        # Update movements
        cursor.execute("UPDATE movements SET account_id = ?, updated_at = ? WHERE account_id = ?", (new_id, now_ts, old_id))
        
        # Update transfers
        cursor.execute("UPDATE transfers SET from_account = ?, updated_at = ? WHERE from_account = ?", (new_id, now_ts, old_id))
        cursor.execute("UPDATE transfers SET to_account = ?, updated_at = ? WHERE to_account = ?", (new_id, now_ts, old_id))
        
        conn.commit()


def get_accounts(db_path: Path | None = None) -> list[dict]:
    if db_path is None:
        db_path = get_db_path()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, balance, credit_limit FROM accounts WHERE id != 'deleted' AND deleted_at IS NULL ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

def get_account(id: str, db_path: Path | None = None) -> dict | None:
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, balance, credit_limit FROM accounts WHERE id = ? AND deleted_at IS NULL", (id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_account(account_id: str, db_path: Path | None = None) -> None:
    if account_id == "deleted":
        raise ValueError("Cannot delete the reserved 'deleted' account.")
        
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM accounts WHERE id = ? AND deleted_at IS NULL", (account_id,))
        if not cursor.fetchone():
            raise ValueError(f"Account with ID '{account_id}' does not exist.")
            
        # Ensure 'deleted' account exists
        cursor.execute("SELECT id FROM accounts WHERE id = 'deleted'")
        if not cursor.fetchone():
            now_ts = get_now_timestamp()
            cursor.execute("""
                INSERT INTO accounts (id, name, type, balance, credit_limit, updated_at)
                VALUES ('deleted', 'Deleted Account', 'debit', 0, 0, ?)
            """, (now_ts,))
            
        now_ts = get_now_timestamp()
        # Reassign movements and transfers, updating their updated_at
        cursor.execute("UPDATE movements SET account_id = 'deleted', updated_at = ? WHERE account_id = ?", (now_ts, account_id))
        cursor.execute("UPDATE transfers SET from_account = 'deleted', updated_at = ? WHERE from_account = ?", (now_ts, account_id))
        cursor.execute("UPDATE transfers SET to_account = 'deleted', updated_at = ? WHERE to_account = ?", (now_ts, account_id))
        
        # Soft delete the account
        cursor.execute("UPDATE accounts SET deleted_at = ?, updated_at = ? WHERE id = ?", (now_ts, now_ts, account_id))
        
        conn.commit()


def update_credit_limit(id: str, limit: int, db_path: Path | None = None) -> None:
    if id == "deleted":
        raise ValueError("Cannot modify the reserved 'deleted' account.")
        
    if db_path is None:
        db_path = get_db_path()
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        now_ts = get_now_timestamp()
        cursor.execute("""
            UPDATE accounts 
            SET credit_limit = ?, updated_at = ?
            WHERE id = ?
        """, (limit, now_ts, id))
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
            WHERE mm.marked = 1 AND m.deleted_at IS NULL
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
        
    from datetime import date
    now_date = date.today().isoformat()
    
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
            WHERE mm.marked = 1 AND m.deleted_at IS NULL
        """)
        row = cursor.fetchone()
        net_amount = row[0] if row and row[0] is not None else 0
        count = row[1] if row and row[1] is not None else 0
        
        if count == 0:
            return 0, 0
            
        # 2. Insert snapshot into render_history
        render_id = str(uuid.uuid4())
        now_ts = get_now_timestamp()
        cursor.execute("""
            INSERT INTO render_history (id, net_amount, rendered_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (render_id, net_amount, now_date, now_ts))
        
        # 3. Unmark processed movements and update their updated_at
        cursor.execute("""
            SELECT m.id FROM movements m
            JOIN movement_marks mm ON m.id = mm.movement_id
            WHERE mm.marked = 1 AND m.deleted_at IS NULL
        """)
        m_ids = [r[0] for r in cursor.fetchall()]
        
        if m_ids:
            placeholders = ",".join(["?"] * len(m_ids))
            cursor.execute(f"UPDATE movements SET updated_at = ? WHERE id IN ({placeholders})", [now_ts] + m_ids)
            cursor.execute(f"UPDATE movement_marks SET marked = 0 WHERE movement_id IN ({placeholders})", m_ids)
        
        conn.commit()
        return net_amount, count


def create_transfer(from_account: str, to_account: str, amount: int, created_at: str | None = None, db_path: Path | None = None) -> str:
    if from_account == "deleted" or to_account == "deleted":
        raise ValueError("Cannot manually transfer to or from the reserved 'deleted' account.")
        
    if db_path is None:
        db_path = get_db_path()
        
    if created_at is None:
        from datetime import date
        created_at = date.today().isoformat()
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Get from_account
        cursor.execute("SELECT type, balance, credit_limit FROM accounts WHERE id = ? AND deleted_at IS NULL", (from_account,))
        from_row = cursor.fetchone()
        if not from_row:
            raise ValueError(f"Account with ID '{from_account}' does not exist.")
        from_type, from_balance, from_limit = from_row
        
        if from_type == "credit":
            raise ValueError("Transfers from credit cards are not allowed.")
        
        # Get to_account
        cursor.execute("SELECT type, balance, credit_limit FROM accounts WHERE id = ? AND deleted_at IS NULL", (to_account,))
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
            if new_to_balance < 0:
                raise ValueError(f"Transfer would leave credit card '{to_account}' with a negative balance. Current balance: {to_balance}, Transfer amount: {amount}")
        else:
            raise ValueError(f"Unknown account type '{to_type}'")
            
        now_ts = get_now_timestamp()
        # Update balances and updated_at
        cursor.execute("UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?", (new_from_balance, now_ts, from_account))
        cursor.execute("UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?", (new_to_balance, now_ts, to_account))
        
        # Insert transfer record
        transfer_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO transfers (id, from_account, to_account, amount, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (transfer_id, from_account, to_account, amount, created_at, now_ts))
            
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
                'm-' || substr(id, 1, 8) AS unique_id,
                type,
                amount,
                description,
                account_id,
                created_at
            FROM movements
            WHERE deleted_at IS NULL
            
            UNION ALL
            
            SELECT 
                't-' || substr(id, 1, 8) AS unique_id,
                'transfer' AS type,
                amount,
                from_account || ' -> ' || to_account AS description,
                '' AS account_id,
                created_at
            FROM transfers
            WHERE deleted_at IS NULL
            
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
            SELECT substr(id, 1, 8) AS id, net_amount, rendered_at
            FROM render_history
            WHERE deleted_at IS NULL
            ORDER BY rendered_at DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]


def create_movement(amount: int, description: str, account_id: str, type: str, marked: bool, created_at: str | None = None, db_path: Path | None = None) -> str:
    if account_id == "deleted":
        raise ValueError("Cannot manually log movements to the reserved 'deleted' account.")
        
    if db_path is None:
        db_path = get_db_path()
        
    if created_at is None:
        from datetime import date
        created_at = date.today().isoformat()
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT type, balance, credit_limit FROM accounts WHERE id = ? AND deleted_at IS NULL", (account_id,))
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
            
        now_ts = get_now_timestamp()
        cursor.execute("""
            UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?
        """, (new_balance, now_ts, account_id))
            
        movement_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO movements (id, amount, description, account_id, type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (movement_id, amount, description, account_id, type, created_at, now_ts))
            
        cursor.execute("""
            INSERT INTO movement_marks (movement_id, marked)
            VALUES (?, ?)
        """, (movement_id, 1 if marked else 0))
        
        conn.commit()
        return movement_id


def delete_record(unique_id: str, db_path: Path | None = None) -> None:
    if db_path is None:
        db_path = get_db_path()

    if unique_id.startswith("m-"):
        record_id = unique_id[2:]
        _delete_movement(record_id, db_path)
    elif unique_id.startswith("t-"):
        record_id = unique_id[2:]
        _delete_transfer(record_id, db_path)
    else:
        raise ValueError("Invalid ID format. Must start with 'm-' for movements or 't-' for transfers.")


def _delete_movement(movement_id: str, db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Resolve short ID prefix
        cursor.execute("SELECT id FROM movements WHERE id LIKE ? AND deleted_at IS NULL", (movement_id + "%",))
        matches = [row[0] for row in cursor.fetchall()]
        if len(matches) == 0:
            raise ValueError(f"Record 'm-{movement_id}' not found.")
        elif len(matches) > 1:
            raise ValueError(f"Record ID 'm-{movement_id}' is ambiguous. Matches: {', '.join(matches)}")
            
        actual_id = matches[0]
        
        # 1. Get movement details
        cursor.execute("""
            SELECT m.amount, m.type, m.account_id, a.type as acc_type, a.balance
            FROM movements m
            JOIN accounts a ON m.account_id = a.id
            WHERE m.id = ?
        """, (actual_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"Record 'm-{actual_id}' not found.")
            
        amount, m_type, acc_id, acc_type, current_balance = row
        
        # 2. Calculate reversed balance
        if m_type == "expense":
            if acc_type == "debit":
                new_balance = current_balance + amount
            else: # credit
                new_balance = current_balance - amount
        else: # income
            if acc_type == "debit":
                new_balance = current_balance - amount
            else: # credit
                new_balance = current_balance + amount
                
        now_ts = get_now_timestamp()
        # 3. Update account balance and updated_at
        cursor.execute("UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?", (new_balance, now_ts, acc_id))
        
        # 4. Soft delete movement
        cursor.execute("UPDATE movements SET deleted_at = ?, updated_at = ? WHERE id = ?", (now_ts, now_ts, actual_id))
        
        conn.commit()


def _delete_transfer(transfer_id: str, db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Resolve short ID prefix
        cursor.execute("SELECT id FROM transfers WHERE id LIKE ? AND deleted_at IS NULL", (transfer_id + "%",))
        matches = [row[0] for row in cursor.fetchall()]
        if len(matches) == 0:
            raise ValueError(f"Record 't-{transfer_id}' not found.")
        elif len(matches) > 1:
            raise ValueError(f"Record ID 't-{transfer_id}' is ambiguous. Matches: {', '.join(matches)}")
            
        actual_id = matches[0]
        
        # 1. Get transfer details
        cursor.execute("""
            SELECT t.amount, t.from_account, t.to_account, 
                   af.type as from_type, af.balance as from_balance,
                   at.type as to_type, at.balance as to_balance
            FROM transfers t
            JOIN accounts af ON t.from_account = af.id
            JOIN accounts at ON t.to_account = at.id
            WHERE t.id = ?
        """, (actual_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"Record 't-{actual_id}' not found.")
            
        amount, from_acc, to_acc, from_type, from_bal, to_type, to_bal = row
        
        # 2. Reverse from_account withdrawal
        if from_type == "debit":
            new_from_balance = from_bal + amount
        else: # credit
            new_from_balance = from_bal - amount
            
        # 3. Reverse to_account deposit
        if to_type == "debit":
            new_to_balance = to_bal - amount
        else: # credit
            new_to_balance = to_bal + amount
            
        now_ts = get_now_timestamp()
        # 4. Update balances and updated_at
        cursor.execute("UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?", (new_from_balance, now_ts, from_acc))
        cursor.execute("UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?", (new_to_balance, now_ts, to_acc))
        
        # 5. Soft delete transfer
        cursor.execute("UPDATE transfers SET deleted_at = ?, updated_at = ? WHERE id = ?", (now_ts, now_ts, actual_id))
        
        conn.commit()


def get_all_table_data(db_path: Path | None = None) -> dict[str, list[dict]]:
    """
    Returns a dictionary with data from all tables.
    Keys are table names, values are lists of dicts (rows).
    """
    if db_path is None:
        db_path = get_db_path()

    tables = ["accounts", "movements", "movement_marks", "transfers", "render_history"]
    all_data = {}

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            all_data[table] = [dict(row) for row in cursor.fetchall()]

    return all_data


def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def import_from_csvs(import_path: Path, db_path: Path | None = None) -> None:
    """
    Imports data from a ZIP file or a folder containing Sigma CSVs.
    Performs validation before clearing and inserting data.
    """
    if db_path is None:
        db_path = get_db_path()

    expected_files = {
        "accounts.csv": ["id", "name", "type", "balance", "credit_limit"],
        "movements.csv": ["id", "amount", "description", "account_id", "type", "created_at"],
        "movement_marks.csv": ["movement_id", "marked"],
        "transfers.csv": ["id", "from_account", "to_account", "amount", "created_at"],
        "render_history.csv": ["id", "net_amount", "rendered_at"]
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        working_dir = Path(tmp_dir)
        
        # 1. Extraction if ZIP
        if import_path.is_file():
            if not zipfile.is_zipfile(import_path):
                raise ValueError(f"File '{import_path}' is not a valid ZIP file.")
            with zipfile.ZipFile(import_path, 'r') as zipf:
                zipf.extractall(working_dir)
        elif import_path.is_dir():
            for f in expected_files:
                src = import_path / f
                if src.exists():
                    shutil.copy(src, working_dir / f)
        else:
            raise ValueError(f"Path '{import_path}' does not exist or is not a file/directory.")

        # 2. Validation
        for filename, expected_headers in expected_files.items():
            file_path = working_dir / filename
            if not file_path.exists():
                raise FileNotFoundError(f"Missing required file: {filename}")
            
            # Check headers
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                try:
                    headers = next(reader)
                    # Use set comparison to be order-independent but strict on presence
                    if not set(expected_headers).issubset(set(headers)):
                        missing = set(expected_headers) - set(headers)
                        raise ValueError(f"Invalid headers in {filename}. Missing: {missing}")
                except StopIteration:
                    # Empty file is okay if it's supposed to be empty, but we still expect headers
                    pass

        # 3. Restoration
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute("DELETE FROM movement_marks")
            cursor.execute("DELETE FROM movements")
            cursor.execute("DELETE FROM transfers")
            cursor.execute("DELETE FROM render_history")
            cursor.execute("DELETE FROM accounts")
            
            movement_id_map = {}
            import_order = ["accounts.csv", "movements.csv", "movement_marks.csv", "transfers.csv", "render_history.csv"]
            
            for file_key in import_order:
                headers = expected_files[file_key]
                table_name = file_key.replace(".csv", "")
                file_path = working_dir / file_key
                
                with open(file_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        clean_row = {}
                        
                        if table_name == "accounts":
                            clean_row = {
                                "id": row["id"],
                                "name": row["name"],
                                "type": row["type"],
                                "balance": int(row["balance"]),
                                "credit_limit": int(row.get("credit_limit") or 0),
                                "updated_at": row.get("updated_at") or get_now_timestamp(),
                                "deleted_at": row.get("deleted_at") or None
                            }
                        elif table_name == "movements":
                            raw_id = row["id"]
                            if is_valid_uuid(raw_id):
                                new_id = raw_id
                            else:
                                new_id = str(uuid.uuid4())
                                movement_id_map[raw_id] = new_id
                            
                            clean_row = {
                                "id": new_id,
                                "amount": int(row["amount"]),
                                "description": row["description"],
                                "account_id": row["account_id"],
                                "type": row["type"],
                                "created_at": row["created_at"],
                                "updated_at": row.get("updated_at") or get_now_timestamp(),
                                "deleted_at": row.get("deleted_at") or None
                            }
                        elif table_name == "movement_marks":
                            raw_mid = row["movement_id"]
                            mapped_mid = movement_id_map.get(raw_mid, raw_mid)
                            clean_row = {
                                "movement_id": mapped_mid,
                                "marked": int(row["marked"])
                            }
                        elif table_name == "transfers":
                            raw_id = row["id"]
                            new_id = raw_id if is_valid_uuid(raw_id) else str(uuid.uuid4())
                            clean_row = {
                                "id": new_id,
                                "from_account": row["from_account"],
                                "to_account": row["to_account"],
                                "amount": int(row["amount"]),
                                "created_at": row["created_at"],
                                "updated_at": row.get("updated_at") or get_now_timestamp(),
                                "deleted_at": row.get("deleted_at") or None
                            }
                        elif table_name == "render_history":
                            raw_id = row["id"]
                            new_id = raw_id if is_valid_uuid(raw_id) else str(uuid.uuid4())
                            clean_row = {
                                "id": new_id,
                                "net_amount": int(row["net_amount"]),
                                "rendered_at": row["rendered_at"],
                                "updated_at": row.get("updated_at") or get_now_timestamp(),
                                "deleted_at": row.get("deleted_at") or None
                            }
                        
                        placeholders = ", ".join(["?"] * len(clean_row))
                        columns = ", ".join(clean_row.keys())
                        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                        cursor.execute(query, list(clean_row.values()))
            
            conn.commit()
