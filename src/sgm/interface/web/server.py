import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field

from sgm.infrastructure.database import (
    get_accounts,
    get_account,
    create_account,
    rename_account,
    update_credit_limit,
    delete_account,
    get_marked_total,
    get_recent_logs,
    get_render_history,
    execute_render,
    create_movement,
    create_transfer,
    delete_record,
)
from sgm.infrastructure.user_config import load_config, save_config

app = FastAPI(
    title="Sigma API",
    description="Local backend API for Sigma personal finance tracker",
    version="1.0.0",
)

# Enable CORS for local Next.js development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to get the correct database path (allows test overrides in app.state.db_path)
def get_current_db_path() -> Optional[Path]:
    return getattr(app.state, "db_path", None)

# Pydantic Schemas
class AccountCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(debit|credit)$")
    initial_balance: int = Field(default=0)
    credit_limit: int = Field(default=0)

class AccountRename(BaseModel):
    new_id: str = Field(..., min_length=1, max_length=50)

class AccountSetLimit(BaseModel):
    limit: int = Field(..., ge=0)

class TransactionExpense(BaseModel):
    amount: int = Field(..., gt=0)
    description: str = Field(..., min_length=1)
    mark: bool = Field(default=True)
    account_id: Optional[str] = None
    date: Optional[str] = None

class TransactionIncome(BaseModel):
    amount: int = Field(..., gt=0)
    description: str = Field(..., min_length=1)
    mark: bool = Field(default=True)
    account_id: Optional[str] = None
    date: Optional[str] = None

class TransactionTransfer(BaseModel):
    from_account: str = Field(..., min_length=1)
    to_account: str = Field(..., min_length=1)
    amount: int = Field(..., gt=0)
    date: Optional[str] = None

class ConfigUpdate(BaseModel):
    income_acc: str
    expense_acc: str

