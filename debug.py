from pathlib import Path
from sgm.infrastructure.database import get_account, init_db, create_account

import os
import sqlite3

def debug():
    db_path = Path("/tmp/sigma_debug.db")
    if db_path.exists():
        db_path.unlink()
    os.environ["HOME"] = "/tmp"
    init_db(db_path)
    create_account("wallet", "Cash", "debit", 0, db_path=db_path)
    
    acc = get_account("fake", db_path=db_path)
    print("get_account('fake'):", acc)
    
    acc2 = get_account("wallet", db_path=db_path)
    print("get_account('wallet'):", acc2)

debug()
