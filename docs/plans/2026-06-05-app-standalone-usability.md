# App Standalone Usability and Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the functional gaps between the CLI and the Web App wrapper, enabling non-coding users to perform backup exports, database imports/restores, application resets, onboarding setups, and update checks completely from the GUI window.

**Architecture:** 
1. **FastAPI Backend (Infrastructure/Interface)**: Add endpoints in `src/sgm/interface/web/server.py` for `/api/v1/backup/export`, `/api/v1/backup/import`, `/api/v1/backup/reset`, and `/api/v1/version`.
2. **Next.js Frontend (Interface)**: Update `web/src/app/page.tsx` to handle backups/resets in the Settings pane, trigger a first-run onboarding screen when transactions are empty, and display update banners when the version is behind the latest release.
3. **Docs**: Update conventions, usage, and decision log files to cover the new web-first flow.

**Tech Stack:** Python 3.12, FastAPI, SQLite, Next.js (React/TypeScript), Tailwind CSS.

---

### Task 1: Implement Backup Export, Import, and Reset Endpoints

**Files:**
- Modify: `src/sgm/interface/web/server.py`
- Test: `tests/integration/test_web_server.py`

**Step 1: Write integration tests for backup endpoints**

Add testing logic to `tests/integration/test_web_server.py`:
```python
def test_backup_endpoints(monkeypatch, tmp_path):
    from sgm.infrastructure.database import init_db
    from fastapi.testclient import TestClient
    import io
    import zipfile
    
    db_file = tmp_path / "test_backup.db"
    monkeypatch.setattr("sgm.infrastructure.database.get_db_path", lambda: db_file)
    monkeypatch.setattr("sgm.interface.web.server.get_current_db_path", lambda: db_file)
    init_db(db_file)
    
    from sgm.interface.web.server import app
    client = TestClient(app)
    
    # Create an account
    client.post("/api/v1/accounts", json={"id": "wallet", "name": "Cash", "type": "debit", "initial_balance": 5000})
    
    # 1. Test Export Endpoint
    response = client.get("/api/v1/backup/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment; filename=" in response.headers["content-disposition"]
    
    # Read the returned ZIP to verify content
    zip_bytes = io.BytesIO(response.content)
    assert zipfile.is_zipfile(zip_bytes)
    with zipfile.ZipFile(zip_bytes) as z:
        namelist = z.namelist()
        assert "accounts.csv" in namelist
        assert "movements.csv" in namelist
        
    # 2. Test Reset Endpoint
    response = client.post("/api/v1/backup/reset")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Verify account was deleted but DB/config remains initialized via fallback
    response = client.get("/api/v1/accounts")
    assert response.status_code == 200
    assert len(response.json()) == 1  # Should contain only default 'wallet' account
    
    # 3. Test Import Endpoint
    # We will import the exported ZIP
    zip_bytes.seek(0)
    files = {"file": ("backup.zip", zip_bytes, "application/zip")}
    response = client.post("/api/v1/backup/import", files=files)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Check that imported account matches the original
    response = client.get("/api/v1/accounts")
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "wallet"
```

**Step 2: Run tests to verify failure**

Run: `python3.12 -m pytest tests/integration/test_web_server.py::test_backup_endpoints`
Expected: FAIL (404/AttributeError due to missing endpoints)

**Step 3: Implement endpoints in `src/sgm/interface/web/server.py`**

*   Import necessary FastAPI elements at the top:
    ```python
    from fastapi import File, UploadFile
    from fastapi.responses import StreamingResponse
    ```
*   Implement endpoints:
    ```python
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
                        # Empty CSV
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
            from pathlib import Path
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
    ```

**Step 4: Run tests to verify they pass**

