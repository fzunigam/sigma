import SwiftUI

public struct LogsView: View {
    @ObservedObject var db = DatabaseManager.shared
    @State private var selectedFilter: LogFilter = .all
    @State private var deleteIdInput: String = ""
    @State private var messageText: String = ""
    @State private var isError: Bool = false
    
    enum LogFilter {
        case all, income, expense, transfer
    }
    
    public init() {}
    
    private var filteredLogs: [LogRecord] {
        switch selectedFilter {
        case .all:
            return db.logs
        case .income:
            return db.logs.filter { $0.type == .income }
        case .expense:
            return db.logs.filter { $0.type == .expense }
        case .transfer:
            return db.logs.filter { $0.type == .transfer }
        }
    }
    
    public var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Header
            Text("LOGS")
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.black)
            
            Rectangle()
                .fill(Color.black)
                .frame(height: 1)
            
            // Filter Buttons
            HStack(spacing: 10) {
                filterButton(title: "ALL", filter: .all)
                filterButton(title: "INCOME", filter: .income)
                filterButton(title: "EXPENSE", filter: .expense)
                filterButton(title: "TRANSFERS", filter: .transfer)
            }
            
            // Logs Table
            VStack(spacing: 0) {
                // Table Header
                HStack {
                    Text("ID").frame(width: 100, alignment: .leading)
                    Text("DATE").frame(width: 130, alignment: .leading)
                    Text("TYPE").frame(width: 80, alignment: .leading)
                    Text("ACCOUNT").frame(width: 100, alignment: .leading)
                    Text("AMOUNT").frame(width: 100, alignment: .trailing)
                    Text("DESCRIPTION").frame(minWidth: 200, alignment: .leading)
                }
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.black)
                .padding(.vertical, 8)
                .padding(.horizontal, 10)
                .background(Color(white: 0.95))
                
                Rectangle()
                    .fill(Color.black)
                    .frame(height: 1)
                
                if filteredLogs.isEmpty {
                    Text("No logs match the selected filter.")
                        .font(.system(size: 12))
                        .foregroundColor(.gray)
                        .padding(20)
                        .frame(maxWidth: .infinity, alignment: .center)
                } else {
                    ScrollView {
                        VStack(spacing: 0) {
                            ForEach(filteredLogs) { log in
                                HStack {
                                    Text(log.id)
                                        .font(.system(.body, design: .monospaced))
                                        .frame(width: 100, alignment: .leading)
                                    Text(log.createdAt)
                                        .frame(width: 130, alignment: .leading)
                                    Text(log.type.rawValue.uppercased())
                                        .frame(width: 80, alignment: .leading)
                                    Text(log.accountId.isEmpty ? "-" : log.accountId)
                                        .frame(width: 100, alignment: .leading)
                                    Text("\(log.amount)")
                                        .frame(width: 100, alignment: .trailing)
                                    Text(log.description)
                                        .frame(minWidth: 200, alignment: .leading)
                                }
                                .font(.system(size: 12))
                                .foregroundColor(.black)
                                .padding(.vertical, 10)
                                .padding(.horizontal, 10)
                                
                                Rectangle()
                                    .fill(Color(white: 0.9))
                                    .frame(height: 1)
                            }
                        }
                    }
                }
            }
            .border(Color.black, width: 1)
            
            // Delete Section
            VStack(alignment: .leading, spacing: 8) {
                Text("DELETE RECORD")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(.black)
                
                HStack(spacing: 12) {
                    TextField("m-xxxxxx / t-xxxxxx", text: $deleteIdInput)
                        .textFieldStyle(PlainTextFieldStyle())
                        .font(.system(.body, design: .monospaced))
                        .foregroundColor(.black)
                        .padding(8)
                        .background(Color.white)
                        .border(Color.black, width: 1)
                        .frame(width: 250)
                    
                    Button(action: deleteRecord) {
                        Text("DELETE")
                            .font(.system(size: 12, weight: .bold))
                            .padding(.horizontal, 20)
                            .padding(.vertical, 8)
                            .background(Color.black)
                            .foregroundColor(.white)
                            .cornerRadius(0)
                    }
                    .buttonStyle(PlainButtonStyle())
                }
                
                if !messageText.isEmpty {
                    Text(messageText)
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(isError ? .black : .gray) // B/W styling constraints
                        .padding(.top, 4)
                }
            }
            .padding(.top, 10)
            
            Spacer()
        }
        .padding(24)
        .background(Color.white)
    }
    
    private func filterButton(title: String, filter: LogFilter) -> some View {
        Button(action: {
            selectedFilter = filter
        }) {
            Text(title)
                .font(.system(size: 10, weight: .bold))
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(selectedFilter == filter ? Color.black : Color.white)
                .foregroundColor(selectedFilter == filter ? Color.white : Color.black)
                .border(Color.black, width: 1)
        }
        .buttonStyle(PlainButtonStyle())
    }
    
    private func deleteRecord() {
        let trimmed = deleteIdInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            isError = true
            messageText = "ID field cannot be empty."
            return
        }
        
        let result = db.deleteRecord(visualId: trimmed)
        switch result {
        case .success:
            isError = false
            messageText = "Successfully deleted record '\(trimmed)'"
            deleteIdInput = ""
        case .failure(let error):
            isError = true
            messageText = error.localizedDescription
        }
    }
}

struct LogsView_Previews: PreviewProvider {
    static var previews: some View {
        LogsView()
    }
}
