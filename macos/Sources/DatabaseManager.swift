import Foundation
import SQLite3

public class DatabaseManager: ObservableObject {
    public static let shared = DatabaseManager()
    
    private var db: OpaquePointer?
    
    @Published public var accounts: [Account] = []
    @Published public var logs: [LogRecord] = []
    @Published public var renderHistory: [RenderSnapshot] = []
    @Published public var markedTotal: Int = 0
    @Published public var netWorth: Int = 0
    
    private init() {
        openDatabase()
        refreshAll()
    }
    
    deinit {
        if db != nil {
            sqlite3_close(db)
        }
    }
    
    private func getDatabasePath() -> String {
        let home = FileManager.default.homeDirectoryForCurrentUser
        return home.appendingPathComponent(".local/share/sgm/sigma.db").path
    }
    
    private func openDatabase() {
        let path = getDatabasePath()
        
        // Ensure parent directories exist
        let parentDir = URL(fileURLWithPath: path).deletingLastPathComponent()
        try? FileManager.default.createDirectory(at: parentDir, withIntermediateDirectories: true, attributes: nil)
        
        if sqlite3_open_v2(path, &db, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, nil) == SQLITE_OK {
            // Enable WAL mode for concurrent write access with CLI
            sqlite3_exec(db, "PRAGMA journal_mode=WAL;", nil, nil, nil)
            sqlite3_exec(db, "PRAGMA foreign_keys=ON;", nil, nil, nil)
        } else {
            print("Failed to open database at path: \(path)")
        }
    }
    
    public func refreshAll() {
        self.accounts = fetchAccounts()
        self.logs = fetchRecentLogs()
        self.renderHistory = fetchRenderHistory()
        self.markedTotal = fetchMarkedTotal()
        self.netWorth = calculateNetWorth()
    }
    