# Endpoints
@app.get("/api/v1/status")
def get_status():
    try:
        db_path = get_current_db_path()
        accounts = get_accounts(db_path=db_path)
        marked_total = get_marked_total(db_path=db_path)
        
        # Calculate net total (debit balances minus credit balances / debt)
        net_balance = 0
        for acc in accounts:
            if acc["type"] == "debit":
                net_balance += acc["balance"]
            elif acc["type"] == "credit":
                # For credit, balance is the spent amount (debt)
                net_balance -= acc["balance"]
                
        return {
            "accounts": accounts,
            "marked_total": marked_total,
            "net_balance": net_balance,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/config")
def get_web_config():
    config_data = load_config()
    defaults = config_data.get("defaults", {})
    return {
        "income_acc": defaults.get("income_acc", ""),
        "expense_acc": defaults.get("expense_acc", ""),
    }

@app.put("/api/v1/config")
def update_web_config(cfg: ConfigUpdate):
    try:
        db_path = get_current_db_path()
        # Verify accounts exist if not empty
        if cfg.income_acc and not get_account(cfg.income_acc, db_path=db_path):
            raise HTTPException(status_code=400, detail=f"Income account '{cfg.income_acc}' not found.")
        if cfg.expense_acc and not get_account(cfg.expense_acc, db_path=db_path):
            raise HTTPException(status_code=400, detail=f"Expense account '{cfg.expense_acc}' not found.")
            
        config_data = load_config()
        if "defaults" not in config_data:
            config_data["defaults"] = {}
        config_data["defaults"]["income_acc"] = cfg.income_acc
        config_data["defaults"]["expense_acc"] = cfg.expense_acc
        save_config(config_data)
        return {"status": "success", "config": config_data["defaults"]}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/accounts")
def list_accounts():
    try:
        return get_accounts(db_path=get_current_db_path())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/accounts")
def create_new_account(acc: AccountCreate):
    try:
        db_path = get_current_db_path()
        if get_account(acc.id, db_path=db_path):
            raise HTTPException(status_code=400, detail=f"Account with ID '{acc.id}' already exists.")
        create_account(
            id=acc.id,
            name=acc.name,
            type=acc.type,
            balance=acc.initial_balance,
            credit_limit=acc.credit_limit,
            db_path=db_path,
        )
        return {"status": "success", "account": get_account(acc.id, db_path=db_path)}
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/accounts/{account_id}/rename")
def rename_existing_account(account_id: str, payload: AccountRename):
    try:
        db_path = get_current_db_path()
        if not get_account(account_id, db_path=db_path):
            raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")
        if get_account(payload.new_id, db_path=db_path):
            raise HTTPException(status_code=400, detail=f"Account with ID '{payload.new_id}' already exists.")
        rename_account(account_id, payload.new_id, db_path=db_path)
        return {"status": "success", "account": get_account(payload.new_id, db_path=db_path)}
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/accounts/{account_id}/limit")
def set_account_limit(account_id: str, payload: AccountSetLimit):
    try:
        db_path = get_current_db_path()
        acc = get_account(account_id, db_path=db_path)
        if not acc:
            raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")
        if acc["type"] != "credit":
            raise HTTPException(status_code=400, detail="Credit limit can only be set on credit accounts.")
        update_credit_limit(account_id, payload.limit, db_path=db_path)
        return {"status": "success", "account": get_account(account_id, db_path=db_path)}
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/accounts/{account_id}")
def delete_existing_account(account_id: str):
    try:
        db_path = get_current_db_path()
        if not get_account(account_id, db_path=db_path):
            raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")
        delete_account(account_id, db_path=db_path)
        return {"status": "success"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/transactions")
def get_transactions(limit: int | None = None, year_month: str | None = None):
    try:
        limit_val = limit if limit is not None else (None if year_month else 50)
        return get_recent_logs(limit=limit_val, year_month=year_month, db_path=get_current_db_path())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/transactions/expense")
def add_expense(tx: TransactionExpense):
    try:
        db_path = get_current_db_path()
        
        # Resolve account_id if not provided
        acc_id = tx.account_id
        if not acc_id:
            config_data = load_config()
            acc_id = config_data.get("defaults", {}).get("expense_acc", "")
        if not acc_id:
            accounts = get_accounts(db_path=db_path)
            if len(accounts) == 1:
                acc_id = accounts[0]["id"]
        
        if not acc_id:
            raise HTTPException(
                status_code=400, 
                detail="No account ID provided and no default expense account is configured."
            )
        if not get_account(acc_id, db_path=db_path):
            raise HTTPException(status_code=404, detail=f"Account '{acc_id}' not found.")
            
        tx_id = create_movement(
            amount=tx.amount,
            description=tx.description,
            account_id=acc_id,
            type="expense",
            marked=tx.mark,
            created_at=tx.date,
            db_path=db_path,
        )
        return {"status": "success", "id": tx_id}
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/transactions/income")
def add_income(tx: TransactionIncome):
    try:
        db_path = get_current_db_path()
        
        # Resolve account_id if not provided
        acc_id = tx.account_id
        if not acc_id:
            config_data = load_config()
            acc_id = config_data.get("defaults", {}).get("income_acc", "")
        if not acc_id:
            accounts = get_accounts(db_path=db_path)
            if len(accounts) == 1:
                acc_id = accounts[0]["id"]
                
        if not acc_id:
            raise HTTPException(
                status_code=400, 
                detail="No account ID provided and no default income account is configured."
            )
        if not get_account(acc_id, db_path=db_path):
            raise HTTPException(status_code=404, detail=f"Account '{acc_id}' not found.")
            
        tx_id = create_movement(
            amount=tx.amount,
            description=tx.description,
            account_id=acc_id,
            type="income",
            marked=tx.mark,
            created_at=tx.date,
            db_path=db_path,
        )
        return {"status": "success", "id": tx_id}
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/transactions/transfer")
def add_transfer(tx: TransactionTransfer):
    try:
        db_path = get_current_db_path()
        if not get_account(tx.from_account, db_path=db_path):
            raise HTTPException(status_code=404, detail=f"Source account '{tx.from_account}' not found.")
        if not get_account(tx.to_account, db_path=db_path):
            raise HTTPException(status_code=404, detail=f"Destination account '{tx.to_account}' not found.")
            
        tx_id = create_transfer(
            from_account=tx.from_account,
            to_account=tx.to_account,
            amount=tx.amount,
            created_at=tx.date,
            db_path=db_path,
        )
        return {"status": "success", "id": tx_id}
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/transactions/{transaction_id}")
def delete_transaction(transaction_id: str):
    try:
        db_path = get_current_db_path()
        delete_record(transaction_id, db_path=db_path)
        return {"status": "success"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/render")
def run_render():
    try:
        db_path = get_current_db_path()
        net_amount, count = execute_render(db_path=db_path)
        return {"status": "success", "net_amount": net_amount, "count": count}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/render/history")
def render_history(limit: int = 50):
    try:
        return get_render_history(limit=limit, db_path=get_current_db_path())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/backup/export")
def export_backup():
    try:
        import io
        import csv
        import zipfile
        from datetime import datetime
        from sgm.infrastructure.database import get_all_table_data
        
        db_path = get_current_db_path()
        all_data = get_all_table_data(db_path=db_path)
        
        # Write files to an in-memory ZIP archive
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for table_name, rows in all_data.items():
                csv_io = io.StringIO()
                if rows:
                    fieldnames = rows[0].keys()
                    writer = csv.DictWriter(csv_io, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                else:
                    # Write empty file
                    pass
                
                zipf.writestr(f"{table_name}.csv", csv_io.getvalue())
        
        zip_io.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sigma_export_{timestamp}.zip"
        
        return StreamingResponse(
            zip_io,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/backup/import")
async def import_backup(file: UploadFile = File(...)):
    try:
        from sgm.infrastructure.database import import_from_csvs
        import shutil
        import tempfile
        import uuid
        
        db_path = get_current_db_path()
        
        # Save uploaded file to a temporary location
        temp_zip = Path(tempfile.gettempdir()) / f"upload_{uuid.uuid4()}.zip"
        try:
            with temp_zip.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            import_from_csvs(temp_zip, db_path=db_path)
        finally:
            if temp_zip.exists():
                temp_zip.unlink()
                
        return {"status": "success"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=400, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/backup/reset")
def reset_database():
    try:
        from sgm.infrastructure.user_config import config_path
        from sgm.cli import ensure_initialized
        from sgm.infrastructure.database import get_db_path
        
        db_path = get_current_db_path() or get_db_path()
        if db_path.exists():
            db_path.unlink()
            
        cfg_path = config_path()
        if cfg_path.exists():
            cfg_path.unlink()
            
        # Re-initialize to a clean, empty state so the server continues running
        ensure_initialized()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/version")
def get_app_version():
    from sgm import __version__
    import urllib.request
    import json
    import sys
    
    repo = "fzunigam/sigma"
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    latest_version = None
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "Sigma-App"})
        # Fetch with a short timeout to prevent blocking the UI
        with urllib.request.urlopen(req, timeout=3.0) as response:
            data = json.loads(response.read().decode())
            latest_version = data["tag_name"].lstrip("v")
    except Exception:
        # Silently fallback to None if offline or request fails
        pass
        
    return {
        "version": __version__,
        "latest_version": latest_version,
        "is_frozen": getattr(sys, "frozen", False),
        "platform": sys.platform
    }

# Setup Static Files serving and SPA fallback routing
static_dir = os.path.join(os.path.dirname(__file__), "static")

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    # If a page is not found (404) and it's not an API call, serve Next.js SPA index.html
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
            
    # Fallback to standard FastAPI error response
    return await http_exception_handler(request, exc)

# Mount the static directory at root /
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    # Developer mode fallback if static files aren't built yet
    @app.get("/", response_class=HTMLResponse)
    def dev_fallback():
        return """
        <html>
            <head>
                <meta name="viewport" content="width=device-width,initial-scale=1" />
                <title>Sigma Web Server</title>
                <style>
                    :root{
                        --color-background: #0f172a;
                        --color-foreground: #f1f5f9;
                        --color-card: #0b1220;
                        --color-muted: #94a3b8;
                        --radius-lg: 0.5rem;
                        --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    }
                    html,body{height:100%;margin:0}
                    body{font-family:var(--font-sans);background:var(--color-background);color:var(--color-foreground);display:flex;align-items:center;justify-content:center;padding:2rem}
                    .card{background:var(--color-card);padding:2rem;border-radius:var(--radius-lg);max-width:720px;width:100%;box-shadow:0 6px 18px rgba(2,6,23,0.6);text-align:left}
                    h2{margin:0 0 0.25rem;font-size:1.25rem}
                    p{margin:0.5rem 0}
                    .note{color:var(--color-muted);font-size:0.95rem}
                    .actions{margin-top:1rem;display:flex;gap:0.5rem}
                    .btn{background:transparent;border:1px solid rgba(255,255,255,0.06);color:var(--color-foreground);padding:0.45rem 0.75rem;border-radius:0.375rem;text-decoration:none;font-weight:600}
                    code{background:rgba(255,255,255,0.03);padding:0.15rem 0.3rem;border-radius:4px}
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>Sigma</h2>
                    <p>The backend API is running successfully.</p>
                    <p class="note">Static frontend assets are not built. Run <code>npm run build</code> in the <code>web/</code> directory to compile the dashboard.</p>
                    <div class="actions">
                        <a class="btn" href="/api/v1/status">API Status</a>
                        <a class="btn" href="/api/v1/config">Config</a>
                    </div>
                </div>
            </body>
        </html>
        """
