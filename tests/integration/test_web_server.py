from fastapi.testclient import TestClient

def test_web_server_full_flow(monkeypatch, tmp_path):
    # Mock DB path to keep tests isolated
    from sgm.infrastructure.database import init_db
    db_file = tmp_path / "test_sigma.db"
    monkeypatch.setattr("sgm.infrastructure.database.get_db_path", lambda: db_file)
    init_db(db_file)
    
    from sgm.interface.web.server import app
    client = TestClient(app)
    
    # Set app DB state
    app.state.db_path = db_file
    
    # 1. Verify initially no accounts exist
    response = client.get("/api/v1/accounts")
    assert response.status_code == 200
    assert len(response.json()) == 0
    
    # 2. Create debit account
    response = client.post("/api/v1/accounts", json={
        "id": "bank",
        "name": "Checking Account",
        "type": "debit",
        "initial_balance": 100000,
        "credit_limit": 0
    })
    assert response.status_code == 200
    assert response.json()["account"]["id"] == "bank"
    assert response.json()["account"]["balance"] == 100000
    
    # 3. Create credit account
    response = client.post("/api/v1/accounts", json={
        "id": "cc",
        "name": "Visa Card",
        "type": "credit",
        "initial_balance": 0,
        "credit_limit": 500000
    })
    assert response.status_code == 200
    
    # 4. Log income
    response = client.post("/api/v1/transactions/income", json={
        "amount": 50000,
        "description": "Salary Bonus",
        "mark": True,
        "account_id": "bank"
    })
    assert response.status_code == 200
    
    # Verify account balance updated
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["net_balance"] == 150000
    assert data["marked_total"] == 50000
    
    # 5. Log expense on credit card
    response = client.post("/api/v1/transactions/expense", json={
        "amount": 20000,
        "description": "Coffee Machine",
        "mark": True,
        "account_id": "cc"
    })
    assert response.status_code == 200
    
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    # net = bank (150000) - cc spend (20000) = 130000
    assert data["net_balance"] == 130000
    # marked total = income (50000) - expense (20000) = 30000
    assert data["marked_total"] == 30000
    
    # 6. Log transfer
    response = client.post("/api/v1/transactions/transfer", json={
        "from_account": "bank",
        "to_account": "cc",
        "amount": 10000
    })
    assert response.status_code == 200
    
    # Verify balances updated: bank 140000, cc spent 10000
    # Net remains 130000
    response = client.get("/api/v1/status")
    assert response.json()["net_balance"] == 130000
    
    # 7. Run render cycle
    response = client.post("/api/v1/render")
    assert response.status_code == 200
    assert response.json()["net_amount"] == 30000
    assert response.json()["count"] == 2
    
    # Marked balance should now be 0
    response = client.get("/api/v1/status")
    assert response.json()["marked_total"] == 0
    
    # 8. Check render history
    response = client.get("/api/v1/render/history")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["net_amount"] == 30000

def test_web_transfer_credit_card_restrictions(monkeypatch, tmp_path):
    from sgm.infrastructure.database import init_db
    from fastapi.testclient import TestClient
    db_file = tmp_path / "test_sigma.db"
    monkeypatch.setattr("sgm.infrastructure.database.get_db_path", lambda: db_file)
    monkeypatch.setattr("sgm.interface.web.server.get_current_db_path", lambda: db_file)
    init_db(db_file)
    
    from sgm.interface.web.server import app
    client = TestClient(app)
    
    # Create accounts
    client.post("/api/v1/accounts", json={"id": "wallet", "name": "Cash", "type": "debit", "initial_balance": 10000})
    client.post("/api/v1/accounts", json={"id": "cc", "name": "Visa", "type": "credit", "initial_balance": 0, "credit_limit": 500000})
    
    # 1. Try transferring from credit card
    response = client.post("/api/v1/transactions/transfer", json={
        "from_account": "cc",
        "to_account": "wallet",
        "amount": 1000
    })
    assert response.status_code == 400
    assert "Transfers from credit cards are not allowed." in response.json()["detail"]
    
    # 2. Try transferring to credit card leaving negative balance
    response = client.post("/api/v1/transactions/transfer", json={
        "from_account": "wallet",
        "to_account": "cc",
        "amount": 1000
    })
    assert response.status_code == 400
    assert "Transfer would leave credit card 'cc' with a negative balance." in response.json()["detail"]
