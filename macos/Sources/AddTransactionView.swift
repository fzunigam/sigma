import SwiftUI

public struct AddTransactionView: View {
    @Binding var isPresented: Bool
    @ObservedObject var db = DatabaseManager.shared
    
    @State private var mode: TransactionMode = .movement
    
    // Movement Fields
    @State private var mAccountId: String = ""
    @State private var mType: MovementType = .expense
    @State private var mAmount: String = ""
    @State private var mDescription: String = ""
    @State private var mMarked: Bool = true
    @State private var mDate: Date = Date()
    
    // Transfer Fields
    @State private var tFromAccountId: String = ""
    @State private var tToAccountId: String = ""
    @State private var tAmount: String = ""
    @State private var tDate: Date = Date()
    
    // Errors
    @State private var errorMessage: String = ""
    
    enum TransactionMode {
        case movement, transfer
    }
    
    public init(isPresented: Binding<Bool>) {
        self._isPresented = isPresented
    }
    
    public var body: some View {
        VStack(spacing: 0) {
            // Title Bar
            HStack {
                Text("LOG TRANSACTION")
                    .font(.system(size: 16, weight: .black))
                    .foregroundColor(.black)
                Spacer()
                Button(action: {
                    isPresented = false
                }) {
                    Text("[X]")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.black)
                }
                .buttonStyle(PlainButtonStyle())
            }
            .padding(.horizontal, 24)
            .padding(.top, 24)
            .padding(.bottom, 16)
            
            Rectangle()
                .fill(Color.black)
                .frame(height: 1)
            
            // Mode Selectors
            HStack(spacing: 0) {
                Button(action: { mode = .movement }) {
                    Text("MOVEMENT")
                        .font(.system(size: 12, weight: .bold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(mode == .movement ? Color.black : Color.white)
                        .foregroundColor(mode == .movement ? Color.white : Color.black)
                }
                .buttonStyle(PlainButtonStyle())
                
                Button(action: { mode = .transfer }) {
                    Text("TRANSFER")
                        .font(.system(size: 12, weight: .bold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(mode == .transfer ? Color.black : Color.white)
                        .foregroundColor(mode == .transfer ? Color.white : Color.black)
                }
                .buttonStyle(PlainButtonStyle())
            }
            .border(Color.black, width: 1)
            .padding(.horizontal, 24)
            .padding(.vertical, 16)
            
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if mode == .movement {
                        movementForm
                    } else {
                        transferForm
                    }
                    
                    if !errorMessage.isEmpty {
                        Text(errorMessage)
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.black)
                            .padding(.vertical, 4)
                    }
                    
                    // Action Buttons
                    HStack(spacing: 12) {
                        Button(action: {
                            isPresented = false
                        }) {
                            Text("CANCEL")
                                .font(.system(size: 12, weight: .bold))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 10)
                                .background(Color.white)
                                .foregroundColor(.black)
                                .border(Color.black, width: 1)
                        }
                        .buttonStyle(PlainButtonStyle())
                        
                        Button(action: submitTransaction) {
                            Text("LOG TRANSACTION")
                                .font(.system(size: 12, weight: .bold))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 10)
                                .background(Color.black)
                                .foregroundColor(.white)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                    .padding(.top, 10)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
            }
        }
        .frame(width: 400, height: 480)
        .background(Color.white)
        .preferredColorScheme(.light)
        .onAppear {
            // Set defaults if active accounts exist
            if let firstId = db.accounts.first?.id {
                mAccountId = firstId
                tFromAccountId = firstId
                if db.accounts.count > 1 {
                    tToAccountId = db.accounts[1].id
                } else {
                    tToAccountId = firstId
                }
            }
        }
    }
    
    // MARK: - Movement Form View
    
    private var movementForm: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("ACCOUNT")
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(.black)
            
            Menu {
                if db.accounts.isEmpty {
                    Button(action: {}) {
                        Text("No accounts")
                    }
                    .disabled(true)
                } else {
                    ForEach(db.accounts) { acc in
                        Button(action: {
                            mAccountId = acc.id
                        }) {
                            Text("\(acc.name) (\(acc.id))")
                        }
                    }
                }
            } label: {
                HStack {
                    if let selectedAcc = db.accounts.first(where: { $0.id == mAccountId }) {
                        Text("\(selectedAcc.name) (\(selectedAcc.id))")
                            .font(.system(size: 12))
                            .foregroundColor(.black)
                    } else {
                        Text("Select Account")
                            .font(.system(size: 12))
                            .foregroundColor(.gray)
                    }
                    Spacer()
                    Text("▼")
                        .font(.system(size: 8))
                        .foregroundColor(.black)
                }
                .padding(8)
                .background(Color.white)
                .border(Color.black, width: 1)
            }
            .menuStyle(.borderlessButton)
            
            HStack(spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("TYPE")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.black)
                    
                    HStack(spacing: 0) {
                        Button(action: { mType = .expense }) {
                            Text("EXPENSE")
                                .font(.system(size: 10, weight: .bold))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 6)
                                .background(mType == .expense ? Color.black : Color.white)
                                .foregroundColor(mType == .expense ? Color.white : Color.black)
                        }
                        .buttonStyle(PlainButtonStyle())
                        
                        Button(action: { mType = .income }) {
                            Text("INCOME")
                                .font(.system(size: 10, weight: .bold))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 6)
                                .background(mType == .income ? Color.black : Color.white)
                                .foregroundColor(mType == .income ? Color.white : Color.black)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                    .border(Color.black, width: 1)
                }
                
