import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    balance INTEGER NOT NULL CHECK (typeof(balance) = 'integer')
);

CREATE TABLE IF NOT EXISTS movements (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK (typeof(amount) = 'integer' AND amount > 0),
    type TEXT NOT NULL,
    account_id TEXT NOT NULL,
    marked INTEGER NOT NULL CHECK (marked IN (0, 1)),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS transfers (
    id TEXT PRIMARY KEY,
    source_account_id TEXT NOT NULL,
    target_account_id TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK (typeof(amount) = 'integer' AND amount > 0),
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_account_id) REFERENCES accounts(id),
    FOREIGN KEY (target_account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS render_history (
    id TEXT PRIMARY KEY,
    rendered_at TEXT NOT NULL,
    income_total INTEGER NOT NULL CHECK (typeof(income_total) = 'integer'),
    expense_total INTEGER NOT NULL CHECK (typeof(expense_total) = 'integer'),
    net INTEGER NOT NULL CHECK (typeof(net) = 'integer'),
    count INTEGER NOT NULL CHECK (typeof(count) = 'integer' AND count >= 0)
);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    connection.commit()
    return connection