    private func getNowTimestamp() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss.SSS"
        formatter.timeZone = TimeZone(secondsFromGMT: 0) // UTC
        return formatter.string(from: Date())
    }
    
    private func getTodayDateString() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: Date())
    }
    
    // MARK: - Helper Statement Execution
    
    private func execute(sql: String, params: [Any] = []) -> Bool {
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
            let errorMsg = String(cString: sqlite3_errmsg(db))
            print("Prepare statement error: \(errorMsg)")
            return false
        }
        
        for (index, param) in params.enumerated() {
            let bindIndex = Int32(index + 1)
            if let stringVal = param as? String {
                sqlite3_bind_text(stmt, bindIndex, stringVal, -1, nil)
            } else if let intVal = param as? Int {
                sqlite3_bind_int64(stmt, bindIndex, Int64(intVal))
            } else if let doubleVal = param as? Double {
                sqlite3_bind_double(stmt, bindIndex, doubleVal)
            } else {
                sqlite3_bind_null(stmt, bindIndex)
            }
        }
        
        let result = sqlite3_step(stmt) == SQLITE_DONE
        sqlite3_finalize(stmt)
        return result
    }
    
    // MARK: - Accounts CRUD
    
    public func fetchAccounts() -> [Account] {
        var list: [Account] = []
        let query = "SELECT id, name, type, balance, credit_limit, updated_at, deleted_at FROM accounts WHERE id != 'deleted' AND deleted_at IS NULL ORDER BY id"
        var stmt: OpaquePointer?
        
        guard sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK else {
            return []
        }
        
        while sqlite3_step(stmt) == SQLITE_ROW {
            let id = String(cString: sqlite3_column_text(stmt, 0))
            let name = String(cString: sqlite3_column_text(stmt, 1))
            let typeStr = String(cString: sqlite3_column_text(stmt, 2))
            let balance = Int(sqlite3_column_int64(stmt, 3))
            let creditLimit = Int(sqlite3_column_int64(stmt, 4))
            let updatedAt = String(cString: sqlite3_column_text(stmt, 5))
            let deletedAt = sqlite3_column_text(stmt, 6) != nil ? String(cString: sqlite3_column_text(stmt, 6)) : nil
            
            let type = AccountType(rawValue: typeStr) ?? .debit
            list.append(Account(id: id, name: name, type: type, balance: balance, creditLimit: creditLimit, updatedAt: updatedAt, deletedAt: deletedAt))
        }
        sqlite3_finalize(stmt)
        return list
    }
    
    public func createAccount(id: String, name: String, type: AccountType, balance: Int, creditLimit: Int = 0) -> Result<Void, Error> {
        let cleanId = id.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if cleanId == "deleted" {
            return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Cannot create an account with the reserved ID 'deleted'."]))
        }
        if cleanId.isEmpty {
            return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Account ID cannot be empty."]))
        }
        
        let now = getNowTimestamp()
        
        // Check if there is an account (active or soft-deleted)
        var stmt: OpaquePointer?
        let checkSql = "SELECT id, deleted_at FROM accounts WHERE id = ?"
        var exists = false
        var isSoftDeleted = false
        
        if sqlite3_prepare_v2(db, checkSql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, cleanId, -1, nil)
            if sqlite3_step(stmt) == SQLITE_ROW {
                exists = true
                isSoftDeleted = sqlite3_column_text(stmt, 1) != nil
            }
            sqlite3_finalize(stmt)
        }
        
        if exists {
            if isSoftDeleted {
                // Revive the soft-deleted account
                let reviveSql = "UPDATE accounts SET name = ?, type = ?, balance = ?, credit_limit = ?, updated_at = ?, deleted_at = NULL WHERE id = ?"
                let success = execute(sql: reviveSql, params: [name, type.rawValue, balance, creditLimit, now, cleanId])
                if success {
                    refreshAll()
                    return .success(())
                } else {
                    return .failure(NSError(domain: "DatabaseError", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed to revive account."]))
                }
            } else {
                return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Account with ID '\(cleanId)' already exists."]))
            }
        }
        
        // Insert new account
        let insertSql = "INSERT INTO accounts (id, name, type, balance, credit_limit, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
        let success = execute(sql: insertSql, params: [cleanId, name, type.rawValue, balance, creditLimit, now])
        if success {
            refreshAll()
            return .success(())
        } else {
            return .failure(NSError(domain: "DatabaseError", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed to insert account."]))
        }
    }
    
    public func deleteAccount(accountId: String) -> Result<Void, Error> {
        if accountId == "deleted" {
            return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Cannot delete the reserved 'deleted' account."]))
        }
        
        var stmt: OpaquePointer?
        let checkSql = "SELECT id FROM accounts WHERE id = ? AND deleted_at IS NULL"
        var exists = false
        if sqlite3_prepare_v2(db, checkSql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, accountId, -1, nil)
            if sqlite3_step(stmt) == SQLITE_ROW {
                exists = true
            }
            sqlite3_finalize(stmt)
        }
        
        if !exists {
            return .failure(NSError(domain: "DatabaseError", code: 404, userInfo: [NSLocalizedDescriptionKey: "Account with ID '\(accountId)' does not exist."]))
        }
        
        let now = getNowTimestamp()
        
        // Ensure 'deleted' placeholder account exists in database
        let ensureSql = "SELECT id FROM accounts WHERE id = 'deleted'"
        var hasDeletedPlaceholder = false
        if sqlite3_prepare_v2(db, ensureSql, -1, &stmt, nil) == SQLITE_OK {
            if sqlite3_step(stmt) == SQLITE_ROW {
                hasDeletedPlaceholder = true
            }
            sqlite3_finalize(stmt)
        }
        
        if !hasDeletedPlaceholder {
            let insertPlaceholder = "INSERT INTO accounts (id, name, type, balance, credit_limit, updated_at) VALUES ('deleted', 'Deleted Account', 'debit', 0, 0, ?)"
            _ = execute(sql: insertPlaceholder, params: [now])
        }
        
        // Begin transaction
        sqlite3_exec(db, "BEGIN TRANSACTION;", nil, nil, nil)
        
        // Reassign movements and transfers
        let reassM = "UPDATE movements SET account_id = 'deleted', updated_at = ? WHERE account_id = ?"
        let reassT1 = "UPDATE transfers SET from_account = 'deleted', updated_at = ? WHERE from_account = ?"
        let reassT2 = "UPDATE transfers SET to_account = 'deleted', updated_at = ? WHERE to_account = ?"
        
        let softDel = "UPDATE accounts SET deleted_at = ?, updated_at = ? WHERE id = ?"
        
        let success = execute(sql: reassM, params: [now, accountId]) &&
                      execute(sql: reassT1, params: [now, accountId]) &&
                      execute(sql: reassT2, params: [now, accountId]) &&
                      execute(sql: softDel, params: [now, now, accountId])
        
        if success {
            sqlite3_exec(db, "COMMIT;", nil, nil, nil)
            refreshAll()
            return .success(())
        } else {
            sqlite3_exec(db, "ROLLBACK;", nil, nil, nil)
            return .failure(NSError(domain: "DatabaseError", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed to delete account."]))
        }
    }
    
    // MARK: - Movements CRUD
    
    public func createMovement(amount: Int, description: String, accountId: String, type: MovementType, marked: Bool, dateString: String? = nil) -> Result<Void, Error> {
        if accountId == "deleted" {
            return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Cannot manually log movements to the reserved 'deleted' account."]))
        }
        
        var stmt: OpaquePointer?
        let checkSql = "SELECT type, balance, credit_limit FROM accounts WHERE id = ? AND deleted_at IS NULL"
        var accountExists = false
        var accType = AccountType.debit
        var balance = 0
        var creditLimit = 0
        
        if sqlite3_prepare_v2(db, checkSql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, accountId, -1, nil)
            if sqlite3_step(stmt) == SQLITE_ROW {
                accountExists = true
                let typeStr = String(cString: sqlite3_column_text(stmt, 0))
                accType = AccountType(rawValue: typeStr) ?? .debit
                balance = Int(sqlite3_column_int64(stmt, 1))
                creditLimit = Int(sqlite3_column_int64(stmt, 2))
            }
            sqlite3_finalize(stmt)
        }
        
        if !accountExists {
            return .failure(NSError(domain: "DatabaseError", code: 404, userInfo: [NSLocalizedDescriptionKey: "Account with ID '\(accountId)' does not exist."]))
        }
        
        // Calculate new balance
        var newBalance = balance
        if type == .expense {
            if accType == .debit {
                newBalance = balance - amount
                if newBalance < 0 {
                    return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Insufficient funds in account '\(accountId)'. Available: \(balance), Required: \(amount)"]))
                }
            } else { // credit
                newBalance = balance + amount
                if newBalance > creditLimit {
                    let avail = creditLimit - balance
                    return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Insufficient credit in account '\(accountId)'. Available: \(avail), Required: \(amount)"]))
                }
            }
        } else { // income
            if accType == .debit {
                newBalance = balance + amount
            } else { // credit
                newBalance = balance - amount
            }
        }
        
        let now = getNowTimestamp()
        let createdDate = dateString ?? getTodayDateString()
        let movementId = UUID().uuidString.lowercased()
        
        sqlite3_exec(db, "BEGIN TRANSACTION;", nil, nil, nil)
        
        let updateAcc = "UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?"
        let insertM = "INSERT INTO movements (id, amount, description, account_id, type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
        let insertMark = "INSERT INTO movement_marks (movement_id, marked) VALUES (?, ?)"
        
        let success = execute(sql: updateAcc, params: [newBalance, now, accountId]) &&
                      execute(sql: insertM, params: [movementId, amount, description, accountId, type.rawValue, createdDate, now]) &&
                      execute(sql: insertMark, params: [movementId, marked ? 1 : 0])
        
        if success {
            sqlite3_exec(db, "COMMIT;", nil, nil, nil)
            refreshAll()
            return .success(())
        } else {
            sqlite3_exec(db, "ROLLBACK;", nil, nil, nil)
            return .failure(NSError(domain: "DatabaseError", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed to create movement."]))
        }
    }
    
    // MARK: - Transfers CRUD
    
    public func createTransfer(fromAccount: String, toAccount: String, amount: Int, dateString: String? = nil) -> Result<Void, Error> {
        if fromAccount == "deleted" || toAccount == "deleted" {
            return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Cannot manually transfer to or from the reserved 'deleted' account."]))
        }
        
        var stmt: OpaquePointer?
        let accSql = "SELECT type, balance, credit_limit FROM accounts WHERE id = ? AND deleted_at IS NULL"
        
        var fromExists = false, toExists = false
        var fromType = AccountType.debit, toType = AccountType.debit
        var fromBal = 0, toBal = 0
        var fromLimit = 0
        
        // Fetch source account details
        if sqlite3_prepare_v2(db, accSql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, fromAccount, -1, nil)
            if sqlite3_step(stmt) == SQLITE_ROW {
                fromExists = true
                fromType = AccountType(rawValue: String(cString: sqlite3_column_text(stmt, 0))) ?? .debit
                fromBal = Int(sqlite3_column_int64(stmt, 1))
                fromLimit = Int(sqlite3_column_int64(stmt, 2))
            }
            sqlite3_finalize(stmt)
        }
        
        // Fetch destination account details
        if sqlite3_prepare_v2(db, accSql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, toAccount, -1, nil)
            if sqlite3_step(stmt) == SQLITE_ROW {
                toExists = true
                toType = AccountType(rawValue: String(cString: sqlite3_column_text(stmt, 0))) ?? .debit
                toBal = Int(sqlite3_column_int64(stmt, 1))
            }
            sqlite3_finalize(stmt)
        }
        
        if !fromExists {
            return .failure(NSError(domain: "DatabaseError", code: 404, userInfo: [NSLocalizedDescriptionKey: "Source account '\(fromAccount)' does not exist."]))
        }
        if !toExists {
            return .failure(NSError(domain: "DatabaseError", code: 404, userInfo: [NSLocalizedDescriptionKey: "Destination account '\(toAccount)' does not exist."]))
        }
        
        // Withdraw calculation
        var newFromBal = fromBal
        if fromType == .debit {
            newFromBal = fromBal - amount
            if newFromBal < 0 {
                return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Insufficient funds in account '\(fromAccount)'. Available: \(fromBal), Required: \(amount)"]))
            }
        } else { // credit
            newFromBal = fromBal + amount
            if newFromBal > fromLimit {
                let avail = fromLimit - fromBal
                return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Insufficient credit in account '\(fromAccount)'. Available: \(avail), Required: \(amount)"]))
            }
        }
        
        // Deposit calculation
        var newToBal = toBal
        if toType == .debit {
            newToBal = toBal + amount
        } else { // credit
            newToBal = toBal - amount
        }
        
        let now = getNowTimestamp()
        let createdDate = dateString ?? getTodayDateString()
        let transferId = UUID().uuidString.lowercased()
        
        sqlite3_exec(db, "BEGIN TRANSACTION;", nil, nil, nil)
        
        let updateAcc = "UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?"
        let insertT = "INSERT INTO transfers (id, from_account, to_account, amount, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
        
        let success = execute(sql: updateAcc, params: [newFromBal, now, fromAccount]) &&
                      execute(sql: updateAcc, params: [newToBal, now, toAccount]) &&
                      execute(sql: insertT, params: [transferId, fromAccount, toAccount, amount, createdDate, now])
                      
        if success {
            sqlite3_exec(db, "COMMIT;", nil, nil, nil)
            refreshAll()
            return .success(())
        } else {
            sqlite3_exec(db, "ROLLBACK;", nil, nil, nil)
            return .failure(NSError(domain: "DatabaseError", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed to execute transfer."]))
        }
    }
    
    // MARK: - Query Helper Methods
    
    public func fetchRecentLogs(limit: Int = 15) -> [LogRecord] {
        var list: [LogRecord] = []
        let query = """
            SELECT 
                'm-' || id AS unique_id,
                'movement' AS record_kind,
                type,
                amount,
                description,
                account_id,
                created_at
            FROM movements
            WHERE deleted_at IS NULL
            
            UNION ALL
            
            SELECT 
                't-' || id AS unique_id,
                'transfer' AS record_kind,
                'transfer' AS type,
                amount,
                from_account || ' -> ' || to_account AS description,
                '' AS account_id,
                created_at
            FROM transfers
            WHERE deleted_at IS NULL
            
            ORDER BY created_at DESC
            LIMIT ?
        """
        var stmt: OpaquePointer?
        
        guard sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK else {
            return []
        }
        
        sqlite3_bind_int(stmt, 1, Int32(limit))
        
        while sqlite3_step(stmt) == SQLITE_ROW {
            let fullId = String(cString: sqlite3_column_text(stmt, 0))
            let recordKind = String(cString: sqlite3_column_text(stmt, 1))
            let typeStr = String(cString: sqlite3_column_text(stmt, 2))
            let amount = Int(sqlite3_column_int64(stmt, 3))
            let description = String(cString: sqlite3_column_text(stmt, 4))
            let accountId = String(cString: sqlite3_column_text(stmt, 5))
            let createdAt = String(cString: sqlite3_column_text(stmt, 6))
            
            // Generate visual ID format e.g. "m-3f2504e0"
            let visualId: String
            if fullId.count >= 10 {
                let prefix = fullId.prefix(10) // "m-" + 8 char hex
                visualId = String(prefix)
            } else {
                visualId = fullId
            }
            
            let recordType: LogRecordType
            if recordKind == "transfer" {
                recordType = .transfer
            } else {
                recordType = typeStr == "income" ? .income : .expense
            }
            
            list.append(LogRecord(id: visualId, type: recordType, amount: amount, description: description, accountId: accountId, createdAt: createdAt))
        }
        sqlite3_finalize(stmt)
        return list
    }
    
    public func fetchMarkedTotal() -> Int {
        let query = """
            SELECT 
                COALESCE(SUM(CASE WHEN m.type = 'income' THEN m.amount ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN m.type = 'expense' THEN m.amount ELSE 0 END), 0)
            FROM movements m
            JOIN movement_marks mm ON m.id = mm.movement_id
            WHERE mm.marked = 1 AND m.deleted_at IS NULL
        """
        var stmt: OpaquePointer?
        var total = 0
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            if sqlite3_step(stmt) == SQLITE_ROW {
                total = Int(sqlite3_column_int64(stmt, 0))
            }
            sqlite3_finalize(stmt)
        }
        return total
    }
    
    public func calculateNetWorth() -> Int {
        let query = "SELECT type, balance FROM accounts WHERE id != 'deleted' AND deleted_at IS NULL"
        var stmt: OpaquePointer?
        var total = 0
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            while sqlite3_step(stmt) == SQLITE_ROW {
                let typeStr = String(cString: sqlite3_column_text(stmt, 0))
                let balance = Int(sqlite3_column_int64(stmt, 1))
                if typeStr == "debit" {
                    total += balance
                } else { // credit account balance increases debt
                    total -= balance
                }
            }
            sqlite3_finalize(stmt)
        }
        return total
    }
    
    // MARK: - Render Run
    
    public func fetchRenderHistory(limit: Int = 15) -> [RenderSnapshot] {
        var list: [RenderSnapshot] = []
        let query = "SELECT id, net_amount, rendered_at, updated_at, deleted_at FROM render_history WHERE deleted_at IS NULL ORDER BY rendered_at DESC LIMIT ?"
        var stmt: OpaquePointer?
        
        guard sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK else {
            return []
        }
        sqlite3_bind_int(stmt, 1, Int32(limit))
        
        while sqlite3_step(stmt) == SQLITE_ROW {
            let fullId = String(cString: sqlite3_column_text(stmt, 0))
            let netAmount = Int(sqlite3_column_int64(stmt, 1))
            let renderedAt = String(cString: sqlite3_column_text(stmt, 2))
            let updatedAt = String(cString: sqlite3_column_text(stmt, 3))
            let deletedAt = sqlite3_column_text(stmt, 4) != nil ? String(cString: sqlite3_column_text(stmt, 4)) : nil
            
            // Visual ID slicing
            let visualId = fullId.count >= 8 ? String(fullId.prefix(8)) : fullId
            
            list.append(RenderSnapshot(id: visualId, netAmount: netAmount, renderedAt: renderedAt, updatedAt: updatedAt, deletedAt: deletedAt))
        }
        sqlite3_finalize(stmt)
        return list
    }
    
    public func executeRender() -> Result<(netAmount: Int, count: Int), Error> {
        sqlite3_exec(db, "BEGIN TRANSACTION;", nil, nil, nil)
        
        // 1. Calculate net amount of marked movements
        let sumSql = """
            SELECT 
                COALESCE(SUM(CASE WHEN m.type = 'income' THEN m.amount ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN m.type = 'expense' THEN m.amount ELSE 0 END), 0),
                COUNT(m.id)
            FROM movements m
            JOIN movement_marks mm ON m.id = mm.movement_id
            WHERE mm.marked = 1 AND m.deleted_at IS NULL
        """
        
        var stmt: OpaquePointer?
        var netAmount = 0
        var count = 0
        
        if sqlite3_prepare_v2(db, sumSql, -1, &stmt, nil) == SQLITE_OK {
            if sqlite3_step(stmt) == SQLITE_ROW {
                netAmount = Int(sqlite3_column_int64(stmt, 0))
                count = Int(sqlite3_column_int64(stmt, 1))
            }
            sqlite3_finalize(stmt)
        }
        
        if count == 0 {
            sqlite3_exec(db, "COMMIT;", nil, nil, nil)
            return .success((0, 0))
        }
        
        let renderId = UUID().uuidString.lowercased()
        let today = getTodayDateString()
        let now = getNowTimestamp()
        
        // 2. Insert into render history
        let insertR = "INSERT INTO render_history (id, net_amount, rendered_at, updated_at) VALUES (?, ?, ?, ?)"
        let insertSuccess = execute(sql: insertR, params: [renderId, netAmount, today, now])
        
        if !insertSuccess {
            sqlite3_exec(db, "ROLLBACK;", nil, nil, nil)
            return .failure(NSError(domain: "DatabaseError", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed to write render history."]))
        }
        
        // 3. Retrieve movement IDs being rendered to update timestamps and unmark
        let fetchIdsSql = """
            SELECT m.id FROM movements m
            JOIN movement_marks mm ON m.id = mm.movement_id
            WHERE mm.marked = 1 AND m.deleted_at IS NULL
        """
        var mIds: [String] = []
        if sqlite3_prepare_v2(db, fetchIdsSql, -1, &stmt, nil) == SQLITE_OK {
            while sqlite3_step(stmt) == SQLITE_ROW {
                mIds.append(String(cString: sqlite3_column_text(stmt, 0)))
            }
            sqlite3_finalize(stmt)
        }
        
        var updateSuccess = true
        for mId in mIds {
            let updateM = "UPDATE movements SET updated_at = ? WHERE id = ?"
            let updateMark = "UPDATE movement_marks SET marked = 0 WHERE movement_id = ?"
            
            if !execute(sql: updateM, params: [now, mId]) || !execute(sql: updateMark, params: [mId]) {
                updateSuccess = false
                break
            }
        }
        
        if updateSuccess {
            sqlite3_exec(db, "COMMIT;", nil, nil, nil)
            refreshAll()
            return .success((netAmount, count))
        } else {
            sqlite3_exec(db, "ROLLBACK;", nil, nil, nil)
            return .failure(NSError(domain: "DatabaseError", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed to update movement marks during render."]))
        }
    }
    
    // MARK: - Delete Records by prefixed ID
    
    public func deleteRecord(visualId: String) -> Result<Void, Error> {
        let cleanId = visualId.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        
        if cleanId.hasPrefix("m-") {
            let mPrefix = String(cleanId.dropFirst(2))
            return deleteMovementByPrefix(prefix: mPrefix)
        } else if cleanId.hasPrefix("t-") {
            let tPrefix = String(cleanId.dropFirst(2))
            return deleteTransferByPrefix(prefix: tPrefix)
        } else {
            return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid ID format. Must start with 'm-' or 't-'"]))
        }
    }
    
    private func deleteMovementByPrefix(prefix: String) -> Result<Void, Error> {
        // Resolve prefix
        let query = "SELECT id FROM movements WHERE id LIKE ? AND deleted_at IS NULL"
        var stmt: OpaquePointer?
        var matches: [String] = []
        
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, prefix + "%", -1, nil)
            while sqlite3_step(stmt) == SQLITE_ROW {
                matches.append(String(cString: sqlite3_column_text(stmt, 0)))
            }
            sqlite3_finalize(stmt)
        }
        
        if matches.isEmpty {
            return .failure(NSError(domain: "DatabaseError", code: 404, userInfo: [NSLocalizedDescriptionKey: "Record 'm-\(prefix)' not found."]))
        } else if matches.count > 1 {
            return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Record ID 'm-\(prefix)' is ambiguous."]))
        }
        
        let actualId = matches[0]
        
        // 1. Get movement details
        let fetchM = """
            SELECT m.amount, m.type, m.account_id, a.type as acc_type, a.balance
            FROM movements m
            JOIN accounts a ON m.account_id = a.id
            WHERE m.id = ?
        """
        
        var amount = 0
        var mTypeStr = ""
        var accId = ""
        var accTypeStr = ""
        var currentBalance = 0
        var detailsFound = false
        
        if sqlite3_prepare_v2(db, fetchM, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, actualId, -1, nil)
            if sqlite3_step(stmt) == SQLITE_ROW {
                amount = Int(sqlite3_column_int64(stmt, 0))
                mTypeStr = String(cString: sqlite3_column_text(stmt, 1))
                accId = String(cString: sqlite3_column_text(stmt, 2))
                accTypeStr = String(cString: sqlite3_column_text(stmt, 3))
                currentBalance = Int(sqlite3_column_int64(stmt, 4))
                detailsFound = true
            }
            sqlite3_finalize(stmt)
        }
        
        if !detailsFound {
            return .failure(NSError(domain: "DatabaseError", code: 404, userInfo: [NSLocalizedDescriptionKey: "Record details not found."]))
        }
        
        let mType = MovementType(rawValue: mTypeStr) ?? .expense
        let accType = AccountType(rawValue: accTypeStr) ?? .debit
        
        // 2. Reverse balance calculation
        var newBalance = currentBalance
        if mType == .expense {
            if accType == .debit {
                newBalance = currentBalance + amount
            } else { // credit
                newBalance = currentBalance - amount
            }
        } else { // income
            if accType == .debit {
                newBalance = currentBalance - amount
            } else { // credit
                newBalance = currentBalance + amount
            }
        }
        
        let now = getNowTimestamp()
        
        sqlite3_exec(db, "BEGIN TRANSACTION;", nil, nil, nil)
        
        let updateAcc = "UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?"
        let softDelM = "UPDATE movements SET deleted_at = ?, updated_at = ? WHERE id = ?"
        
        let success = execute(sql: updateAcc, params: [newBalance, now, accId]) &&
                      execute(sql: softDelM, params: [now, now, actualId])
                      
        if success {
            sqlite3_exec(db, "COMMIT;", nil, nil, nil)
            refreshAll()
            return .success(())
        } else {
            sqlite3_exec(db, "ROLLBACK;", nil, nil, nil)
            return .failure(NSError(domain: "DatabaseError", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed to delete movement."]))
        }
    }
    
    private func deleteTransferByPrefix(prefix: String) -> Result<Void, Error> {
        // Resolve prefix
        let query = "SELECT id FROM transfers WHERE id LIKE ? AND deleted_at IS NULL"
        var stmt: OpaquePointer?
        var matches: [String] = []
        
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, prefix + "%", -1, nil)
            while sqlite3_step(stmt) == SQLITE_ROW {
                matches.append(String(cString: sqlite3_column_text(stmt, 0)))
            }
            sqlite3_finalize(stmt)
        }
        
        if matches.isEmpty {
            return .failure(NSError(domain: "DatabaseError", code: 404, userInfo: [NSLocalizedDescriptionKey: "Record 't-\(prefix)' not found."]))
        } else if matches.count > 1 {
            return .failure(NSError(domain: "DatabaseError", code: 400, userInfo: [NSLocalizedDescriptionKey: "Record ID 't-\(prefix)' is ambiguous."]))
        }
        
        let actualId = matches[0]
        
        // 1. Get transfer details
        let fetchT = """
            SELECT t.amount, t.from_account, t.to_account, 
                   af.type as from_type, af.balance as from_balance,
                   at.type as to_type, at.balance as to_balance
            FROM transfers t
            JOIN accounts af ON t.from_account = af.id
            JOIN accounts at ON t.to_account = at.id
            WHERE t.id = ?
        """
        
        var amount = 0
        var fromAcc = ""
        var toAcc = ""
        var fromTypeStr = ""
        var fromBal = 0
        var toTypeStr = ""
        var toBal = 0
        var detailsFound = false
        
        if sqlite3_prepare_v2(db, fetchT, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, actualId, -1, nil)
            if sqlite3_step(stmt) == SQLITE_ROW {
                amount = Int(sqlite3_column_int64(stmt, 0))
                fromAcc = String(cString: sqlite3_column_text(stmt, 1))
                toAcc = String(cString: sqlite3_column_text(stmt, 2))
                fromTypeStr = String(cString: sqlite3_column_text(stmt, 3))
                fromBal = Int(sqlite3_column_int64(stmt, 4))
                toTypeStr = String(cString: sqlite3_column_text(stmt, 5))
                toBal = Int(sqlite3_column_int64(stmt, 6))
                detailsFound = true
            }
            sqlite3_finalize(stmt)
        }
        
        if !detailsFound {
            return .failure(NSError(domain: "DatabaseError", code: 404, userInfo: [NSLocalizedDescriptionKey: "Record details not found."]))
        }
        
        let fromType = AccountType(rawValue: fromTypeStr) ?? .debit
        let toType = AccountType(rawValue: toTypeStr) ?? .debit
        
        // 2. Reverse balances
        // From account: reverse withdrawal (debit: +amount, credit: -amount)
        let newFromBal = fromType == .debit ? fromBal + amount : fromBal - amount
        // To account: reverse deposit (debit: -amount, credit: +amount)
        let newToBal = toType == .debit ? toBal - amount : toBal + amount
        
        let now = getNowTimestamp()
        
        sqlite3_exec(db, "BEGIN TRANSACTION;", nil, nil, nil)
        
        let updateAcc = "UPDATE accounts SET balance = ?, updated_at = ? WHERE id = ?"
        let softDelT = "UPDATE transfers SET deleted_at = ?, updated_at = ? WHERE id = ?"
        
        let success = execute(sql: updateAcc, params: [newFromBal, now, fromAcc]) &&
                      execute(sql: updateAcc, params: [newToBal, now, toAcc]) &&
                      execute(sql: softDelT, params: [now, now, actualId])
                      
        if success {
            sqlite3_exec(db, "COMMIT;", nil, nil, nil)
            refreshAll()
            return .success(())
        } else {
            sqlite3_exec(db, "ROLLBACK;", nil, nil, nil)
            return .failure(NSError(domain: "DatabaseError", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed to delete transfer."]))
        }
    }
}