Run: `python3.12 -m pytest tests/integration/test_web_server.py::test_backup_endpoints`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/interface/web/server.py tests/integration/test_web_server.py
git commit -m "feat: implement backup export, import, and reset API endpoints"
```

---

### Task 2: Implement App Version and Update Check Endpoints

**Files:**
- Modify: `src/sgm/interface/web/server.py`
- Test: `tests/integration/test_web_server.py`

**Step 1: Write integration tests for version endpoints**

Add testing logic to `tests/integration/test_web_server.py`:
```python
def test_version_endpoints(monkeypatch):
    from fastapi.testclient import TestClient
    from sgm.interface.web.server import app
    client = TestClient(app)
    
    # Test version endpoint
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "latest_version" in data
```

**Step 2: Run test to verify it fails**

Run: `python3.12 -m pytest tests/integration/test_web_server.py::test_version_endpoints`
Expected: FAIL (404)

**Step 3: Implement version checking endpoint**

In `src/sgm/interface/web/server.py`:
*   Import `__version__` from `sgm` and check version:
    ```python
    from sgm import __version__
    import urllib.request
    import json
    import sys
    ```
*   Implement endpoint:
    ```python
    @app.get("/api/v1/version")
    def get_app_version():
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
    ```

**Step 4: Run tests to verify they pass**

Run: `python3.12 -m pytest tests/integration/test_web_server.py::test_version_endpoints`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/interface/web/server.py tests/integration/test_web_server.py
git commit -m "feat: implement app version and update check endpoints"
```

---

### Task 3: Develop Backup and Maintenance UI Panels

**Files:**
- Modify: `web/src/app/page.tsx`

**Step 1: Integrate Export, Import, and Reset UI elements inside settings**

*   Locate the "Config Panel" in `web/src/app/page.tsx` under `activeTab === 'accounts'` (lines 984–1050).
*   Add a new section for **Administration & Backups** directly below the config panel:
    ```tsx
    {/* Administration & Backups Panel */}
    <div className="bg-card border border-border rounded-lg p-6 space-y-6">
      <div>
        <h3 className="text-base font-semibold">Administration & Backups</h3>
        <p className="text-xs text-muted-foreground mt-0.5">Manage data archives and reset the application state.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
        {/* Backup Operations */}
        <div className="space-y-4">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Backups</h4>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => {
                window.open(`${API_URL}/api/v1/backup/export`, '_blank');
                addToast('success', 'Downloading backup archive...');
              }}
              className="bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold px-4 py-2 rounded-md transition duration-200"
            >
              Export ZIP Backup
            </button>
            
            <label className="bg-secondary hover:bg-secondary/95 text-secondary-foreground text-xs font-semibold px-4 py-2 rounded-md cursor-pointer transition duration-200 inline-block">
              <span>Import ZIP Backup</span>
              <input
                type="file"
                accept=".zip"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  
                  const formData = new FormData();
                  formData.append('file', file);
                  
                  setIsSubmitting(true);
                  try {
                    const res = await fetch(`${API_URL}/api/v1/backup/import`, {
                      method: 'POST',
                      body: formData,
                    });
                    if (!res.ok) {
                      const errorData = await res.json();
                      throw new Error(errorData.detail || 'Import failed');
                    }
                    addToast('success', 'Backup restored successfully!');
                    fetchData(true);
                  } catch (err: any) {
                    addToast('error', err.message);
                  } finally {
                    setIsSubmitting(false);
                    e.target.value = '';
                  }
                }}
              />
            </label>
          </div>
        </div>

        {/* System Reset / Danger Zone */}
        <div className="space-y-4">
          <h4 className="text-xs font-semibold text-red-500 uppercase tracking-wider">Danger Zone</h4>
          <div>
            <button
              onClick={async () => {
                const confirmation = prompt("WARNING: This will wipe ALL database records and configuration settings! This cannot be undone.\n\nType 'RESET' to confirm deletion:");
                if (confirmation !== 'RESET') {
                  addToast('info', 'Reset cancelled.');
                  return;
                }
                
                setIsSubmitting(true);
                try {
                  const res = await fetch(`${API_URL}/api/v1/backup/reset`, {
                    method: 'POST',
                  });
                  if (!res.ok) throw new Error('Reset failed');
                  addToast('success', 'Database wiped and reset to clean state.');
                  fetchData(true);
                } catch (err: any) {
                  addToast('error', err.message);
                } finally {
                  setIsSubmitting(false);
                }
              }}
              className="bg-red-650 hover:bg-red-700 text-white text-xs font-semibold px-4 py-2 rounded-md transition duration-200"
            >
              Reset Database & Config
            </button>
          </div>
        </div>
      </div>
    </div>
    ```

---

### Task 4: Implement First-Run Onboarding Welcome Screen

**Files:**
- Modify: `web/src/app/page.tsx`

**Step 1: Check for new installation state on startup**

*   Define a state for the Welcome Modal in `Dashboard()`:
    ```typescript
    const [showWelcomeModal, setShowWelcomeModal] = useState(false);
    ```
