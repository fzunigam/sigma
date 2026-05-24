import SwiftUI

public enum AppTab {
    case dashboard
    case logs
    case accounts
    case render
}

struct MainView: View {
    @State private var activeTab: AppTab = .dashboard
    
    var body: some View {
        HStack(spacing: 0) {
            // Sidebar Navigation Pane (Width: 200)
            VStack(alignment: .leading, spacing: 0) {
                // Branding Header
                Text("SIGMA")
                    .font(.system(size: 20, weight: .black))
                    .foregroundColor(.black)
                    .padding(.horizontal, 24)
                    .padding(.top, 28)
                    .padding(.bottom, 24)
                
                Rectangle()
                    .fill(Color.black)
                    .frame(height: 1)
                
                VStack(spacing: 4) {
                    sidebarButton(title: "DASHBOARD", tab: .dashboard)
                    sidebarButton(title: "LOGS", tab: .logs)
                    sidebarButton(title: "ACCOUNTS", tab: .accounts)
                    sidebarButton(title: "RENDER ENGINE", tab: .render)
                }
                .padding(.top, 16)
                .padding(.horizontal, 12)
                
                Spacer()
                
                // Footer
                VStack(alignment: .leading, spacing: 4) {
                    Text("LOCAL-FIRST")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.gray)
                    Text("v0.2.1")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(.black)
                }
                .padding(24)
            }
            .frame(width: 200)
            .frame(maxHeight: .infinity, alignment: .leading)
            .background(Color.white)
            
            // Vertical Stark Divider
            Rectangle()
                .fill(Color.black)
                .frame(width: 1)
            
            // Detail Display Pane
            ZStack {
                Color.white
                
                switch activeTab {
                case .dashboard:
                    DashboardView()
                case .logs:
                    LogsView()
                case .accounts:
                    AccountsView()
                case .render:
                    RenderView()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(minWidth: 1000, minHeight: 650)
        .background(Color.white)
        .preferredColorScheme(.light)
    }
    
    private func sidebarButton(title: String, tab: AppTab) -> some View {
        Button(action: {
            activeTab = tab
        }) {
            HStack {
                Text(title)
                    .font(.system(size: 11, weight: .bold))
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(activeTab == tab ? Color.black : Color.white)
            .foregroundColor(activeTab == tab ? Color.white : Color.black)
            .cornerRadius(0) // stark edges
        }
        .buttonStyle(PlainButtonStyle())
    }
}

@main
struct SigmaApp: App {
    init() {
        // Trigger initial db load
        _ = DatabaseManager.shared
    }
    
    var body: some Scene {
        WindowGroup {
            MainView()
                .navigationTitle("")
                .background(Color.white)
                .preferredColorScheme(.light)
        }
        .windowStyle(TitleBarWindowStyle())
    }
}
