import SwiftUI

@main
struct LedgerFlowApp: App {
    var body: some Scene {
        WindowGroup {
            MobileRoot()
                .environment(\.locale, Locale(identifier: "en"))
                .preferredColorScheme(.light)
        }
    }
}