*   Update `fetchData` in `web/src/app/page.tsx` to automatically trigger the Welcome dialog if:
    - There are no transactions.
    - And the only account is `wallet` with a balance of `0`.
    ```typescript
    // Inside fetchData after loading states
    const resTx = await fetch(`${API_URL}/api/v1/transactions?limit=30`);
    let txList = [];
    if (resTx.ok) {
      txList = await resTx.json();
      setTransactions(txList);
    }
    
    // Check for fresh installation:
    const hasNoMovements = txList.length === 0;
    const hasOnlyDefaultWallet = dataStatus.accounts?.length === 1 && dataStatus.accounts[0].id === 'wallet' && dataStatus.accounts[0].balance === 0;
    if (hasOnlyDefaultWallet && hasNoMovements) {
      setShowWelcomeModal(true);
    }
    ```

**Step 2: Design the Onboarding Modal component**

Add the onboarding modal container to the UI:
```tsx
{/* Welcome Wizard / First Run Onboarding Modal */}
{showWelcomeModal && (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
    <div className="bg-card border border-border rounded-lg max-w-md w-full p-6 shadow-xl space-y-6">
      <div className="space-y-1.5">
        <h2 className="text-xl font-bold tracking-tight text-accent flex items-center gap-2">
          <span>Σ</span> Welcome to Sigma
        </h2>
        <p className="text-xs text-muted-foreground">
          Let's set up your local finance database. Choose an option to get started:
        </p>
      </div>

      <div className="space-y-4">
        {/* Onboarding Path 1: Configure Cash Account */}
        <div className="p-4 border border-border hover:border-accent/30 rounded-md transition duration-200 space-y-3">
          <div>
            <h3 className="text-xs font-semibold">Start Fresh</h3>
            <p className="text-[11px] text-muted-foreground mt-0.5">Customize your cash account and configure default settings.</p>
          </div>
          
          <div className="space-y-2.5">
            <div>
              <label htmlFor="wizard-acc-name" className="block text-[10px] text-muted-foreground mb-0.5">Primary Cash Account Name</label>
              <input
                id="wizard-acc-name"
                type="text"
                placeholder="Cash / Pocket Money"
                value={newAccName}
                onChange={(e) => setNewAccName(e.target.value)}
                className="bg-background border border-border text-foreground text-xs rounded px-2.5 py-1.5 w-full focus:outline-none"
              />
            </div>
            <div>
              <label htmlFor="wizard-acc-bal" className="block text-[10px] text-muted-foreground mb-0.5">Initial Balance (CLP)</label>
              <input
                id="wizard-acc-bal"
                type="number"
                placeholder="0"
                value={newAccBalance}
                onChange={(e) => setNewAccBalance(e.target.value)}
                className="bg-background border border-border text-foreground text-xs rounded px-2.5 py-1.5 w-full focus:outline-none"
              />
            </div>
            {newAccError && <p className="text-[11px] text-red-500">{newAccError}</p>}
            
            <button
              onClick={async () => {
                setNewAccError('');
                const name = newAccName.trim() || 'Cash';
                const bal = parseInt(newAccBalance, 10) || 0;
                
                setIsSubmitting(true);
                try {
                  // Rename the default 'wallet' account
                  const renameRes = await fetch(`${API_URL}/api/v1/accounts/wallet/rename`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_id: name.toLowerCase().replace(/\s+/g, '_') }),
                  });
                  if (!renameRes.ok) throw new Error('Failed to set account name');
                  const renamedAccount = await renameRes.json();
                  const finalId = renamedAccount.account.id;
                  
                  // Delete default 'wallet' and add a new one:
                  const deleteRes = await fetch(`${API_URL}/api/v1/accounts/wallet`, { method: 'DELETE' });
                  if (!deleteRes.ok) throw new Error('Initialization failed');
                  
                  const createRes = await fetch(`${API_URL}/api/v1/accounts`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      id: name.toLowerCase().replace(/\s+/g, '_'),
                      name: name,
                      type: 'debit',
                      initial_balance: bal,
                      credit_limit: 0
                    }),
                  });
                  if (!createRes.ok) throw new Error('Account creation failed');
                  const newAcc = await createRes.json();
                  const newId = newAcc.account.id;
                  
                  // Save default config
                  await fetch(`${API_URL}/api/v1/config`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ income_acc: newId, expense_acc: newId }),
                  });
                  
                  addToast('success', 'Application initialized!');
                  setShowWelcomeModal(false);
                  fetchData(true);
                } catch (err: any) {
                  setNewAccError(err.message);
                } finally {
                  setIsSubmitting(false);
                }
              }}
              className="bg-accent hover:bg-accent-hover text-black font-semibold text-xs px-3 py-1.5 rounded transition duration-200 w-full"
            >
              Initialize Database
            </button>
          </div>
        </div>

        {/* Onboarding Path 2: Import Backup ZIP */}
        <div className="p-4 border border-border hover:border-accent/30 rounded-md transition duration-200 flex flex-col items-center justify-between text-center space-y-3">
          <div>
            <h3 className="text-xs font-semibold">Restore from Backup</h3>
            <p className="text-[11px] text-muted-foreground mt-0.5">Upload a previous Sigma backup ZIP archive to restore all data.</p>
          </div>
          
          <label className="bg-secondary hover:bg-secondary/95 text-secondary-foreground text-xs font-semibold px-4 py-2 rounded cursor-pointer transition duration-200 w-full text-center">
            <span>Select ZIP Backup File</span>
            <input
              type="file"
              accept=".zip"
              className="hidden"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                
                const formData = new FormData();
                formData.append('file', file);
                
                setIsSubmitting(true);
                try {
                  const res = await fetch(`${API_URL}/api/v1/backup/import`, {
                    method: 'POST',
                    body: formData,
                  });
                  if (!res.ok) {
                    const errorData = await res.json();
                    throw new Error(errorData.detail || 'Import failed');
                  }
                  addToast('success', 'Backup restored successfully!');
                  setShowWelcomeModal(false);
                  fetchData(true);
                } catch (err: any) {
                  addToast('error', err.message);
                } finally {
                  setIsSubmitting(false);
                  e.target.value = '';
                }
              }}
            />
          </label>
        </div>
      </div>
    </div>
  </div>
)}
```

