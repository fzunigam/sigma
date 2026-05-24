import SwiftUI

public struct RenderView: View {
    @ObservedObject var db = DatabaseManager.shared
    
    @State private var messageText: String = ""
    @State private var isError: Bool = false
    
    public init() {}
    
    public var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Header
            Text("RENDER ENGINE")
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.black)
            
            Rectangle()
                .fill(Color.black)
                .frame(height: 1)
            
            HStack(alignment: .top, spacing: 40) {
                // Left Column: Render Executer
                VStack(alignment: .leading, spacing: 14) {
                    Text("CURRENT UNRENDERED STATE")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.black)
                    
                    VStack(alignment: .leading, spacing: 14) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("NET UNRENDERED AMOUNT")
                                .font(.system(size: 9, weight: .bold))
                                .foregroundColor(.gray)
                            Text("\(db.markedTotal) CLP")
                                .font(.system(size: 24, weight: .black))
                                .foregroundColor(.black)
                        }
                        
                        Button(action: runRender) {
                            Text("EXECUTE RENDER RUN")
                                .font(.system(size: 11, weight: .bold))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                                .background(Color.black)
                                .foregroundColor(.white)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                    .padding(20)
                    .border(Color.black, width: 1)
                    
                    if !messageText.isEmpty {
                        Text(messageText)
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.black)
                            .padding(.top, 4)
                    }
                }
                .frame(width: 320)
                
                // Right Column: Render History List
                VStack(alignment: .leading, spacing: 14) {
                    Text("RENDER SNAPSHOT HISTORY")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.black)
                    
                    VStack(spacing: 0) {
                        // Header
                        HStack {
                            Text("SNAPSHOT ID").font(.system(size: 10, weight: .bold)).frame(width: 100, alignment: .leading)
                            Text("DATE").font(.system(size: 10, weight: .bold)).frame(minWidth: 120, alignment: .leading)
                            Text("NET AMOUNT").font(.system(size: 10, weight: .bold)).frame(width: 120, alignment: .trailing)
                        }
                        .padding(.vertical, 8)
                        .padding(.horizontal, 10)
                        .background(Color(white: 0.95))
                        
                        Rectangle().fill(Color.black).frame(height: 1)
                        
                        if db.renderHistory.isEmpty {
                            Text("No render history snapshots found.")
                                .font(.system(size: 12))
                                .foregroundColor(.gray)
                                .padding(20)
                                .frame(maxWidth: .infinity, alignment: .center)
                        } else {
                            ScrollView {
                                VStack(spacing: 0) {
                                    ForEach(db.renderHistory) { snapshot in
                                        HStack {
                                            Text(snapshot.id)
                                                .font(.system(size: 12, design: .monospaced))
                                                .frame(width: 100, alignment: .leading)
                                            
                                            Text(snapshot.renderedAt)
                                                .font(.system(size: 12))
                                                .frame(minWidth: 120, alignment: .leading)
                                            
                                            Text("\(snapshot.netAmount)")
                                                .font(.system(size: 12, weight: .bold))
                                                .frame(width: 120, alignment: .trailing)
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
    
    private func runRender() {
        messageText = ""
        
        let result = db.executeRender()
        switch result {
        case .success(let info):
            if info.count == 0 {
                isError = false
                messageText = "No marked movements to render."
            } else {
                isError = false
                messageText = "Render completed. Rendered \(info.count) movements. Snapshot logged."
            }
        case .failure(let error):
            isError = true
            messageText = error.localizedDescription
        }
    }
}

struct RenderView_Previews: PreviewProvider {
    static var previews: some View {
        RenderView()
    }
}
