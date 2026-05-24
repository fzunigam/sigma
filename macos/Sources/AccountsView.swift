import SwiftUI

public struct AccountsView: View {
    @ObservedObject var db = DatabaseManager.shared
    
    // Account Form Fields
    @State private var accountId: String = ""
    @State private var accountName: String = ""
    @State private var accountType: AccountType = .debit
    @State private var initialBalance: String = "0"
    @State private var creditLimit: String = "0"
    
    // Notifications
    @State private var messageText: String = ""
    @State private var isError: Bool = false
    
    public init() {}
    
    public var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Header
            Text("ACCOUNTS")
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.black)
            
            Rectangle()
                .fill(Color.black)
                .frame(height: 1)
            
            HStack(alignment: .top, spacing: 40) {
                // Form: Add Account (Left Column)
                VStack(alignment: .leading, spacing: 14) {
                    Text("ADD ACCOUNT")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.black)
                    
                    VStack(alignment: .leading, spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("ACCOUNT ID (LOWERCASE, NO SPACES)")
                                .font(.system(size: 9, weight: .bold))
                                .foregroundColor(.gray)
                            TextField("e.g. bank", text: $accountId)
                                .textFieldStyle(PlainTextFieldStyle())
                                .padding(8)
                                .border(Color.black, width: 1)
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("ACCOUNT NAME")
                                .font(.system(size: 9, weight: .bold))
                                .foregroundColor(.gray)
                            TextField("e.g. Main Savings", text: $accountName)
                                .textFieldStyle(PlainTextFieldStyle())
                                .padding(8)
                                .border(Color.black, width: 1)
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("TYPE")
                                .font(.system(size: 9, weight: .bold))
                                .foregroundColor(.gray)
                            Picker("", selection: $accountType) {
                                Text("DEBIT").tag(AccountType.debit)
                                Text("CREDIT").tag(AccountType.credit)
                            }
                            .pickerStyle(SegmentedPickerStyle())
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("INITIAL BALANCE")
                                .font(.system(size: 9, weight: .bold))
                                .foregroundColor(.gray)
                            TextField("e.g. 1000", text: $initialBalance)
                                .textFieldStyle(PlainTextFieldStyle())
                                .padding(8)
                                .border(Color.black, width: 1)
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("CREDIT LIMIT")
                                .font(.system(size: 9, weight: .bold))
                                .foregroundColor(accountType == .credit ? Color.gray : Color(white: 0.8))
                            TextField("e.g. 500000", text: $creditLimit)
                                .textFieldStyle(PlainTextFieldStyle())
                                .padding(8)
                                .border(accountType == .credit ? Color.black : Color(white: 0.8), width: 1)
                                .disabled(accountType == .debit)
                        }
                        
                        Button(action: addAccount) {
                            Text("CREATE ACCOUNT")
                                .font(.system(size: 11, weight: .bold))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 10)
                                .background(Color.black)
                                .foregroundColor(.white)
                        }
                        .buttonStyle(PlainButtonStyle())
                        .padding(.top, 6)
                    }
                    .padding(16)
                    .border(Color.black, width: 1)
                    
                    if !messageText.isEmpty {
                        Text(messageText)
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.black)
                    }
                }
                .frame(width: 320)
                
                // List: Active Accounts (Right Column)
                VStack(alignment: .leading, spacing: 14) {
                    Text("ACTIVE ACCOUNTS")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.black)
                    
                    VStack(spacing: 0) {
                        // Header
                        HStack {
                            Text("NAME (ID)").font(.system(size: 10, weight: .bold)).frame(minWidth: 150, alignment: .leading)
                            Text("BALANCE").font(.system(size: 10, weight: .bold)).frame(width: 100, alignment: .trailing)
                            Text("ACTION").font(.system(size: 10, weight: .bold)).frame(width: 80, alignment: .trailing)
                        }
                        .padding(.vertical, 8)
                        .padding(.horizontal, 10)
                        .background(Color(white: 0.95))
                        
                        Rectangle().fill(Color.black).frame(height: 1)
                        
                        if db.accounts.isEmpty {
                            Text("No accounts found.")
                                .font(.system(size: 12))
                                .foregroundColor(.gray)
                                .padding(20)
                                .frame(maxWidth: .infinity, alignment: .center)
                        } else {
                            ScrollView {
                                VStack(spacing: 0) {
                                    ForEach(db.accounts) { acc in
                                        HStack {
                                            VStack(alignment: .leading, spacing: 2) {
                                                Text(acc.name)
                                                    .font(.system(size: 12, weight: .bold))
                                                Text(acc.id)
                                                    .font(.system(size: 10, design: .monospaced))
                                                    .foregroundColor(.gray)
                                            }
                                            .frame(minWidth: 150, alignment: .leading)
                                            
                                            Text("\(acc.balance)")
                                                .font(.system(size: 12))
                                                .frame(width: 100, alignment: .trailing)
                                            
                                            Button(action: {
                                                confirmDelete(accountId: acc.id)
                                            }) {
                                                Text("[DELETE]")
                                                    .font(.system(size: 10, weight: .bold))
                                                    .foregroundColor(.black)
                                            }
                                            .buttonStyle(PlainButtonStyle())
                                            .frame(width: 80, alignment: .trailing)
                                        }
                                        .padding(.vertical, 10)
                                        .padding(.horizontal, 10)
                                        
                                        Rectangle().fill(Color(white: 0.9)).frame(height: 1)
                                    }
                                }
                            }
                        }
                    }
                    .border(Color.black, width: 1)
                }
            }
            Spacer()
        }
        .padding(24)
        .background(Color.white)
    }
    
    private func addAccount() {
        messageText = ""
        
        let idClean = accountId.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let nameClean = accountName.trimmingCharacters(in: .whitespacesAndNewlines)
        
        guard !idClean.isEmpty else {
            isError = true
            messageText = "Account ID cannot be empty."
            return
        }
        guard !nameClean.isEmpty else {
            isError = true
            messageText = "Account Name cannot be empty."
            return
        }
        
        guard let balVal = Int(initialBalance) else {
            isError = true
            messageText = "Initial balance must be an integer."
            return
        }
        
        var limitVal = 0
        if accountType == .credit {
            guard let parsedLimit = Int(creditLimit), parsedLimit >= 0 else {
                isError = true
                messageText = "Credit limit must be a positive integer."
                return
            }
            limitVal = parsedLimit
        }
        
        let result = db.createAccount(id: idClean, name: nameClean, type: accountType, balance: balVal, creditLimit: limitVal)
        switch result {
        case .success:
            isError = false
            messageText = "Account '\(nameClean)' created successfully."
            
            // Reset fields
            accountId = ""
            accountName = ""
            initialBalance = "0"
            creditLimit = "0"
            accountType = .debit
            
        case .failure(let error):
            isError = true
            messageText = error.localizedDescription
        }
    }
    
    private func confirmDelete(accountId: String) {
        let alert = NSAlert()
        alert.messageText = "Delete Account"
        alert.informativeText = "Are you sure you want to delete account '\(accountId)'? Movements and transfers will be reassigned to the 'deleted' account."
        alert.alertStyle = .warning
        alert.addButton(withTitle: "Delete")
        alert.addButton(withTitle: "Cancel")
        
        let response = alert.runModal()
        if response == .alertFirstButtonReturn {
            let result = db.deleteAccount(accountId: accountId)
            switch result {
            case .success:
                isError = false
                messageText = "Account '\(accountId)' deleted successfully."
            case .failure(let error):
                isError = true
                messageText = error.localizedDescription
            }
        }
    }
}

struct AccountsView_Previews: PreviewProvider {
    static var previews: some View {
        AccountsView()
    }
}