---

### Task 5: Display App Version and Update Banners

**Files:**
- Modify: `web/src/app/page.tsx`

**Step 1: Check application version status on startup**

*   Define version state in `Dashboard()`:
    ```typescript
    const [versionInfo, setVersionInfo] = useState<{ version: string; latest_version: string | null; is_frozen: boolean; platform: string } | null>(null);
    ```
*   Fetch version info in `useEffect` or inside `fetchData`:
    ```typescript
    const fetchVersion = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/version`);
        if (res.ok) {
          setVersionInfo(await res.json());
        }
      } catch (err) {}
    };
    ```

**Step 2: Add version footer inside settings sidebar or main view**

*   Display the version at the bottom of the navigation sidebar (lines 752–758 in `page.tsx`):
    ```tsx
    {versionInfo && (
      <div className="pt-4 border-t border-border mt-auto">
        <p className="text-[10px] text-muted-foreground font-mono">Sigma App v{versionInfo.version}</p>
        {versionInfo.latest_version && versionInfo.version !== versionInfo.latest_version && (
          <div className="mt-1.5 p-2 bg-accent/10 border border-accent/20 rounded text-[10px] text-accent font-semibold flex flex-col gap-1">
            <span>New Version Available (v{versionInfo.latest_version})</span>
            {versionInfo.is_frozen ? (
              <span className="text-[9px] text-muted-foreground font-normal">To update, open terminal and run 'sgm update'</span>
            ) : (
              <span className="text-[9px] text-muted-foreground font-normal">To update, run 'pip install -U sigma-finance'</span>
            )}
          </div>
        )}
      </div>
    )}
    ```

---

### Task 6: Compile and Validate Frontend Web Build

**Files:**
- Run builds and check static assets: `scripts/build_macos_app.sh`

**Step 1: Compile the frontend assets**

Run: `npm run build` in the `web/` directory.

**Step 2: Verify static files update**

Ensure `src/sgm/interface/web/static/index.html` has updated correctly and there are no compilation errors.

**Step 3: Run full pytest suite**

Run: `python3.12 -m pytest`
Expected: 81 passed.

---

### Task 7: Update Documentation and Changelog

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`

**Step 1: Document changes in CHANGELOG.md**

Add the new backup management, onboarding wizards, and update checkers in the unreleased changes section.

**Step 2: Update Architecture docs**

Update `docs/architecture.md` to document the new backup, import/export, and reset features of the API.
