import SwiftUI

public struct DashboardView: View {
    @ObservedObject var db = DatabaseManager.shared
    @State private var isShowingAddTx = false
    
    public init() {}
    
    public var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Header
            HStack {
                Text("DASHBOARD")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundColor(.black)
                Spacer()
                Button(action: {
                    isShowingAddTx = true
                }) {
                    Text("+ LOG TRANSACTION")
                        .font(.system(size: 12, weight: .bold))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Color.black)
                        .foregroundColor(.white)
                        .cornerRadius(0) // Stark sharp edges
                }
                .buttonStyle(PlainButtonStyle())
            }
            
            Rectangle()
                .fill(Color.black)
                .frame(height: 1)
            
            // Metrics Block
            HStack(spacing: 40) {
                // Net Worth
                VStack(alignment: .leading, spacing: 6) {
                    Text("NET WORTH")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.gray)
                    Text("\(db.netWorth) CLP")
                        .font(.system(size: 32, weight: .black))
                        .foregroundColor(.black)
                }
                .padding(16)
                .border(Color.black, width: 1)
                
                // Marked Total (Unrendered)
                VStack(alignment: .leading, spacing: 6) {
                    Text("MARKED TOTAL (UNRENDERED)")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.gray)
                    Text("\(db.markedTotal) CLP")
                        .font(.system(size: 32, weight: .black))
                        .foregroundColor(.black)
                }
                .padding(16)
                .border(Color.black, width: 1)
            }
            .padding(.vertical, 10)
            
            // Active Accounts Table
            Text("ACTIVE ACCOUNTS")
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.black)
            
            VStack(spacing: 0) {
                // Table Header
                HStack {
                    Text("ID").frame(width: 120, alignment: .leading)
                    Text("NAME").frame(minWidth: 200, alignment: .leading)
                    Text("TYPE").frame(width: 100, alignment: .leading)
                    Text("BALANCE").frame(width: 120, alignment: .trailing)
                    Text("CREDIT LIMIT").frame(width: 120, alignment: .trailing)
                }
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.black)
                .padding(.vertical, 8)
                .padding(.horizontal, 10)
                .background(Color(white: 0.95))
                
                Rectangle()
                    .fill(Color.black)
                    .frame(height: 1)
                
                if db.accounts.isEmpty {
                    Text("No active accounts found.")
                        .font(.system(size: 12))
                        .foregroundColor(.gray)
                        .padding(20)
                        .frame(maxWidth: .infinity, alignment: .center)
                } else {
                    ScrollView {
                        VStack(spacing: 0) {
                            ForEach(db.accounts) { acc in
                                HStack {
                                    Text(acc.id)
                                        .font(.system(.body, design: .monospaced))
                                        .frame(width: 120, alignment: .leading)
                                    Text(acc.name)
                                        .frame(minWidth: 200, alignment: .leading)
                                    Text(acc.type.rawValue.uppercased())
                                        .frame(width: 100, alignment: .leading)
                                    Text("\(acc.balance)")
                                        .frame(width: 120, alignment: .trailing)
                                    Text(acc.type == .credit ? "\(acc.creditLimit)" : "-")
                                        .frame(width: 120, alignment: .trailing)
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
            
            Spacer()
        }
        .padding(24)
        .background(Color.white)
        .sheet(isPresented: $isShowingAddTx) {
            AddTransactionView(isPresented: $isShowingAddTx)
        }
    }
}

struct DashboardView_Previews: PreviewProvider {
    static var previews: some View {
        DashboardView()
    }
}