                VStack(alignment: .leading, spacing: 6) {
                    Text("MARKED (UNRENDERED)")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.black)
                    Toggle("", isOn: $mMarked)
                        .toggleStyle(CheckboxToggleStyle()) // custom default style check
                }
            }
            
            VStack(alignment: .leading, spacing: 6) {
                Text("AMOUNT (CLP)")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.black)
                TextField("e.g. 5000", text: $mAmount)
                    .textFieldStyle(PlainTextFieldStyle())
                    .foregroundColor(.black)
                    .padding(8)
                    .background(Color.white)
                    .border(Color.black, width: 1)
            }
            
            VStack(alignment: .leading, spacing: 6) {
                Text("DESCRIPTION")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.black)
                TextField("e.g. Lunch", text: $mDescription)
                    .textFieldStyle(PlainTextFieldStyle())
                    .foregroundColor(.black)
                    .padding(8)
                    .background(Color.white)
                    .border(Color.black, width: 1)
            }
            
            VStack(alignment: .leading, spacing: 6) {
                Text("DATE")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.black)
                DatePicker("", selection: $mDate, displayedComponents: .date)
                    .datePickerStyle(DefaultDatePickerStyle())
                    .labelsHidden()
                    .preferredColorScheme(.light)
            }
        }
    }
    
    // MARK: - Transfer Form View
    
    private var transferForm: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("FROM ACCOUNT")
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(.black)
            
            Menu {
                ForEach(db.accounts) { acc in
                    Button(action: {
                        tFromAccountId = acc.id
                    }) {
                        Text("\(acc.name) (\(acc.id))")
                    }
                }
            } label: {
                HStack {
                    if let selectedAcc = db.accounts.first(where: { $0.id == tFromAccountId }) {
                        Text("\(selectedAcc.name) (\(selectedAcc.id))")
                            .font(.system(size: 12))
                            .foregroundColor(.black)
                    } else {
                        Text("Select Account")
                            .font(.system(size: 12))
                            .foregroundColor(.gray)
                    }
                    Spacer()
                    Text("▼")
                        .font(.system(size: 8))
                        .foregroundColor(.black)
                }
                .padding(8)
                .background(Color.white)
                .border(Color.black, width: 1)
            }
            .menuStyle(.borderlessButton)
            
            Text("TO ACCOUNT")
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(.black)
            
            Menu {
                ForEach(db.accounts) { acc in
                    Button(action: {
                        tToAccountId = acc.id
                    }) {
                        Text("\(acc.name) (\(acc.id))")
                    }
                }
            } label: {
                HStack {
                    if let selectedAcc = db.accounts.first(where: { $0.id == tToAccountId }) {
                        Text("\(selectedAcc.name) (\(selectedAcc.id))")
                            .font(.system(size: 12))
                            .foregroundColor(.black)
                    } else {
                        Text("Select Account")
                            .font(.system(size: 12))
                            .foregroundColor(.gray)
                    }
                    Spacer()
                    Text("▼")
                        .font(.system(size: 8))
                        .foregroundColor(.black)
                }
                .padding(8)
                .background(Color.white)
                .border(Color.black, width: 1)
            }
            .menuStyle(.borderlessButton)
            
            VStack(alignment: .leading, spacing: 6) {
                Text("AMOUNT (CLP)")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.black)
                TextField("e.g. 3000", text: $tAmount)
                    .textFieldStyle(PlainTextFieldStyle())
                    .foregroundColor(.black)
                    .padding(8)
                    .background(Color.white)
                    .border(Color.black, width: 1)
            }
            
            VStack(alignment: .leading, spacing: 6) {
                Text("DATE")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.black)
                DatePicker("", selection: $tDate, displayedComponents: .date)
                    .datePickerStyle(DefaultDatePickerStyle())
                    .labelsHidden()
                    .preferredColorScheme(.light)
            }
        }
    }
    
    // MARK: - Operations
    
    private func getFormattedDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }
    
    private func submitTransaction() {
        errorMessage = ""
        
        if mode == .movement {
            guard !mAccountId.isEmpty else {
                errorMessage = "Select a valid account."
                return
            }
            guard let amountVal = Int(mAmount), amountVal > 0 else {
                errorMessage = "Enter a valid positive amount."
                return
            }
            let trimmedDesc = mDescription.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmedDesc.isEmpty else {
                errorMessage = "Description cannot be empty."
                return
            }
            
            let dateStr = getFormattedDate(mDate)
            let result = db.createMovement(amount: amountVal, description: trimmedDesc, accountId: mAccountId, type: mType, marked: mMarked, dateString: dateStr)
            
            switch result {
            case .success:
                isPresented = false
            case .failure(let error):
                errorMessage = error.localizedDescription
            }
        } else {
            guard !tFromAccountId.isEmpty, !tToAccountId.isEmpty else {
                errorMessage = "Select valid accounts."
                return
            }
            if tFromAccountId == tToAccountId {
                errorMessage = "Source and destination accounts must be different."
                return
            }
            guard let amountVal = Int(tAmount), amountVal > 0 else {
                errorMessage = "Enter a valid positive amount."
                return
            }
            
            let dateStr = getFormattedDate(tDate)
            let result = db.createTransfer(fromAccount: tFromAccountId, toAccount: tToAccountId, amount: amountVal, dateString: dateStr)
            
            switch result {
            case .success:
                isPresented = false
            case .failure(let error):
                errorMessage = error.localizedDescription
            }
        }
    }
}
