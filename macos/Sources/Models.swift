import Foundation

public enum AccountType: String, Codable, CaseIterable {
    case debit = "debit"
    case credit = "credit"
}

public struct Account: Identifiable, Codable, Equatable {
    public let id: String
    public var name: String
    public var type: AccountType
    public var balance: Int
    public var creditLimit: Int
    public var updatedAt: String
    public var deletedAt: String?

    public init(id: String, name: String, type: AccountType, balance: Int, creditLimit: Int = 0, updatedAt: String = "", deletedAt: String? = nil) {
        self.id = id
        self.name = name
        self.type = type
        self.balance = balance
        self.creditLimit = creditLimit
        self.updatedAt = updatedAt
        self.deletedAt = deletedAt
    }
}

public enum MovementType: String, Codable {
    case income = "income"
    case expense = "expense"
}

public struct Movement: Identifiable, Codable, Equatable {
    public let id: String
    public var amount: Int
    public var description: String
    public var accountId: String
    public var type: MovementType
    public var createdAt: String
    public var updatedAt: String
    public var deletedAt: String?
    public var marked: Bool

    public init(id: String, amount: Int, description: String, accountId: String, type: MovementType, createdAt: String, updatedAt: String = "", deletedAt: String? = nil, marked: Bool = false) {
        self.id = id
        self.amount = amount
        self.description = description
        self.accountId = accountId
        self.type = type
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.deletedAt = deletedAt
        self.marked = marked
    }
}

public struct Transfer: Identifiable, Codable, Equatable {
    public let id: String
    public var fromAccount: String
    public var toAccount: String
    public var amount: Int
    public var createdAt: String
    public var updatedAt: String
    public var deletedAt: String?

    public init(id: String, fromAccount: String, toAccount: String, amount: Int, createdAt: String, updatedAt: String = "", deletedAt: String? = nil) {
        self.id = id
        self.fromAccount = fromAccount
        self.toAccount = toAccount
        self.amount = amount
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.deletedAt = deletedAt
    }
}

public struct RenderSnapshot: Identifiable, Codable, Equatable {
    public let id: String
    public var netAmount: Int
    public var renderedAt: String
    public var updatedAt: String
    public var deletedAt: String?

    public init(id: String, netAmount: Int, renderedAt: String, updatedAt: String = "", deletedAt: String? = nil) {
        self.id = id
        self.netAmount = netAmount
        self.renderedAt = renderedAt
        self.updatedAt = updatedAt
        self.deletedAt = deletedAt
    }
}

// Helper struct for Log display in Table view
public enum LogRecordType: String, Codable {
    case income = "income"
    case expense = "expense"
    case transfer = "transfer"
}

public struct LogRecord: Identifiable, Codable, Equatable {
    public let id: String          // e.g. "m-3f2504e0" or "t-9c3f1b4a"
    public let type: LogRecordType
    public let amount: Int
    public let description: String
    public let accountId: String
    public let createdAt: String
    
    public init(id: String, type: LogRecordType, amount: Int, description: String, accountId: String, createdAt: String) {
        self.id = id
        self.type = type
        self.amount = amount
        self.description = description
        self.accountId = accountId
        self.createdAt = createdAt
    }
}
